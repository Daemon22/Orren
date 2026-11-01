# Orren — Concrete Runtime Architecture v0.1

This repository companion records the supplied concrete runtime architecture.

## Runtime decisions

- Python 3.12+ / asyncio
- SQLite with WAL mode
- FastAPI + WebSocket
- single no-build browser hub
- minimal .orn structural parser for the first slice
- multi-process infrastructure deferred

## Runtime structure

The runtime consists of an in-memory SIR field, event bus, cooperative agent tasks, SQLite persistence, FastAPI/WebSocket transport, and a visual hub. The defining rule is that agents subscribe to field changes and write results back to the field. The field is the inbox and API.

## Mutation cycle

1. Mutate the field.
2. Emit a field-change event.
3. Fan the event to subscribers.
4. Let interested agents work cooperatively.
5. Check convergence.
6. Persist snapshots and provenance.

If an agent cannot proceed, it emits a proposal or low-confidence state and returns; it never waits for another agent.

## Demonstrable path

Slice 0 proves the field, persistence, and non-destructive resolution. Slice 1 connects the text producer, refiners, resolver, Bash/Python realizers, persistence, and provenance. Slice 2 adds the live Semantic Tree hub and visual producer/observer. Slice 3 adds the CLI vertical.

The current branch implements the first living field plus the first visual slice. Later surfaces remain staged rather than being claimed as complete.

The supplied runtime PDF remains the implementation reference; this file makes the decisions reviewable inside the repository.