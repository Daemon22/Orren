# Orren Visual Hub — first visual proof

A dependency-free, browser-runnable prototype of the **Living SIR Field + Semantic Tree** milestone from [`docs/VISUAL_HUB.md`](../docs/VISUAL_HUB.md). The supplied Orren artwork informs the emblem and the blue / violet / luminous-gold interface palette.

## Run it

From the repository root:

```bash
python3 -m http.server 4173 --directory visual-hub
```

Then open <http://localhost:4173>.

## Try the milestone

1. Choose **Start with an empty field** (the plus button at the top right).
2. Add `MyApp`, then add `UI` and `Button` beneath the selected node.
3. Select `Button`; in **Add meaning**, enter `Make it fetch the weather` and choose **Add behavior**.
4. Choose **Add web target**, then **Realize**. The path is derived as `src/ui/Button.tsx`.
5. Add `Controls` under `MyApp`, drag `Button` onto it, and observe the path update to `src/controls/Button.tsx`.
6. Explore the Flow Graph, Dimension Lens, Realization View, and Provenance Trail. They all render the same in-memory field.

**Prototype boundary:** state lives in memory in this browser tab. The Visual Producer and Observer are UI-level demonstrations; no SIR engine, persistence, voice input, compiler, or artifact backend is connected yet. Realization marks a derived artifact as current in the prototype; it does not generate a source file.
