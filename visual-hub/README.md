# Orren Visual Hub — first visual proof

A dependency-free, browser-runnable prototype of the **Living SIR Field + Semantic Tree** milestone from [`docs/VISUAL_HUB.md`](../docs/VISUAL_HUB.md). It follows the supplied reference: a cinematic Orren landscape around a gold-edged glass phone, a glowing branching field, and the focused node's dimension/realization inspector. The supplied Orren emblem and blue / violet / luminous-gold identity are carried through the interface.

## Run it

From the repository root:

```bash
python3 -m http.server 4173 --directory visual-hub
```

Then open <http://localhost:4173>.

## Try the milestone

1. The default field shows `MyApp` branching to `UI` and `Logic`, `Dashboard` and `WeatherService`, and `Button`, `Card`, and `Chart`.
2. `Button` is selected with the behavior “Triggers weather data fetch and updates the dashboard.” Its Web realization is current at a derived path.
3. Choose **Start with an empty field** (the plus button at the top right) to create your own structure.
4. Add nodes, behavior, and a web target, then drag nodes to restructure and observe derived paths update.
5. Explore the Flow Graph, Dimension Lens, Realization View, and Provenance Trail. They all render the same in-memory field.

**Prototype boundary:** state lives in memory in this browser tab. The Visual Producer and Observer are UI-level demonstrations; no SIR engine, persistence, voice input, compiler, or artifact backend is connected yet. Realization marks a derived artifact as current in the prototype; it does not generate a source file.
