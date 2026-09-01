# Orren Foundation Language v1

## Purpose

This document defines the foundation of Orren's language after the Zero-Assumption Purification. It goes one level deeper than a list of keywords: it distinguishes what exists in the ontology from how the language writes it and from how the execution pipeline processes it.

The governing rule is:

> **A language construct may expose a primitive without making every implementation mechanism an ontological primitive.**

The language therefore has a small semantic kernel and a larger set of grammatical mechanisms built on that kernel.

---

## 1. The foundation

The purified ontology contains nine primitives in three layers.

### Core

| Primitive | Question answered | Role |
|---|---|---|
| Structure | Where/how is this situated? | Topology, containment, scope, nesting |
| Meaning | What is this? | Typed semantic content |
| Relation | How is it connected? | Semantics of edges |
| Constraint | Under what conditions is it valid? | Conditions, invariants, boundaries |

### Enrichment

| Primitive | Question answered | Role |
|---|---|---|
| Intent | Why is it here? | Purpose/rationale |
| Behavior | What happens? | Executable effect |
| Temporal Scope | When does it apply? | Time, duration, recurrence, validity |

### Meta

| Primitive | Question answered | Role |
|---|---|---|
| Confidence | How certain is this assertion? | Epistemic metadata |
| Provenance | Where did it come from? | Derivation/audit metadata |

The distinction between domain content and system metadata is mandatory. Confidence about a temperature is not part of the temperature's Meaning; it is information about the assertion. Provenance likewise describes the origin of the assertion. fileciteturn0file0L449-L468

---

## 2. The crucial distinction: primitive vs construct

The ontology and the syntax are related but not identical.

The language exposes seven primary constructs:

```text
entity       creates a semantic node
relation     creates a semantic edge
constraint   creates a validity proposition
scope        creates a structural boundary
intent       attaches purpose
behavior     attaches execution semantics
temporal     attaches temporal scope
```

The Core ontology contains **four primitives**, but `scope` is not a fifth semantic substance. Scope is the language's explicit notation for part of **Structure**. Likewise, the keyword `entity` is not itself a new primitive: it is the canonical syntax for creating a node that participates in Structure and has Meaning.

This prevents keyword counting from becoming ontology counting.

---

## 3. The semantic atom

The smallest semantic unit in Orren is a **node with Meaning situated in Structure**.

A node is identified by a stable name within a scope and has a typed Meaning.

Conceptually:

```text
Node = Identity + Meaning + Position
```

where:

- **Identity** is a stable reference mechanism, not an independent ontology primitive.
- **Meaning** is typed semantic content.
- **Position** is supplied by Structure.

A node may additionally carry Enrichment and Meta information.

The language must not allow a node whose only content is an untyped name. A named placeholder is structural syntax, not yet a complete semantic entity.

---

## 4. Meaning must be typed

This is the most important refinement over the first purified syntax.

The expression:

```orn
entity sensor: device = "soil moisture sensor"
```

contains three different things:

```text
sensor                      identity
       device                semantic classification
              "soil ..."    Meaning value
```

The right-hand side is therefore not merely prose. It is a value belonging to a semantic type.

Orren must support at least these foundational value categories:

```text
literal       concrete value: text, number, boolean, quantity
reference     reference to another semantic node
expression    computed or symbolic value
collection    finite group of values/references
```

These are **value categories**, not new ontological primitives. They are required to express Meaning without creating another taxonomy of dimensions.

Examples:

```orn
entity temperature: quantity = 25 C
entity controller: device = "irrigation controller"
entity sensor_output: value = controller.reading
entity safe_range: interval = [10 C, 40 C]
```

The exact standard-library type names may evolve; the semantic distinction must not.

---

## 5. Reference is a language mechanism, not an ontology primitive

Relations, constraints, behavior, and expressions all need to refer to nodes.

A canonical reference is therefore required:

```text
reference → identifier | scoped.identifier
```

Examples:

```orn
sensor
irrigation.sensor
system.controller
```

A reference resolves against the nearest visible scope and then outward through enclosing scopes according to lexical visibility rules.

Reference resolution is a **Parse/Construct concern**, not a semantic dimension.

An unresolved reference is an error. Orren must not silently invent a node to make a reference succeed.

---

## 6. Structure and scope

`scope` is the language's explicit structural boundary.

```orn
scope irrigation {
    entity controller: device = "irrigation controller"

    scope sensing {
        entity sensor: device = "soil moisture sensor"
    }
}
```

This creates a structural tree:

```text
irrigation
└── sensing
    └── sensor
```

Scope determines:

- visibility of names;
- containment;
- lifetime of declarations;
- qualification of references.

Structure is not duplicated by another `context` system. The old universal `CONTEXT`, `SCOPE`, and structural hierarchy are consolidated here, consistent with the purification. fileciteturn0file0L499-L511

---

## 7. Entity

Canonical form:

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

An entity declaration establishes a node and its Meaning. The type constrains which enrichments and values are valid; it does not create a second ontology.

The minimum valid entity therefore has:

```text
name + type + meaning
```

The type may be a standard-library type or a user-defined semantic type.

---

## 8. Relation

Canonical form:

```orn
relation SOURCE -> TARGET: TYPE
```

Optional qualification:

```orn
relation sensor -> controller: dependency
relation sensor -> controller: dependency when controller.active
```

A relation is an edge whose **type is itself Meaning** about the connection.

Therefore:

```text
Structure says: an edge exists.
Relation says: what that edge means.
```

This preserves the distinction made in the purification between graph topology and the semantic role of an edge. fileciteturn0file0L397-L407

The relation target and source must resolve to existing entities.

---

## 9. Constraint

A constraint is a proposition over entities, relations, values, or scopes.

Canonical form:

```orn
constraint sensor.value > 0
```

Examples:

```orn
constraint temperature >= 0 C
constraint controller.active implies sensor.available
constraint relation(sensor, controller, dependency) implies controller.enabled
```

A constraint does not execute behavior. It states what must hold.

The Resolve stage consumes constraints and attempts to find an interpretation satisfying them to the maximum supported extent. fileciteturn0file0L617-L622

### Constraint classes

These are grammatical/evaluation categories, not ontology primitives:

```text
assertion       must hold
implication     if A then B
exclusion      A and B cannot both hold
requirement    A must exist/be satisfied
```

The language may expose these as operators rather than keywords.

---

## 10. Intent

Intent answers **why**.

```orn
entity controller: device = "irrigation controller" {
    intent "maintain safe soil moisture"
}
```

Intent is enrichment. It does not alter graph topology and does not automatically create behavior.

The purification explicitly collapses the former intent attribute, intent-layer hierarchy, and cognitive `intend` operation into this single semantic concept. fileciteturn0file0L421-L429

---

## 11. Behavior

Behavior answers **what happens when activated or realized**.

```orn
entity controller: process = "irrigation controller" {
    behavior "open valve when soil is dry"
}
```

Behavior is the bridge from declarative semantic structure to executable realization. It is enrichment because many entities have Meaning but no executable effect. fileciteturn0file0L430-L440

At foundation level, behavior must therefore be representable as semantic content. A future execution layer may lower it to a formal action graph; that action graph is not part of the primitive ontology yet.

---

## 12. Temporal Scope

Temporal answers **when**.

```orn
entity irrigation_cycle: process = "watering cycle" {
    temporal "active every morning while soil moisture is below threshold"
}
```

Temporal scope may encode:

```text
ordering       before / after
interval       valid from / until
duration       how long
recurrence     how often
activation     when active
```

These are forms of the single Temporal Scope primitive, not separate dimensions. fileciteturn0file0L441-L448

---

## 13. Metadata is orthogonal

Confidence and Provenance must never be confused with Meaning.

Conceptually:

```text
assertion:
    temperature = 25 C

meta:
    confidence = 0.82
    provenance = ...
```

The language should eventually support metadata syntax, but metadata is not required to make the semantic node itself valid.

A useful future form is:

```orn
entity temperature: quantity = 25 C
    meta confidence 0.82
```

This is intentionally **future syntax**, not required foundation syntax.

---

## 14. Operators are not primitives

Orren will need operators for values and propositions.

Examples:

```text
+  -  *  /  <  <=  >  >=  =  !=
and  or  not  implies
```

These are evaluation mechanisms. They do not enlarge the ontology.

Likewise, functions, pattern matching, loops, collections, modules, imports, and standard-library types are language machinery built on the semantic kernel.

The foundation should resist the historical failure mode of promoting every useful mechanism into a new semantic dimension.

---

## 15. The canonical source grammar

At foundation level, the grammar is intentionally small:

```ebnf
program        = { declaration } ;

declaration    = entity
               | relation
               | constraint
               | scope ;

entity         = "entity" identifier ":" type "=" meaning [ entity_body ] ;

entity_body    = "{" { annotation } "}" ;

annotation     = intent
               | behavior
               | temporal ;

intent         = "intent" value ;
behavior       = "behavior" value ;
temporal       = "temporal" value ;

relation       = "relation" reference "->" reference ":" relation_type
                 [ "when" proposition ] ;

constraint     = "constraint" proposition ;

scope          = "scope" identifier "{" { declaration } "}" ;

meaning        = value
               | expression ;

value          = literal
               | reference
               | collection ;

reference      = identifier { "." identifier } ;
```

This is the **foundation grammar**, not the entire eventual programming language.

It deliberately omits old sections such as `vibe`, `cognitive`, `equilibrium`, `realize`, and `degrade`, because those were identified as domain annotations, pipeline mechanisms, or realization policy rather than foundational language constructs. fileciteturn0file0L571-L585

---

## 16. The five execution boundaries

The language is complete only when its constructs have unambiguous destinations in the execution pipeline:

```text
SOURCE
  │
  ▼
PARSE
  │  syntax → AST
  ▼
CONSTRUCT
  │  entity/relation/constraint/scope
  │  → Core SIR
  ▼
ENRICH
  │  intent/behavior/temporal
  │  → enriched SIR
  ▼
RESOLVE
  │  reference resolution + constraint satisfaction
  │  + conflict resolution
  ▼
REALIZE
  │  resolved semantics → executable representation
  ▼
OUTPUT
```

The purification defines these five responsibilities explicitly: Parse is syntax only; Construct builds Core; Enrich populates enrichment; Resolve handles constraint satisfaction/conflicts; Realize emits executable output. fileciteturn0file0L599-L628

---

## 17. What counts as the roof

The foundation is not considered complete merely because the parser accepts seven keywords.

The roof is reached when the following invariants are true:

### Ontological invariant
Every semantic concept has exactly one canonical home.

### Typing invariant
Every entity has a typed Meaning.

### Reference invariant
Every reference resolves or produces an explicit error.

### Structural invariant
Scope and containment are represented through one Structure model.

### Relational invariant
Edges have explicit semantic Relation types.

### Constraint invariant
Validity conditions are explicit and independent from behavior.

### Enrichment invariant
Intent, Behavior, and Temporal Scope enrich Core semantics without redefining it.

### Meta invariant
Confidence and Provenance describe assertions rather than becoming domain dimensions.

### Pipeline invariant
Each stage has one responsibility and one well-defined input/output boundary.

### Sovereignty invariant
The SIR remains the canonical representation; no backend becomes the architectural definition of Orren. This follows the strongest architectural principle identified in the purification. fileciteturn0file0L768-L786

---

## 18. The foundation example

A complete small program should already be expressible without any specialized extensions:

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

This example uses only the foundation. No vibe system, cognitive taxonomy, mediation layer, equilibrium keyword, realization declaration, or backend declaration is needed to describe the semantics.

---

## 19. Design law

The language follows one governing law:

> **Do not create a new primitive when an existing primitive can express the concept without loss of meaning.**

This is the practical form of purification.

The result is not a language with fewer ideas. It is a language where each idea has one home, each mechanism has a boundary, and each layer depends only on layers beneath it.

That is the foundation on which the compiler, cognitive extensions, multiple realization backends, VM, LSP, and richer standard library can later be built.
