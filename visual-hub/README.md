# Orren Visual Hub

The Visual Hub is Orren's desktop-first, three-pane SIR workspace: a navigable semantic hierarchy, a spatial field/flow/lens, and a meaning inspector. Its supplied emblem and blue-violet/gold visual identity remain intact while the reference MyApp graph now comes from Orren's **real Python Engine**, not hard-coded UI sample state.

## Run locally

From the repository root, with the Orren package dependencies installed:

```bash
python3 visual-hub/server.py
```

Open <http://127.0.0.1:4173>. The server defaults to loopback. To expose a temporary hosted sandbox preview, set the host and port explicitly, for example:

```bash
HOST=0.0.0.0 PORT=4173 python3 visual-hub/server.py
```

## What is connected

- `visual-hub/MyApp.orn` is parsed by `Engine.run()` and becomes the live SIR graph shown in the tree, field, Flow Graph, Dimension Lens, inspector, and Provenance view.
- Nine-dimension bars and the radar are derived from actual SIR payload counts. Their heat/radius is normalized within the current field and is **not a confidence score**. The current SIR schema does not model confidence.
- Create-node, add-behavior, reparent, typed relationship, target add/remove, and refresh-plan actions update the in-memory SIR session using the Engine's semantic editor / realization coordinator.
- Relationship connections are written only after the builder explicitly chooses a type and confirms.
- Provenance lists actions from this server process and uses the Engine's SIR-graph signature. It is not a source-file hash or durable audit log.
- Target cards show the coordinator's real target plan, output-file paths, preservation assessment, and declared bridge needs. These are plans, **not emitted source files**.

## Current boundary

The session is in memory. Restarting the server restores the `.orn` fixture and discards edits; this workbench does not configure persistence or authentication. Source emission remains unavailable because the optional `orren_engine.backends.web_layout` module is absent from this repository revision. The Visual Hub reports that capability gap explicitly and never presents coordinator plans as generated artifacts. The core Engine/SIR editing path remains live.

Run the bridge regression tests with:

```bash
pytest tests/test_visual_hub_runtime.py -q
```
