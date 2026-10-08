"""Regression tests for the Visual Hub's real Orren Engine bridge."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "visual-hub"))
import server as visual_hub_server  # noqa: E402


def test_fixture_hydrates_real_sir_dimensions_relations_and_plans():
    session = visual_hub_server.RuntimeSession()
    snapshot = session.snapshot()

    assert snapshot["runtime"]["connected"] is True
    assert snapshot["runtime"]["sourceFile"] == "visual-hub/MyApp.orn"
    assert snapshot["runtime"]["zaryelValid"] is True
    assert len(snapshot["nodes"]) == 8
    assert len(snapshot["relations"]) == 3
    assert len(snapshot["targets"]) == 3
    button = next(node for node in snapshot["nodes"] if node["name"] == "Button")
    assert button["dimensionCounts"]["Behavioral"] == 2
    assert button["dimensionCounts"]["Vibe"] > 0
    assert button["dimensions"]["Behavioral"]
    assert all(target["outputFiles"] for target in snapshot["targets"])
    assert all(target["emitted"] is False for target in snapshot["targets"])


def test_visual_producer_mutations_update_sir_and_derived_paths():
    session = visual_hub_server.RuntimeSession()
    initial = session.snapshot()
    dashboard = next(node for node in initial["nodes"] if node["name"] == "Dashboard")
    logic = next(node for node in initial["nodes"] if node["name"] == "Logic")
    card = next(node for node in initial["nodes"] if node["name"] == "Card")
    button = next(node for node in initial["nodes"] if node["name"] == "Button")

    created = session.apply({"action": "create", "name": "QAProbe", "parentId": dashboard["id"]})
    probe = next(node for node in created["nodes"] if node["name"] == "QAProbe")
    assert probe["path"] == "myapp.ui.dashboard.qaprobe"
    assert probe["parentId"] == dashboard["id"]

    with_behavior = session.apply({"action": "behavior", "nodeId": probe["id"], "text": "Track a user intent"})
    probe = next(node for node in with_behavior["nodes"] if node["id"] == probe["id"])
    assert probe["dimensionCounts"]["Behavioral"] == 1
    assert "Track a user intent" in probe["behavior"]

    moved = session.apply({"action": "move", "nodeId": button["id"], "parentId": logic["id"]})
    button_after = next(node for node in moved["nodes"] if node["id"] == button["id"])
    assert button_after["parentId"] == logic["id"]
    assert button_after["path"] == "myapp.logic.button"

    linked = session.apply({"action": "relate", "from": card["id"], "to": button["id"], "type": "depends_on", "note": "The card uses refresh"})
    relation = next(edge for edge in linked["relations"] if edge["from"] == card["id"] and edge["to"] == button["id"] and edge["type"] == "depends_on")
    assert relation["intent"] == "The card uses refresh"
    assert linked["runtime"]["fingerprint"] != initial["runtime"]["fingerprint"]
    assert linked["events"][0]["title"]
    assert all(target["emitted"] is False for target in linked["targets"])
