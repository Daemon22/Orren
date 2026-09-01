# Orren Purified Language

**Status: foundation specification**

This specification is derived from **Zero-Assumption Orren Purification**. It defines the smallest language capable of expressing the purified ontology without recreating the old competing taxonomies.

## 1. Ontology

Orren has three strictly ordered semantic layers:

### Core

1. **Structure** — topology, containment, nesting, scope.
2. **Meaning** — typed semantic content: what a node represents.
3. **Relation** — semantic significance of connections between nodes.
4. **Constraint** — conditions and boundaries under which semantics are valid.

### Enrichment

5. **Intent** — why a construct exists.
6. **Behavior** — what happens when activated or realized.
7. **Temporal Scope** — when a construct is valid, active, or relevant.

### Meta

8. **Confidence** — certainty about a semantic assertion.
9. **Provenance** — origin and derivation history.

The purification establishes these as one canonical ontology rather than parallel taxonomies. fileciteturn0file0L371-L376

## 2. Constructs are not primitives

The language exposes seven primary constructs:

| Layer | Construct | Role |
|---|---|---|
| Core | `entity` | Creates a semantic node with typed Meaning. |
| Core | `relation` | Creates a semantically typed edge. |
| Core | `constraint` | Creates a validity proposition. |
| Core | `scope` | Explicit syntax for Structure's contextual boundary. |
| Enrichment | `intent` | Attaches purpose. |
| Enrichment | `behavior` | Attaches executable behavior. |
| Enrichment | `temporal` | Attaches Temporal Scope. |

`scope` is not a fifth Core primitive. It is syntax for Structure. Likewise, `entity` is syntax for creating a node that participates in Structure and has Meaning.

This distinction is essential: **the number of language keywords is not the number of ontological primitives.**

## 3. The semantic atom

A semantic node is conceptually:

```text
Node = Identity + Meaning + Position
```

Identity is a reference mechanism, Position is supplied by Structure, and Meaning is typed semantic content.

A name without Meaning is only a declaration shell. A complete semantic entity therefore requires:

```text
name + type + meaning
```

## 4. Meaning is typed

The first purified proposal was too permissive in treating Meaning as nearly free-form text. The ontology itself requires Meaning to be a typed value. fileciteturn0file0L389-L396

Canonical form:

```orn
entity sensor: device = "soil moisture sensor"
entity temperature: quantity = 25 C
entity controller: device = "irrigation controller"
```

The value side may be one of these foundational categories:

```text
literal       concrete scalar or quantity
reference     another semantic node
expression    computed/symbolic value
collection    group of values or references
```

These are value categories, not additional ontology primitives.

## 5. References

References are required by relations, constraints, behaviors, and expressions.

```text
reference = identifier | identifier "." identifier { "." identifier }
```

Examples:

```orn
sensor
irrigation.sensor
system.controller
```

Resolution is lexical and scope-aware. An unresolved reference is an explicit error; the system must not silently invent a node.

## 6. Scope and Structure

```orn
scope irrigation {
    entity controller: device = "irrigation controller"

    scope sensing {
        entity sensor: device = "soil moisture sensor"
    }
}
```

Scope supplies:

- visibility;
- containment;
- lifetime;
- qualification of references.

This replaces the former universal `context` attribute with explicit structure, consistent with the purification. fileciteturn0file0L499-L511

## 7. Entity

```orn
entity NAME: TYPE = MEANING
```

Optional enrichment:

```orn
entity NAME: TYPE = MEANING {
    intent "..."
    behavior "..."
    temporal "..."
}
```

`entity` creates a semantic node. Its type constrains which values and enrichments are meaningful; it does not create another ontological layer.

## 8. Relation

```orn
relation SOURCE -> TARGET: TYPE
```

Optional condition:

```orn
relation sensor -> controller: dependency when controller.active
```

Structure answers whether the edge exists. Relation answers what the edge means. This preserves the distinction established by the purification. fileciteturn0file0L397-L407

Common relation types include:

```text
causality
 dependency
sequence
containment
equivalence
```

User-defined relation types remain permitted.

## 9. Constraint

```orn
constraint sensor.value > 0
constraint controller.active implies sensor.available
```

Constraints are propositions over semantic values, entities, relations, or scopes. They are consumed by the Resolve stage and are independent from behavior.

## 10. Enrichment

### Intent

```orn
intent "maintain safe soil moisture"
```

Intent answers **why**. It enriches semantics and does not inherently alter topology or execute behavior. The purification collapses the former intent attribute, intent layers, and `intend` cognitive operation into one concept. fileciteturn0file0L421-L429

### Behavior

```orn
behavior "open or close water flow"
```

Behavior answers **what happens** and provides the bridge to realization. fileciteturn0file0L430-L440

### Temporal

```orn
temporal "active during the irrigation cycle"
```

Temporal Scope unifies ordering, duration, recurrence, validity, and activation without reintroducing multiple temporal dimensions. fileciteturn0file0L441-L448

## 11. Meta

Confidence and Provenance are orthogonal metadata:

```text
assertion:
    temperature = 25 C

meta:
    confidence = 0.82
    provenance = ...
```

They describe the assertion rather than changing its domain Meaning. The purified ontology explicitly places them in the Meta layer. fileciteturn0file0L449-L468

Metadata syntax is intentionally left outside the foundation grammar until its semantics and persistence contract are fixed.

## 12. What is outside the foundation language

These are **not** foundation constructs:

```text
vibe
cognitive
spatial-as-a-dimension
equilibrium
realize
degrade
mediation layers
cognitive domains
intent layers
```

The purification reclassifies them as annotations, operations, pipeline stages, or future extensions. Equilibrium in particular is a graph-level process, not node state. fileciteturn0file0L342-L362

## 13. Foundation grammar

```ebnf
program        = { declaration } ;

declaration    = entity | relation | constraint | scope ;

entity         = "entity" identifier ":" type "=" meaning [ entity_body ] ;
entity_body    = "{" { annotation } "}" ;

annotation     = intent | behavior | temporal ;
intent         = "intent" value ;
behavior       = "behavior" value ;
temporal       = "temporal" value ;

relation       = "relation" reference "->" reference ":" relation_type
                 [ "when" proposition ] ;
constraint     = "constraint" proposition ;
scope          = "scope" identifier "{" { declaration } "}" ;

meaning        = value | expression ;
value          = literal | reference | collection ;
reference      = identifier { "." identifier } ;
```

This is the foundation grammar, not the entire eventual programming language. Operators, functions, modules, control flow, standard-library types, and realization policy can be built above it without becoming new semantic primitives.

## 14. Execution boundary

The language must map cleanly onto the five processing stages defined by the purification:

```text
SOURCE
  │
  ▼
PARSE       syntax → AST
  │
  ▼
CONSTRUCT   entity/relation/constraint/scope → Core SIR
  │
  ▼
ENRICH      intent/behavior/temporal → enriched SIR
  │
  ▼
RESOLVE     reference + constraint + conflict resolution
  │
  ▼
REALIZE     resolved SIR → executable output
```

The PDF explicitly separates these responsibilities and places equilibrium resolution in the Resolve stage and executable generation in Realize. fileciteturn0file0L599-L628

## 15. Foundation invariants

The foundation is considered sound only when all of these hold:

1. **Ontological uniqueness** — every semantic concept has one canonical home.
2. **Typed Meaning** — every entity has typed semantic content.
3. **Reference closure** — every reference resolves or fails explicitly.
4. **Single Structure model** — scope, nesting, containment, and visibility do not use parallel systems.
5. **Semantic edges** — every relation has an explicit type.
6. **Independent constraints** — validity is represented independently of behavior.
7. **Layered enrichment** — Intent, Behavior, Temporal Scope augment Core but do not redefine it.
8. **Orthogonal metadata** — Confidence and Provenance describe assertions rather than domain meaning.
9. **Pipeline separation** — each stage has one responsibility.
10. **SIR sovereignty** — SIR remains the canonical representation and no backend defines the semantics. fileciteturn0file0L768-L786

## 16. Foundation example

```orn
scope irrigation {
    entity sensor: device = "soil moisture sensor" {
        intent "measure current soil moisture"
        behavior "produce a moisture reading"
        temporal "active while the system is running"
    }

    entity controller: process = "irrigation controller" {
        intent "maintain safe soil moisture"
        behavior "open or close water flow"
        temporal "active during the irrigation cycle"
    }

    relation sensor -> controller: dependency
    relation controller -> sensor: reads

    constraint sensor.reading >= 0
    constraint sensor.reading <= 100
    constraint controller.active implies sensor.available
}
```

This describes a meaningful semantic system without importing the old nine-dimensional SIR taxonomy into the language.

## 17. Governing law

> **Do not create a new primitive when an existing primitive can express the concept without loss of meaning.**

The foundation is therefore not defined by how many keywords exist. It is defined by whether each concept has one home, whether every construct has a clear semantic interpretation, and whether the resulting representation can pass through Parse → Construct → Enrich → Resolve → Realize without ambiguity.
