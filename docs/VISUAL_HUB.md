# ORREN — The Visual Hub

**Status:** Canonical architectural addendum to the Orren architecture.

The Visual Hub extends the surface-form and CLI mediation architecture with Orren's visual half: a live semantic map through which a builder can see, navigate, and shape the SIR field.

## XV.1 Identity

Orren has two complementary halves:

- **Semantic Engine** — parses, refines, resolves, and realizes meaning.
- **Visual Hub** — renders the SIR field so the builder can see and shape semantic structure.

The Visual Hub is **not** a file explorer, conventional code editor, or static dashboard. It is a semantic map. Files, paths, and source code are realizations derived from meaning and are therefore secondary.

## XV.2 Core principles

1. **Structure is visible.** The builder can see the semantic tree, relationships, and flows.
2. **Paths are derived.** The builder creates and places semantic nodes rather than manually constructing implementation paths. Paths follow semantic hierarchy and realization target.
3. **Dimensions are progressive.** All nine dimensions remain present in the SIR model, while the visual surface reveals relevant dimensions progressively and makes the remainder available on demand.

## XV.3 Five live views

All views render the same living SIR field.

### 1. Semantic Tree

The default hierarchical view of meaning.

- `◈` structural/container node
- `◉` behavioral node
- `◇` realization target
- Click a node to inspect its dimensions.
- Right-click to propose a resolution, request realization, add a child, or connect nodes.
- Dragging restructures semantic hierarchy.
- Typing a name creates a node and lets Orren derive implementation paths.

### 2. Flow Graph

Shows data, behavioral, realization, and temporal movement. Hovering highlights edges; selecting an edge exposes its semantic relationship. Drawing a new edge creates a relationship proposal whose type can be inferred by Orren.

### 3. Dimension Lens

Combines the semantic tree with a dimensional heatmap/radial profile. Builders can filter by dimension and compare nodes without turning the tree into a nine-dimension text dump.

### 4. Realization View

Shows which realizations exist for each semantic node and whether artifacts are current, stale, degraded, or missing. A builder can inspect an artifact, view a capability gap, or request realization.

### 5. Provenance Trail

Shows the semantic history of a node: producer, refiners, resolvers, realizers, timestamps, and source hash. It connects realized artifacts back to semantic origin and supports inspection of prior SIR state.

## XV.4 Visual agents

### Visual Producer

A Producer agent that injects builder actions into the SIR field.

- Create node → semantic node with high-confidence initial intent and derived path.
- Drag node → restructuring proposal.
- Draw edge → relationship node.
- Type name → named node with inferred dimensions.
- Toggle dimension → dimension enrichment.

The Visual Producer does not assume semantic authority. It records what the builder did and lets the field refine and resolve the result.

### Visual Observer

An Observer agent that renders the current field and identifies what the builder needs to see.

It watches for new nodes, resolutions, artifacts, low-confidence nodes, capability gaps, focus, selection, and hover state. It is read-only with respect to semantic content: it renders and never modifies the field directly or blocks another agent.

## XV.5 Path-free construction

A node is created from semantic placement, not a manually entered implementation path.

Example:

1. Create `MyApp`.
2. Place `UI` under it.
3. Place `Button` under `UI`.
4. Orren derives the realization path for each target.
5. Add behavior such as `Make it fetch the weather`.
6. Realize the target.

For a web target, `Button` may derive a path such as `src/ui/Button.tsx`. If the node is moved under `Controls`, the realization path becomes `src/controls/Button.tsx` without requiring the builder to rewrite the path manually.

The same principle applies across realization targets, including Android and logic backends: semantic hierarchy is the source of path derivation.

## XV.6 Progressive dimensional display

The visual surface uses progressive disclosure:

- **Level 1:** node richness/radial profile.
- **Level 2:** side panel with values, confidence, and provenance.
- **Level 3:** dimension filtering.
- **Level 4:** node comparison.
- **Level 5:** equilibrium overlay showing conflicts, proposals, and resolution status.

The tree does not display all nine dimensions as text. Visual richness communicates structure at a glance; detailed semantic information remains one interaction away.

## XV.7 Interaction modes

The Visual Hub is one of Orren's surface forms. The builder may interact through:

- **Click** — inspect and select.
- **Drag** — restructure and connect.
- **Speak** — express intent conversationally.
- **Type** — precise semantic naming and input.
- **Draw** — create relationships visually.

None of these is canonical. Every interaction feeds the same SIR field.

## XV.8 Staying oriented

The Visual Hub prevents semantic work from disappearing behind implementation details:

1. The whole semantic structure remains visible.
2. Structure and dimensional inspection use distinct views.
3. Nothing depends on manually navigating implementation paths.
4. The hub updates live as speech, code, agents, and resolvers change the field.

## XV.9 Relationship to Speech and CLI

| Surface | Strength | Limitation |
|---|---|---|
| Speech | Fast, interactive, conversational intent | Less precise for exact structural work |
| CLI | Precise, composable, scriptable automation | Poorer discovery and navigation |
| Visual Hub | Structural, navigable, holistic understanding | Less suited to rapid-fire commands |

A typical multimodal loop can therefore be:

**Speak** an application intent → the semantic tree grows → **click** a node → adjust its Vibe → realization artifacts become stale → **realize** → use the **CLI** for precise preview/automation → the hub marks the artifacts current.

## XV.10 Anti-patterns

The Visual Hub must not become:

- a file explorer disguised as a semantic tool;
- a conventional code editor with semantic labels;
- a nine-dimension text dump;
- a path-entry workflow;
- a static visualization;
- a single-view interface.

The architecture is defined by the semantic tree, flow graph, dimension lens, realization view, and provenance trail operating over one living field.

## XV.11 Extended first milestone

The first visual milestone is:

> **The Living SIR Field + The Semantic Tree**

Required deliverables:

- semantic tree;
- Visual Producer;
- Visual Observer;
- semantic path derivation;
- one realization view.

Acceptance scenario:

1. Open an empty hub.
2. Create `MyApp`, `UI`, and `Button`.
3. Speak: `Make it fetch the weather`.
4. Observe `Button` gaining Behavioral meaning.
5. Add a web realization target.
6. Realize and observe the derived `src/ui/Button.tsx` artifact.
7. Drag `Button` under `Controls`.
8. Observe the derived realization path update to `src/controls/Button.tsx`.

If this passes, the visual half of Orren has its first concrete proof.

## XV.12 Architectural sentence

> **The Visual Hub is the seeing half of Orren: a live, multi-view, path-free semantic map of everything the builder is creating, where structure is visible, paths are derived, dimensions are progressive, and meaning is never lost in the act of building.**

## XV.13 Closing principle

The Semantic Engine works in the dark; the Visual Hub makes the work visible.

- **Tree** holds structure.
- **Flow graph** shows movement.
- **Dimension lens** exposes meaning.
- **Realization view** shows output.
- **Provenance trail** preserves history.

The builder speaks; the engine parses; the field resolves; the hub shows; the builder refines; the system realizes.

**Meaning remains primary. Vision makes meaning navigable. Structure makes vision usable.**
