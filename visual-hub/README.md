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
- The legacy local routes (`/api/field` and `/api/action`) keep one in-memory session for the standalone UI. Studio v1 sessions use the same Engine/editor/coordinator against a separate durable database and command log for each project.
- Relationship connections are written only after the builder explicitly chooses a type and confirms.
- Provenance lists actions from this server process and uses the Engine's SIR-graph signature. It is not a source-file hash or durable audit log.
- Target cards show the coordinator's real target plan, output-file paths, preservation assessment, and declared bridge needs. These are plans, **not emitted source files**.

## Studio project API

Set `ORREN_SERVICE_TOKEN` to a random secret of at least 32 characters when connecting Studio, and set `ORREN_PROJECT_DATA_DIR` to a durable directory mounted only by the Orren service. Configure Studio with `ORREN_API_VERSION=1`. The standalone UI remains loopback-accessible without a token in local development; remote clients must present the bearer token.

- `GET /v1/projects/{projectId}/snapshot` returns `projectId`, monotonically increasing `revision`, and the current `field`.
- `POST /v1/projects/{projectId}/commands` accepts `{"action": {...}}`, requires `If-Match: "<revision>"` and an `Idempotency-Key`, and returns the updated envelope.
- Revision mismatches return HTTP 409 with `currentRevision`. Reusing a key with the same action returns its saved result; using it with another action returns HTTP 409.
- Project IDs are hashed before becoming SQLite filenames. SQLite stores each materialized Orren SIR revision and a replayable command log so the live graph and event timestamps recover after restart.
- Keep one Orren server process as the writer for a project data directory. The in-process session locks do not coordinate multiple Orren worker processes; multi-process deployment needs a shared transactional store and distributed locking.

The default `/api/field` standalone session is still in memory. Source emission remains unavailable because the optional `orren_engine.backends.web_layout` module is absent from this repository revision. The Visual Hub reports that capability gap explicitly and never presents coordinator plans as generated artifacts.

Run the bridge regression tests with:

```bash
pytest tests/test_visual_hub_runtime.py -q
```
