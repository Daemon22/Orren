# Orren — Implementation Status

The canonical architecture defines Orren as a meaning-first semantic mediator. The concrete runtime architecture selects Python asyncio, SQLite WAL, FastAPI/WebSocket, and a no-build visual hub for the first demonstrable build.

This implementation preserves the existing orren_engine compiler and realization system. The new runtime is a field-mediated execution layer, not a replacement.

Implemented in this vertical:
- living in-memory SIR field with canonical snapshot hashes;
- SIR and resolution nodes with provenance;
- non-destructive resolution state;
- cooperative event/bus model;
- structural text producer;
- grounding/conflict agent hooks;
- Bash and Python realization adapters;
- semantic path derivation;
- SQLite WAL snapshots and artifact records;
- Visual Producer and Observer;
- FastAPI/WebSocket hub;
- Semantic Tree live surface;
- end-to-end regression coverage.

The other Visual Hub surfaces share the same state contract but are intentionally staged after the Semantic Tree, matching the architecture's progressive milestone.
