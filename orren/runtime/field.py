from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable
import asyncio, json, uuid

DIMENSIONS = ("expression","cognitive","vibe","spatial","temporal","relational","conditional","behavioral","equilibrium")

def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return f"{prefix}_{uuid.uuid4().hex[:12]}"

@dataclass(frozen=True)
class Provenance:
    producer: str
    timestamp: str
    parent_nodes: tuple[str,...] = ()
    source_hash: str = ""

@dataclass
class SIRNode:
    id: str
    name: str
    content: dict[str,Any] = dc_field(default_factory=dict)
    dimensions: dict[str,Any] = dc_field(default_factory=lambda:{d:None for d in DIMENSIONS})
    confidence: float = .5
    stability: str = "changing"
    active: bool = True
    provenance: Provenance = dc_field(default_factory=lambda:Provenance("unknown",now()))
    proposals: list[str] = dc_field(default_factory=list)
    resolved_by: list[str] = dc_field(default_factory=list)
    def snapshot(self):
        return {"id":self.id,"name":self.name,"content":self.content,"dimensions":self.dimensions,
                "confidence":self.confidence,"stability":self.stability,"active":self.active,
                "provenance":{"producer":self.provenance.producer,"timestamp":self.provenance.timestamp,
                "parent_nodes":list(self.provenance.parent_nodes),"source_hash":self.provenance.source_hash},
                "proposals":self.proposals,"resolved_by":self.resolved_by}

@dataclass
class ResolutionNode:
    id: str
    type: str
    subjects: tuple[str,...]
    proposed_action: str
    confidence: float = .5
    accepted_by: list[str] = dc_field(default_factory=list)
    rejected_by: list[str] = dc_field(default_factory=list)
    status: str = "proposed"
    provenance: Provenance = dc_field(default_factory=lambda:Provenance("resolver",now()))
    def snapshot(self):
        return {"id":self.id,"type":self.type,"subjects":list(self.subjects),
                "proposed_action":self.proposed_action,"confidence":self.confidence,
                "accepted_by":self.accepted_by,"rejected_by":self.rejected_by,"status":self.status,
                "provenance":{"producer":self.provenance.producer,"timestamp":self.provenance.timestamp,
                "parent_nodes":list(self.provenance.parent_nodes),"source_hash":self.provenance.source_hash}}

@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str = "contains"

@dataclass(frozen=True)
class FieldChanged:
    node_id: str
    change_type: str
    snapshot_id: str

class EventBus:
    def __init__(self): self._subscribers=[]
    def subscribe(self, callback): self._subscribers.append(callback)
    async def publish(self,event):
        for cb in tuple(self._subscribers):
            result=cb(event)
            if asyncio.iscoroutine(result): await result
        await asyncio.sleep(0)

class SIRField:
    def __init__(self):
        self.nodes={}; self.edges=set(); self.bus=EventBus()
        self.cycle=0; self.idle_ticks=0; self.state="converging"
    def _canonical(self):
        payload={"nodes":[self.nodes[k].snapshot() for k in sorted(self.nodes)],
                 "edges":[e.__dict__ for e in sorted(self.edges,key=lambda x:(x.src,x.dst,x.kind))]}
        return json.dumps(payload,sort_keys=True,separators=(",",":"))
    @property
    def snapshot_id(self): return sha256(self._canonical().encode()).hexdigest()[:24]
    async def mutate(self, fn:Callable[[],str|None]):
        changed=fn(); self.cycle+=1; self.idle_ticks=0; self.state="converging"
        event=FieldChanged(changed or "","mutation",self.snapshot_id); await self.bus.publish(event)
        return event.snapshot_id
    async def add_node(self,node): return await self.mutate(lambda:self.nodes.__setitem__(node.id,node) or node.id)
    async def add_edge(self,src,dst,kind="contains"):
        return await self.mutate(lambda:self.edges.add(Edge(src,dst,kind)) or dst)
    async def update_node(self,node_id,**changes):
        node=self.nodes[node_id]
        if isinstance(node,ResolutionNode): raise TypeError("resolution nodes use accept/reject")
        def apply():
            for key,value in changes.items():
                if key=="dimensions": node.dimensions.update(value)
                else: setattr(node,key,value)
            return node_id
        return await self.mutate(apply)
    async def propose(self,resolution):
        for sid in resolution.subjects:
            n=self.nodes.get(sid)
            if isinstance(n,SIRNode) and resolution.id not in n.proposals: n.proposals.append(resolution.id)
        return await self.add_node(resolution)
    async def accept_resolution(self,resolution_id,actor="builder"):
        r=self.nodes[resolution_id]
        if not isinstance(r,ResolutionNode): raise KeyError(resolution_id)
        r.status="accepted"; r.accepted_by.append(actor)
        for sid in r.subjects:
            n=self.nodes.get(sid)
            if isinstance(n,SIRNode): n.active=False; n.resolved_by.append(resolution_id)
        return await self.mutate(lambda:resolution_id)
    def find(self,name):
        for n in self.nodes.values():
            if isinstance(n,SIRNode) and n.active and n.name.lower()==name.lower(): return n
        return None
    def children(self,node_id):
        ids=[e.dst for e in self.edges if e.src==node_id and e.kind=="contains"]
        return [self.nodes[i] for i in ids if i in self.nodes]
    def parents(self,node_id):
        ids=[e.src for e in self.edges if e.dst==node_id and e.kind=="contains"]
        return [self.nodes[i] for i in ids if i in self.nodes]
    def mark_stable_if_quiet(self,ticks=3):
        self.idle_ticks+=1
        if self.idle_ticks>=ticks:
            self.state="stable"
            for n in self.nodes.values():
                if isinstance(n,SIRNode): n.stability="stable"
            return True
        return False
    def export(self):
        return {"state":self.state,"cycle":self.cycle,"snapshot_id":self.snapshot_id,
                "nodes":[self.nodes[k].snapshot() for k in sorted(self.nodes)],
                "edges":[e.__dict__ for e in sorted(self.edges,key=lambda x:(x.src,x.dst,x.kind))]}
