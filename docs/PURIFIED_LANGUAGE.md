# Orren Purified Language

**Status: canonical language proposal implemented by `PurifiedParser`**

This specification is derived from **Zero-Assumption Orren Purification**. The purpose is to give Orren one authoritative language vocabulary instead of maintaining multiple competing taxonomies.

## 1. Ontological foundation

Orren's semantic ontology has three layers:

### Core

1. **Structure** — graph topology, containment, scope, and nesting.
2. **Meaning** — what a semantic entity represents.
3. **Relation** — the semantic role of an edge between entities.
4. **Constraint** — conditions and boundaries required for validity.

### Enrichment

5. **Intent** — why a construct exists.
6. **Behavior** — what happens when it is activated or realized.
7. **Temporal Scope** — when it is valid, active, or relevant.

### Meta

8. **Confidence** — certainty about a semantic assertion.
9. **Provenance** — origin and derivation history.

Meta information is deliberately not part of the seven core language constructs. It describes the semantic system rather than the modeled domain.

## 2. Language constructs

The language has exactly seven semantic constructs.

| Layer | Construct | Purpose |
|---|---|---|
| Core | `entity` | Declare a semantic node with a Meaning. |
| Core | `relation` | Declare a typed semantic edge between entities. |
| Core | `constraint` | Declare a condition that must be satisfied. |
| Core | `scope` | Declare a contextual/visibility boundary. |
| Enrichment | `intent` | State the purpose or rationale of a construct. |
| Enrichment | `behavior` | State what the construct does when activated/realized. |
| Enrichment | `temporal` | State when the construct applies or remains active. |

These are constructs, not dimensions. The language must not reintroduce the old nine-dimensional node model through syntax.

## 3. Canonical syntax

### Entity

```orn
entity sensor: device = "soil moisture sensor" {
    intent "measure soil moisture"
    behavior "emit measurement"
    temporal "active while the controller is running"
}
```

An entity always has a name, type, and Meaning. Enrichment annotations are optional unless required by the entity type.

### Relation

```orn
relation sensor -> controller: dependency
```

The relation type gives semantic significance to the graph edge. Common relation types include `causality`, `dependency`, `sequence`, `containment`, and `equivalence`, while user-defined relation types remain possible.

A relation may carry a condition:

```orn
relation sensor -> controller: dependency when controller.active
```

### Constraint

```orn
constraint sensor.value > 0
```

Constraints may apply to an entity, a relation, or the graph as a whole. They are consumed by the Resolve pipeline stage.

### Scope

```orn
scope irrigation {
    entity controller: process = "irrigation controller"
}
```

Scopes provide contextual boundaries, visibility, nesting, and lifetime. They replace the former universal `context` attribute as a first-class language concept.

### Enrichment

```orn
entity controller: process = "irrigation controller" {
    intent "maintain irrigation conditions"
    behavior "regulate water delivery"
    temporal "active during the irrigation cycle"
}
```

`intent` describes **why**, `behavior` describes **what happens**, and `temporal` describes **when**.

## 4. What is no longer a language-core construct

The following concepts are intentionally removed from the language core:

- `vibe`
- `cognitive`
- `equilibrium`
- `realize`
- `degrade`
- the ten cognitive domains
- the five mediation layers
- the six intent layers
- the old eight universal foundation attributes
- the nine-dimensional SIR node taxonomy

This does not declare those concepts useless. They belong in extensions, libraries, metadata, or pipeline stages where appropriate.

In particular, **Equilibrium is a process, not a node property**. It belongs to Resolve. Cognitive domains belong to processing operations. Mediation layers belong to the pipeline. Domain-specific qualities such as Vibe and Spatial semantics belong to qualified annotations/extensions.

## 5. Processing model

The purified language maps onto a five-stage semantic execution pipeline:

```text
Source
  │
  ▼
Parse       → AST; syntax only
  │
  ▼
Construct   → Core SIR: Structure, Meaning, Relation, Constraint
  │
  ▼
Enrich      → Intent, Behavior, Temporal Scope
  │
  ▼
Resolve     → constraint satisfaction and conflict resolution
  │
  ▼
Realize     → executable output
```

The Semantic Intermediate Representation remains the canonical representation. No backend is the reference implementation.

## 6. Migration rule

The old `.orn` syntax remains available through the legacy `CoParser` while migration is underway. New language work must target `PurifiedParser` and the seven-construct vocabulary.

The working Python backend remains the first realization target. Additional backends are extensibility points, not first-class architectural requirements.
