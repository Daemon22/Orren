#!/usr/bin/env python3
"""Serve the Orren Visual Hub and a real, in-memory Orren Engine session.

Run from the repository root with `python3 visual-hub/server.py`.
Mutations update the Engine's live SIR graph for this server process only.
The coordinator returns realization plans; this server does not claim to emit
source files while the optional web-layout code generator is unavailable.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys
from threading import RLock
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = Path(__file__).resolve().parent
FIXTURE = WEB_ROOT / "MyApp.orn"
sys.path.insert(0, str(REPO_ROOT))

from orren_engine import (  # noqa: E402
    BehavioralStatement,
    Dimension,
    Engine,
    RealizationTarget,
    RelationalStatement,
    SIRNode,
    __version__ as ENGINE_VERSION,
)

DIMENSION_NAMES = {
    Dimension.EXPRESSION: "Expression",
    Dimension.COGNITIVE: "Cognitive",
    Dimension.VIBE: "Vibe",
    Dimension.SPATIAL: "Spatial",
    Dimension.TEMPORAL: "Temporal",
    Dimension.RELATIONAL: "Relational",
    Dimension.CONDITIONAL: "Conditional",
    Dimension.BEHAVIORAL: "Behavioral",
    Dimension.EQUILIBRIUM: "Equilibrium",
}
TARGET_CATALOG = {
    "web_interface": {
        "language": "HTML/CSS/JS",
        "capabilities": ["layout", "color", "motion", "event_handling", "typography"],
        "can_express": ["conditional", "behavioral", "temporal"],
        "needs_bridge": ["weather_provider"],
        "preservation_score": 0.92,
    },
    "android_app": {
        "language": "Kotlin",
        "capabilities": ["layout", "event_handling", "temporal"],
        "needs_bridge": ["weather_provider"],
        "preservation_score": 0.72,
    },
    "rust_core": {
        "language": "Rust",
        "capabilities": ["data_processing", "relational_logic"],
        "preservation_score": 0.81,
    },
}


def _json_value(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key.value if isinstance(key, Enum) else key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _identifier(value: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "node"


def _display_name(name: str) -> str:
    special = {"myapp": "MyApp", "ui": "UI", "weather_service": "WeatherService"}
    if name.lower() in special:
        return special[name.lower()]
    return " ".join(part[:1].upper() + part[1:] for part in name.replace("-", "_").split("_") if part)


class RuntimeSession:
    """One volatile Engine/SIR workspace and its action provenance."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.engine: Engine | None = None
        self.result = None
        self.graph = None
        self.editor = None
        self.artifacts = []
        self.events: list[dict] = []
        self.display_names: dict[str, str] = {}
        self.last_realization = None
        self.codegen_message = ""
        try:
            from orren_engine import generate_code as _optional_generator  # noqa: F401
            self.codegen_available = True
        except Exception as exc:
            self.codegen_available = False
            missing = getattr(exc, "name", "optional backend")
            self.codegen_message = f"Source emitter unavailable ({missing}). The coordinator still provides real plans."
        self.reset("example")

    def reset(self, mode: str) -> dict:
        with self.lock:
            if mode == "empty":
                source = "create workspace : Application\n\n    context:\n        purpose: an empty Orren Visual Hub field\n"
                source_name = "New in-memory field"
            else:
                source = FIXTURE.read_text(encoding="utf-8")
                source_name = "visual-hub/MyApp.orn"
            engine = Engine()
            result = engine.run(source)
            if result.graph is None:
                raise RuntimeError("Engine did not produce a SIR graph")
            self.engine, self.result, self.graph = engine, result, result.graph
            self.editor = engine.editor()
            self.artifacts = list(result.artifacts)
            self.display_names = {}
            self.last_realization = datetime.now(timezone.utc).isoformat()
            self.events = []
            self.source_name = source_name
            self.record("Field loaded into the Orren Engine", f"Parsed {result.expressions_count} expression(s); built {result.sir_node_count} SIR nodes and {len(result.artifacts)} realization plans.", None, "Engine · .orn")
            return self.snapshot()

    def record(self, title: str, description: str, node_id: str | None, source: str = "Visual Producer · SIR") -> None:
        self.events.insert(0, {
            "title": title,
            "description": description,
            "nodeId": node_id,
            "time": datetime.now().astimezone().strftime("%H:%M:%S"),
            "source": source,
        })
        self.events = self.events[:80]

    def _node_by_id(self, node_id: str | None):
        if not node_id:
            return None
        return next((node for node in self.graph.nodes if node.node_id == node_id), None)

    def _display(self, node) -> str:
        if node.node_id in self.display_names:
            return self.display_names[node.node_id]
        return _display_name(node.name)

    def _node_kind(self, node) -> str:
        if node.parent is None or node.kind == "root":
            return "Semantic root"
        name = node.name.lower()
        if name in {"ui", "logic", "structure"}:
            return "Structure"
        if name in {"dashboard", "interface"}:
            return "Interface"
        if name in {"weather_service", "service"}:
            return "Service"
        if node.get_dimension(Dimension.BEHAVIORAL):
            return "Behavioral node"
        return "Component"

    def _behavior_text(self, node) -> str:
        statements = node.get_dimension(Dimension.BEHAVIORAL)
        if not statements:
            return ""
        def field(item, name, default=""):
            return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)
        statement = next((item for item in statements if field(item, "kind") == "responds_to"), statements[0])
        kind = field(statement, "kind")
        if kind == "responds_to":
            return f"Responds to {field(statement, 'stimulus', 'an intent')} with {field(statement, 'response', 'a defined response')}."
        if kind == "behaves_as":
            return f"Behaves as {field(statement, 'role', 'a semantic component')}"
        if kind == "lifecycle":
            return "Lifecycle: " + " → ".join(field(statement, "states", []) or [])
        if kind == "transitions":
            return f"Transitions from {field(statement, 'from_state', 'a state')} to {field(statement, 'to_state', 'another state')} on {field(statement, 'trigger', 'an event')}"
        return str(field(statement, "response", ""))

    def _resolve_reference(self, name: str):
        if not name:
            return None
        exact = self.graph.find(name)
        if exact:
            return exact
        candidates = [node for node in self.graph.nodes if node.name.casefold() == name.casefold()]
        if not candidates:
            candidates = [node for node in self.graph.nodes if node.path.casefold().endswith("." + name.casefold())]
        return candidates[0] if len(candidates) == 1 else None

    def _relations(self) -> list[dict]:
        relations = []
        for source in self.graph.nodes:
            for statement in source.get_dimension(Dimension.RELATIONAL):
                data = _json_value(statement)
                destination = self._resolve_reference(data.get("target", ""))
                if not destination:
                    continue
                relation = str(data.get("relation", "relates"))
                identity = f"{source.node_id}:{destination.node_id}:{relation}:{len(relations)}"
                label = relation.replace("_", " ")
                note = data.get("qualifier")
                relations.append({
                    "id": identity,
                    "from": source.node_id,
                    "to": destination.node_id,
                    "type": relation,
                    "label": label,
                    "intent": note or f"{self._display(source)} {label} {self._display(destination)}.",
                    "sourcePath": source.path,
                    "targetPath": destination.path,
                })
        return relations

    def _target_rows(self) -> list[dict]:
        plans = {artifact.target_name: artifact for artifact in self.artifacts}
        rows = []
        for target in self.graph.realization_targets:
            plan = plans.get(target.name)
            score = plan.preservation_score if plan else target.preservation_score
            output_files = [asdict(item) for item in plan.output_files] if plan else []
            report = list(plan.degradation_report) if plan else []
            rows.append({
                "id": target.name,
                "name": target.name,
                "language": target.language,
                "capabilities": list(target.capabilities),
                "needsBridge": list(target.needs_bridge),
                "preservationScore": round(float(score), 4),
                "outputFiles": output_files,
                "degradationCount": len(report),
                "degradationBySeverity": {
                    level: sum(1 for item in report if item.get("severity") == level)
                    for level in ("none", "low", "medium", "high", "out_of_scope")
                },
                "planState": "degraded" if float(score) < 0.999 else "planned",
                "emitted": False,
            })
        return rows

    def snapshot(self) -> dict:
        with self.lock:
            max_count = {name: 0 for name in DIMENSION_NAMES.values()}
            counts_by_node = {}
            for node in self.graph.nodes:
                counts = {DIMENSION_NAMES[dim]: len(node.get_dimension(dim)) for dim in Dimension}
                counts_by_node[node.node_id] = counts
                for name, count in counts.items():
                    max_count[name] = max(max_count[name], count)
            nodes = []
            for node in self.graph.nodes:
                dimensions = {
                    DIMENSION_NAMES[dim]: [_json_value(item) for item in node.get_dimension(dim)]
                    for dim in Dimension
                }
                counts = counts_by_node[node.node_id]
                profile = {name: (count / max_count[name] if max_count[name] else 0) for name, count in counts.items()}
                nodes.append({
                    "id": node.node_id,
                    "name": self._display(node),
                    "parentId": node.parent.node_id if node.parent else None,
                    "path": node.path,
                    "kind": self._node_kind(node),
                    "confidence": None,
                    "behavior": self._behavior_text(node),
                    "webTarget": False,
                    "realization": "planned",
                    "profile": profile,
                    "dimensionCounts": counts,
                    "dimensions": dimensions,
                })
            root = self.graph.root
            fingerprint = sha256(self.graph.signature().encode("utf-8")).hexdigest()
            zaryel = self.result.zaryel_report if self.result else None
            return {
                "runtime": {
                    "connected": True,
                    "engineVersion": ENGINE_VERSION,
                    "mode": "in-memory SIR session",
                    "sourceFile": self.source_name,
                    "fingerprint": f"sha256:{fingerprint}",
                    "fingerprintType": "SIR semantic graph signature; not the source-file hash",
                    "codegenAvailable": self.codegen_available,
                    "codegenMessage": self.codegen_message,
                    "zaryelValid": bool(zaryel and zaryel.valid),
                    "sessionOnly": True,
                    "lastPlanAt": self.last_realization,
                },
                "rootId": root.node_id if root else None,
                "focusId": next((node.node_id for node in self.graph.nodes if node.name.casefold() == "button"), root.node_id if root else None),
                "nodes": nodes,
                "relations": self._relations(),
                "targets": self._target_rows(),
                "availableTargets": [
                    {"id": name, "language": spec["language"], "present": any(t.name == name for t in self.graph.realization_targets)}
                    for name, spec in TARGET_CATALOG.items()
                ],
                "events": list(self.events),
                "engineSummary": self.result.summary() if self.result else "",
            }

    def _replan(self) -> None:
        self.artifacts = self.engine.re_coordinate()
        self.last_realization = datetime.now(timezone.utc).isoformat()

    def apply(self, data: dict) -> dict:
        with self.lock:
            action = str(data.get("action", ""))
            if action == "reset":
                return self.reset(str(data.get("mode", "example")))
            if action == "realize":
                self._replan()
                selected_id = data.get("nodeId")
                node = self._node_by_id(selected_id)
                note = "The Orren coordinator refreshed the realization plans for the current SIR graph. No files are emitted by this preview."
                self.record("Realization plans refreshed", note, selected_id, "Engine · coordinator")
                return self.snapshot()
            if action == "create":
                name = " ".join(str(data.get("name", "")).strip().split())[:48]
                if not name:
                    raise ValueError("Enter a name for the semantic node.")
                parent = self._node_by_id(data.get("parentId")) or self.graph.root
                if parent is None:
                    raise ValueError("Create a root field before adding a child node.")
                segment = _identifier(name)
                sibling_names = {child.name.casefold() for child in parent.children}
                base, suffix = segment, 2
                while segment.casefold() in sibling_names:
                    segment = f"{base}_{suffix}"
                    suffix += 1
                node = SIRNode(path=f"{parent.path}.{segment}", name=segment, kind="entity", parent=parent)
                parent.children.append(node)
                self.graph.nodes.append(node)
                self.display_names[node.node_id] = name
                self.record(f"{name} added to the live SIR", f"Created {node.path} beneath {parent.path} in the in-memory semantic graph.", node.node_id)
                self._replan()
            elif action == "behavior":
                node = self._node_by_id(data.get("nodeId"))
                text = " ".join(str(data.get("text", "")).strip().split())[:180]
                if node is None or not text:
                    raise ValueError("Select a node and describe the behavior to add.")
                statement = BehavioralStatement(subject=node.name, kind="responds_to", stimulus="visual_producer_intent", response=text)
                self.editor.add(node.path, Dimension.BEHAVIORAL, statement, rationale="Visual Producer intent accepted by the builder.")
                self.record(f"Behavior added to {self._display(node)}", text, node.node_id)
                self._replan()
            elif action == "move":
                node = self._node_by_id(data.get("nodeId"))
                parent = self._node_by_id(data.get("parentId"))
                if node is None or parent is None or node is parent:
                    raise ValueError("Select a different existing semantic parent.")
                cursor = parent
                while cursor:
                    if cursor is node:
                        raise ValueError("That move would create a semantic cycle.")
                    cursor = cursor.parent
                if node.parent is parent:
                    return self.snapshot()
                old_parent = node.parent
                self.editor.relocate(node.path, parent.path, rationale="Visual Producer proposed a hierarchy change; builder applied it to SIR.")
                self.record(f"{self._display(node)} reparented in SIR", f"Moved from {old_parent.path if old_parent else 'field root'} to {parent.path}; semantic paths were recomputed.", node.node_id)
                self._replan()
            elif action == "relate":
                source = self._node_by_id(data.get("from"))
                target = self._node_by_id(data.get("to"))
                relation = str(data.get("type", "feeds"))
                note = " ".join(str(data.get("note", "")).strip().split())[:120]
                if source is None or target is None or source is target:
                    raise ValueError("Choose two different SIR nodes.")
                if relation not in {"feeds", "triggers", "produces", "depends_on"}:
                    raise ValueError("Choose a supported typed relationship.")
                existing = [item for item in source.get_dimension(Dimension.RELATIONAL) if _json_value(item).get("target") == target.path and _json_value(item).get("relation") == relation]
                if existing:
                    raise ValueError("That typed relationship is already in SIR.")
                payload = RelationalStatement(source=source.path, relation=relation, target=target.path, qualifier=note or None)
                self.editor.add(source.path, Dimension.RELATIONAL, payload, rationale="Explicitly proposed and confirmed in the Visual Hub.")
                self.record(f"{self._display(source)} {relation.replace('_', ' ')} {self._display(target)}", note or "Typed relationship confirmed and written to the SIR relational dimension.", target.node_id)
                self._replan()
            elif action == "add_target":
                name = str(data.get("target", ""))
                spec = TARGET_CATALOG.get(name)
                if spec is None:
                    raise ValueError("Choose a target from the Orren platform catalog.")
                if any(target.name == name for target in self.graph.realization_targets):
                    raise ValueError(f"The {name} target is already in this field.")
                self.graph.realization_targets.append(RealizationTarget(
                    name=name,
                    language=spec["language"],
                    capabilities=list(spec.get("capabilities", [])),
                    can_express=list(spec.get("can_express", [])),
                    needs_bridge=list(spec.get("needs_bridge", [])),
                    preservation_score=float(spec.get("preservation_score", 1.0)),
                ))
                self.record(f"{name} target added to the SIR field", f"The coordinator will assess {spec['language']} against the whole semantic graph; this adds a plan, not generated files.", None)
                self._replan()
            elif action == "remove_target":
                name = str(data.get("target", ""))
                before = len(self.graph.realization_targets)
                self.graph.realization_targets[:] = [target for target in self.graph.realization_targets if target.name != name]
                if len(self.graph.realization_targets) == before:
                    raise ValueError("That target is not in this SIR field.")
                self.record(f"{name} target removed from the SIR field", "The meaning graph was preserved; its realization plan was removed.", None)
                self._replan()
            else:
                raise ValueError("Unsupported Visual Producer action.")
            return self.snapshot()


SESSION = RuntimeSession()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == "/api/health":
            state = SESSION.snapshot()
            self._json(200, {"ok": True, "runtime": state["runtime"]})
            return
        if route == "/api/field":
            self._json(200, SESSION.snapshot())
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/action":
            self._json(404, {"error": "Unknown Orren API route."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 32768:
                raise ValueError("Request size must be between 1 byte and 32 KB.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON action object.")
            self._json(200, SESSION.apply(data))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:  # Keep the local workbench responsive on engine errors.
            self._json(500, {"error": f"Orren Engine action failed: {exc}"})

    def log_message(self, format, *args):
        if os.environ.get("ORREN_HTTP_LOG", "1") != "0":
            super().log_message(format, *args)


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "4173"))
    server = ThreadingHTTPServer((host, port), Handler)
    server.session = SESSION
    print(f"Orren Visual Hub + Engine listening on http://{host}:{port}", flush=True)
    print(f"Engine {ENGINE_VERSION} · {len(SESSION.graph.nodes)} SIR nodes · {len(SESSION.artifacts)} realization plans", flush=True)
    print(f"Source generation: {'available' if SESSION.codegen_available else SESSION.codegen_message}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
