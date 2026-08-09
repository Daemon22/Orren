"""Smoke test: does the engine import and run end-to-end?"""
import sys
sys.path.insert(0, "/home/z/my-project")

from orren_engine import Engine

SOURCE = """create mic_app : Application

    context:
        purpose: a microphone control

    structure:
        home
            microphone_control

    cognitive:
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone = calm

    realize:
        target: web_interface (HTML/CSS/JS)
            capabilities: layout, color, event_handling
            can_express: spatial, conditional, behavioral
            needs_bridge: device_microphone
            cannot_express: aesthetic
            preservation_score: 0.83
"""

if __name__ == "__main__":
    engine = Engine()
    result = engine.run(SOURCE)
    print(result.summary())
    print()
    print("=== All SIR nodes ===")
    for node in result.graph.nodes:
        print(f"  {node.path} ({node.kind})")
        for dim in __import__("orren_engine").data_model.Dimension:
            payload = node.get_dimension(dim)
            if payload:
                print(f"    {dim.value}: {len(payload)} entries")
                for p in payload:
                    print(f"      - {p}")
    print()
    print("=== Realization artifacts ===")
    for art in result.artifacts:
        print(f"  target: {art.target_name} ({art.target_language})")
        print(f"    score: {art.preservation_score}")
        for d in art.degradation_report:
            print(f"    - {d}")

