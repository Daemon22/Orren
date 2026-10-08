import asyncio, hashlib
from .field import SIRField
from .agents import TextProducer, GroundingRefiner, ConflictResolver, BashRealizer, PythonRealizer, VisualProducer, VisualObserver
from .store import Store
class OrrenRuntime:
    def __init__(self, db_path="orren.sqlite"):
        self.field=SIRField(); self.store=Store(db_path)
        self.text=TextProducer(self.field); self.grounding=GroundingRefiner(self.field); self.conflicts=ConflictResolver(self.field)
        self.bash=BashRealizer(self.field); self.python=PythonRealizer(self.field)
        self.visual=VisualProducer(self.field); self.observer=VisualObserver(self.field)
        self.field.bus.subscribe(self.grounding.on_event)
        self.field.bus.subscribe(self.conflicts.on_event)
    async def settle(self, ticks=3):
        for _ in range(ticks):
            await asyncio.sleep(0)
            self.field.mark_stable_if_quiet(1)
        self.store.snapshot(self.field)
        return self.field.state
    async def inject(self, source):
        nodes=await self.text.inject(source); await self.settle(); return nodes
    async def realize(self, node_id, target):
        node=self.field.nodes[node_id]
        if target=="bash": result=await self.bash.realize(node)
        elif target=="python": result=await self.python.realize(node)
        else: raise ValueError(target)
        digest=hashlib.sha256(result["content"].encode()).hexdigest()
        result["hash"]=digest
        self.store.db.execute("INSERT INTO artifacts(node_id,realizer,path,status,hash) VALUES(?,?,?,?,?)",(node_id,result["realizer"],result["path"],result["status"],digest))
        self.store.db.commit()
        return result
