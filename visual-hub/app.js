(() => {
  const dimensionNames = ["Expression", "Cognitive", "Vibe", "Spatial", "Temporal", "Relational", "Conditional", "Behavioral", "Equilibrium"];
  const viewInfo = {
    tree: { title: "Semantic field", subtitle: "The map shows structure; use the left tree to reshape it.", icon: "◈" },
    flow: { title: "Flow graph", subtitle: "Follow behavioral, data, and realization movement.", icon: "⌁" },
    lens: { title: "Dimension lens", subtitle: "Reveal where meaning is strongest across the field.", icon: "◉" },
    realizations: { title: "Realizations", subtitle: "Artifacts follow semantic intent; paths are derived.", icon: "◇" },
    provenance: { title: "Provenance", subtitle: "Trace each preview change back to its semantic origin.", icon: "◷" }
  };
  const baseProfile = (expression, cognitive, vibe, spatial, temporal, relational, conditional, behavioral, equilibrium) => ({ Expression: expression, Cognitive: cognitive, Vibe: vibe, Spatial: spatial, Temporal: temporal, Relational: relational, Conditional: conditional, Behavioral: behavioral, Equilibrium: equilibrium });
  const defaults = () => ({
    nodes: [
      { id: "myapp", name: "MyApp", parentId: null, kind: "Semantic root", confidence: null, behavior: "", webTarget: false, realization: "missing", profile: baseProfile(.94,.86,.82,.38,.21,.57,.18,.22,.71) },
      { id: "ui", name: "UI", parentId: "myapp", kind: "Structure", confidence: null, behavior: "", webTarget: false, realization: "missing", profile: baseProfile(.82,.72,.88,.75,.25,.59,.18,.29,.66) },
      { id: "logic", name: "Logic", parentId: "myapp", kind: "Structure", confidence: null, behavior: "", webTarget: false, realization: "missing", profile: baseProfile(.77,.88,.65,.43,.58,.82,.62,.68,.70) },
      { id: "dashboard", name: "Dashboard", parentId: "ui", kind: "Interface", confidence: null, behavior: "", webTarget: false, realization: "missing", profile: baseProfile(.88,.75,.76,.82,.63,.78,.30,.51,.69) },
      { id: "weather", name: "WeatherService", parentId: "logic", kind: "Service", confidence: null, behavior: "Fetches the latest weather conditions.", webTarget: false, realization: "missing", profile: baseProfile(.78,.89,.70,.43,.85,.88,.71,.91,.74) },
      { id: "button", name: "Button", parentId: "dashboard", kind: "Behavioral node", confidence: null, behavior: "Triggers weather data fetch and updates the dashboard.", webTarget: true, realization: "current", profile: baseProfile(.82,.68,.76,.62,.71,.58,.63,.91,.69) },
      { id: "card", name: "Card", parentId: "dashboard", kind: "Component", confidence: null, behavior: "Presents the latest weather summary.", webTarget: false, realization: "missing", profile: baseProfile(.85,.72,.78,.81,.52,.69,.28,.60,.68) },
      { id: "chart", name: "Chart", parentId: "dashboard", kind: "Component", confidence: null, behavior: "Visualizes temperature across the day.", webTarget: false, realization: "missing", profile: baseProfile(.81,.80,.72,.83,.91,.74,.24,.67,.65) }
    ],
    relations: [
      { from: "button", to: "weather", type: "triggers", label: "triggers", intent: "Button requests the latest weather." },
      { from: "weather", to: "card", type: "feeds", label: "feeds", intent: "Weather data refreshes the summary card." },
      { from: "weather", to: "chart", type: "feeds", label: "feeds", intent: "Weather data supplies the daily chart." }
    ],
    events: [
      { title: "Button realized for web", description: "Example artifact at src/ui/dashboard/Button.tsx.", nodeId: "button", time: "example", source: "Sample" },
      { title: "Button gained behavioral meaning", description: "Triggers weather data fetch and updates the dashboard.", nodeId: "button", time: "example", source: "Sample" },
      { title: "WeatherService joined Logic", description: "A service now carries the weather flow.", nodeId: "weather", time: "example", source: "Sample" },
      { title: "Dashboard joined UI", description: "The semantic surface now contains Button, Card, and Chart.", nodeId: "dashboard", time: "example", source: "Sample" },
      { title: "MyApp entered the field", description: "The example opens interface and logic branches.", nodeId: "myapp", time: "example", source: "Sample" }
    ],
    selectedId: "button",
    selectedRelation: null,
    view: "tree",
    filter: "all",
    lensDimension: "Behavioral",
    connectMode: false,
    linkSource: null,
    pendingRelation: null,
    compareIds: [],
    inspectorOpen: true,
    runtime: null,
    targets: [],
    availableTargets: []
  });

  let state = defaults();
  let toastTimer;
  let draggedId = null;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  const nodeById = id => state.nodes.find(node => node.id === id);
  const selectedNode = () => nodeById(state.selectedId) || state.nodes[0] || null;
  const childNodes = parentId => state.nodes.filter(node => node.parentId === parentId);
  const latest = () => state.events[0];
  const slug = value => value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "node";
  const labelCase = value => String(value || "").replace(/[_-]+/g, " ").replace(/\b\w/g, ch => ch.toUpperCase());

  function lineageFor(node) {
    const result = [];
    let cursor = node;
    const guard = new Set();
    while (cursor && !guard.has(cursor.id)) {
      guard.add(cursor.id);
      result.unshift(cursor);
      cursor = nodeById(cursor.parentId);
    }
    return result;
  }
  function derivedPath(node) {
    if (!node?.webTarget) return "";
    const lineage = lineageFor(node);
    const folders = lineage.slice(1, -1).map(entry => slug(entry.name));
    const folderPath = folders.length ? `${folders.join("/")}/` : "";
    const filename = node.name.trim().replace(/[^A-Za-z0-9_-]+/g, "") || "Node";
    return `src/${folderPath}${filename}.tsx`;
  }
  function addEvent(title, description, nodeId, source = "Visual Producer · preview") {
    state.events.unshift({ title, description, nodeId, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), source });
    state.events = state.events.slice(0, 40);
  }
  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 3200);
  }
  function profileScore(node) {
    const values = Object.values(node?.profile || {}).filter(value => Number.isFinite(value));
    return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length * 100) : 0;
  }
  function dimensionCoverage(node) {
    return dimensionNames.filter(name => Number(node?.dimensionCounts?.[name]) > 0).length;
  }
  function richnessLabel(node) {
    return node?.dimensionCounts ? `${dimensionCoverage(node)}/9 dims` : `${profileScore(node)}% richness`;
  }
  function dimensionValueLabel(node, name) {
    return node?.dimensionCounts ? `${Number(node.dimensionCounts[name]) || 0} entries` : `${Math.round((Number(node?.profile?.[name]) || 0) * 100)}% example`;
  }
  function relativeDimensionValue(node, name) {
    return Math.max(0, Math.min(1, Number(node?.profile?.[name]) || 0));
  }
  function nodeHasDimension(node, dimension) {
    if (dimension === "behavioral") return Boolean(node.behavior);
    if (dimension === "realization") return state.runtime?.connected ? Boolean(node.parentId === null && state.targets.length) : Boolean(node.webTarget);
    if (dimension === "relational") return state.relations.some(edge => edge.from === node.id || edge.to === node.id);
    return true;
  }
  function matchesFilter(node) { return state.filter === "all" || nodeHasDimension(node, state.filter); }
  function glyphFor(node) {
    if (node.webTarget) return "◇";
    if (node.behavior) return "◉";
    return node.parentId === null ? "✳" : "◈";
  }

  function renderSidebarBranch(parentId, depth = 0) {
    return childNodes(parentId).map(node => {
      const selected = node.id === state.selectedId;
      const dimmed = !matchesFilter(node);
      const markerClass = node.webTarget ? "target" : node.behavior ? "behavioral" : "";
      return `<div class="sidebar-tree-entry" role="none"><button class="sidebar-tree-node ${selected ? "is-selected" : ""} ${dimmed ? "is-dimmed" : ""}" type="button" data-select="${escapeHTML(node.id)}" data-sidebar-node="${escapeHTML(node.id)}" style="--depth:${depth}" role="treeitem" aria-selected="${selected}" aria-level="${depth + 1}" aria-grabbed="false" draggable="true" title="Select ${escapeHTML(node.name)}; drag here to propose a hierarchy change"><span class="structure-marker ${markerClass}" aria-hidden="true">${glyphFor(node)}</span><span class="structure-name">${escapeHTML(node.name)}</span><span class="structure-richness" aria-label="${state.runtime?.connected ? "SIR dimension coverage" : "Illustrative sample richness"}">${escapeHTML(richnessLabel(node))}</span></button>${childNodes(node.id).length ? `<div class="sidebar-tree-group" role="group">${renderSidebarBranch(node.id, depth + 1)}</div>` : ""}</div>`;
    }).join("");
  }
  function renderSidebarTree() {
    const roots = state.nodes.filter(node => !node.parentId || !nodeById(node.parentId));
    const target = $("#sidebar-tree");
    target.setAttribute("aria-label", "Semantic hierarchy; changes here propose reparenting");
    target.innerHTML = roots.length ? roots.map(node => {
      const selected = node.id === state.selectedId;
      const markerClass = node.webTarget ? "target" : node.behavior ? "behavioral" : "";
      return `<div class="sidebar-tree-entry" role="none"><button class="sidebar-tree-node ${selected ? "is-selected" : ""} ${matchesFilter(node) ? "" : "is-dimmed"}" type="button" data-select="${escapeHTML(node.id)}" data-sidebar-node="${escapeHTML(node.id)}" style="--depth:0" role="treeitem" aria-selected="${selected}" aria-level="1" aria-grabbed="false" draggable="true" title="Select ${escapeHTML(node.name)}; drag here to propose a hierarchy change"><span class="structure-marker ${markerClass}" aria-hidden="true">${glyphFor(node)}</span><span class="structure-name">${escapeHTML(node.name)}</span><span class="structure-richness">${escapeHTML(richnessLabel(node))}</span></button><div class="sidebar-tree-group" role="group">${renderSidebarBranch(node.id, 1)}</div></div>`;
    }).join("") : `<div class="sidebar-empty">No nodes yet.<br>Start with a root idea.</div>`;
  }

  function treeLayout() {
    const roots = state.nodes.filter(node => !node.parentId || !nodeById(node.parentId));
    const compact = window.matchMedia("(max-width: 640px)").matches;
    const boxWidth = compact ? 132 : 144, boxHeight = compact ? 54 : 58, gapX = compact ? 20 : 24, gapY = compact ? 54 : 60, padX = compact ? 24 : 50, padY = 28;
    const subtreeWidths = new Map();
    const maxDepth = { value: 0 };
    const measure = (node, depth = 0) => {
      maxDepth.value = Math.max(maxDepth.value, depth);
      const children = childNodes(node.id);
      const childWidth = children.reduce((sum, child, index) => sum + measure(child, depth + 1) + (index ? gapX : 0), 0);
      const width = Math.max(boxWidth, childWidth);
      subtreeWidths.set(node.id, width);
      return width;
    };
    const rootWidths = roots.map(root => measure(root));
    const totalWidth = Math.max(boxWidth + padX * 2, rootWidths.reduce((sum, width, index) => sum + width + (index ? gapX * 1.5 : 0), 0) + padX * 2);
    const totalHeight = padY * 2 + (maxDepth.value + 1) * (boxHeight + gapY) - gapY;
    const positions = new Map();
    const place = (node, left, depth) => {
      const ownWidth = subtreeWidths.get(node.id) || boxWidth;
      const cx = left + ownWidth / 2;
      const x = cx - boxWidth / 2;
      const y = padY + depth * (boxHeight + gapY);
      positions.set(node.id, { x, y, cx, top: y, bottom: y + boxHeight });
      const children = childNodes(node.id);
      const childrenWidth = children.reduce((sum, child, index) => sum + (subtreeWidths.get(child.id) || boxWidth) + (index ? gapX : 0), 0);
      let cursor = left + (ownWidth - childrenWidth) / 2;
      children.forEach(child => {
        place(child, cursor, depth + 1);
        cursor += (subtreeWidths.get(child.id) || boxWidth) + gapX;
      });
    };
    let cursor = padX;
    roots.forEach((root, index) => {
      place(root, cursor, 0);
      cursor += rootWidths[index] + gapX * 1.5;
    });
    return { roots, positions, width: totalWidth, height: totalHeight, boxWidth, boxHeight };
  }
  function renderTree() {
    const { roots, positions, width, height, boxWidth, boxHeight } = treeLayout();
    if (!roots.length) return `<div class="graph-empty"><div class="empty-state"><div class="empty-state-inner"><img class="empty-emblem" src="assets/orren-emblem.webp" alt=""><span class="view-overline">THE LIVING SIR FIELD</span><h3>Start with meaning.</h3><p>Create a semantic node, speak an intent, or load the example field. Orren will derive implementation paths from the structure.</p><div class="empty-actions"><button class="small-action" type="button" data-empty="create">＋ Create a node</button><button class="small-action" type="button" data-empty="speak">◖ Speak an intent</button><button class="small-action" type="button" data-empty="open" title="Requires the Orren runtime" disabled>Open a field · runtime offline</button><button class="small-action" type="button" data-empty="example">Load example</button></div><small class="empty-boundary">Local preview only · no SIR engine connection</small></div></div></div>`;
    const structural = state.nodes.filter(node => node.parentId && positions.has(node.parentId) && positions.has(node.id)).map(node => {
      const from = positions.get(node.parentId), to = positions.get(node.id);
      const startY = from.bottom, endY = to.top;
      const curve = Math.max(22, (endY - startY) * .47);
      return `<path class="graph-link" d="M ${from.cx} ${startY} C ${from.cx} ${startY + curve}, ${to.cx} ${endY - curve}, ${to.cx} ${endY}" aria-hidden="true"><title>${escapeHTML(nodeById(node.parentId)?.name)} contains ${escapeHTML(node.name)}</title></path>`;
    }).join("");
    const rels = state.relations.map((edge, index) => {
      const from = positions.get(edge.from), to = positions.get(edge.to);
      if (!from || !to) return "";
      const sx = from.cx, sy = from.y + boxHeight / 2, tx = to.cx, ty = to.y + boxHeight / 2;
      const bend = Math.max(24, Math.abs(tx - sx) * .2);
      const mid = (sx + tx) / 2;
      return `<path class="graph-link relation-link" data-rel-index="${index}" d="M ${sx} ${sy} C ${mid + bend} ${sy - bend}, ${mid - bend} ${ty + bend}, ${tx} ${ty}" marker-end="url(#relation-arrow)" aria-label="${escapeHTML(edge.label)} relationship"><title>${escapeHTML(edge.intent || edge.label)} · select in Flow Graph for details</title></path>`;
    }).join("");
    const nodeHtml = state.nodes.map(node => {
      const pos = positions.get(node.id);
      if (!pos) return "";
      const selected = node.id === state.selectedId;
      const dimmed = !matchesFilter(node);
      const activeSource = node.id === state.linkSource;
      const tone = node.webTarget ? "target" : node.behavior ? "behavioral" : "";
      return `<button class="graph-node ${selected ? "is-selected" : ""} ${dimmed ? "is-dimmed" : ""} ${activeSource ? "is-link-source" : ""} ${node.id === state.selectedId ? "is-live" : ""}" type="button" data-select="${escapeHTML(node.id)}" style="left:${pos.x}px;top:${pos.y}px" aria-label="Select ${escapeHTML(node.name)}, ${escapeHTML(node.kind)}${node.behavior ? ", has behavior" : ""}${node.webTarget ? ", has web realization target" : ""}" title="Select to inspect · use the left structure tree to change hierarchy"><span class="graph-glyph ${tone}" aria-hidden="true">${glyphFor(node)}</span><span class="graph-node-copy"><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)}</small></span><span class="graph-node-meta" title="${state.runtime?.connected ? "SIR dimensions with payloads" : "Illustrative sample profile"}">${escapeHTML(richnessLabel(node))}</span></button>`;
    }).join("");
    return `<div class="graph-caption"><span>SEMANTIC FIELD</span><span>Selection syncs with the left structure tree · reparent there explicitly</span></div><div class="semantic-graph" style="width:${width}px;height:${height}px"><svg class="graph-links" viewBox="0 0 ${width} ${height}" aria-hidden="true"><defs><marker id="relation-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="rgba(170,126,255,.72)"></path></marker></defs>${structural}${rels}</svg>${nodeHtml}</div>`;
  }

  function allRelationships() {
    const treeLinks = state.nodes.filter(node => node.parentId && nodeById(node.parentId)).map(node => ({ from: node.parentId, to: node.id, label: "contains", type: "structure", intent: "Semantic hierarchy" }));
    return [...treeLinks, ...state.relations];
  }
  function renderFlow() {
    const links = allRelationships();
    const rows = links.map((edge, index) => {
      const from = nodeById(edge.from), to = nodeById(edge.to);
      if (!from || !to) return "";
      return `<div class="flow-row" data-link-from="${escapeHTML(from.id)}" data-link-to="${escapeHTML(to.id)}"><button class="flow-node ${state.selectedId === from.id ? "is-selected" : ""}" type="button" data-select="${escapeHTML(from.id)}"><span class="node-glyph">${glyphFor(from)}</span><span class="flow-node-copy"><strong>${escapeHTML(from.name)}</strong><small>${escapeHTML(from.kind)}</small></span></button><button class="flow-edge" type="button" data-rel-index="${index}" aria-label="Inspect ${escapeHTML(edge.label || "relationship")} relationship"><span>${escapeHTML(edge.label || "relates")}</span><b>→</b></button><button class="flow-node ${state.selectedId === to.id ? "is-selected" : ""}" type="button" data-select="${escapeHTML(to.id)}"><span class="node-glyph ${to.behavior ? "behavioral" : ""} ${to.webTarget ? "target" : ""}">${glyphFor(to)}</span><span class="flow-node-copy"><strong>${escapeHTML(to.name)}</strong><small>${escapeHTML(to.kind)}</small></span></button></div>`;
    });
    const behaviors = state.nodes.filter(node => node.behavior).map(node => `<div class="flow-row" data-link-from="${escapeHTML(node.id)}"><button class="flow-node ${state.selectedId === node.id ? "is-selected" : ""}" type="button" data-select="${escapeHTML(node.id)}"><span class="node-glyph behavioral">◉</span><span class="flow-node-copy"><strong>${escapeHTML(node.name)}</strong><small>behavioral node</small></span></button><div class="flow-edge static-edge"><span>intent</span><b>→</b></div><div class="flow-node intent-node"><span class="flow-node-copy"><strong>${escapeHTML(node.behavior)}</strong><small>example behavior · local preview</small></span></div></div>`);
    const root = state.nodes.find(node => !node.parentId);
    const targets = state.runtime?.connected
      ? state.targets.map(target => `<div class="flow-row" data-link-from="${escapeHTML(root?.id || "")}"><button class="flow-node ${state.selectedId === root?.id ? "is-selected" : ""}" type="button" data-select="${escapeHTML(root?.id || "")}"><span class="node-glyph target">◇</span><span class="flow-node-copy"><strong>${escapeHTML(root?.name || "SIR field")}</strong><small>whole-field target</small></span></button><div class="flow-edge static-edge"><span>planned for</span><b>→</b></div><div class="flow-node target-node"><span class="flow-node-copy"><strong>${escapeHTML(target.name)}</strong><small>${escapeHTML(target.language)} · plan only · no files emitted</small></span></div></div>`)
      : state.nodes.filter(node => node.webTarget).map(node => `<div class="flow-row" data-link-from="${escapeHTML(node.id)}"><button class="flow-node ${state.selectedId === node.id ? "is-selected" : ""}" type="button" data-select="${escapeHTML(node.id)}"><span class="node-glyph target">◇</span><span class="flow-node-copy"><strong>${escapeHTML(node.name)}</strong><small>semantic target</small></span></button><div class="flow-edge static-edge"><span>derived path</span><b>→</b></div><div class="flow-node target-node"><span class="flow-node-copy"><strong>${escapeHTML(node.realization === "current" ? "Example artifact" : "Derived target")}</strong><small>${escapeHTML(derivedPath(node))}</small></span></div></div>`);
    const rowHtml = [...rows, ...behaviors, ...targets].join("");
    return `<div class="flow-view"><div class="view-intro"><div><span class="view-overline">DATA · BEHAVIOR · REALIZATION</span><h3>How meaning moves</h3><p>Choose a relationship to see what connects its source and destination. New links require an explicit type proposal.</p></div><span class="view-count-pill">${links.length} links</span></div><div class="flow-filters"><button class="dimension-chip selected" data-flow-filter="all" type="button">All movement</button><button class="dimension-chip" data-flow-filter="structure" type="button">Structure</button><button class="dimension-chip" data-flow-filter="behavior" type="button">Behavior</button><button class="dimension-chip" data-flow-filter="relation" type="button">Relationships</button></div><div class="flow-stage">${rowHtml || '<div class="flow-empty">No movement yet. Create two semantic nodes and propose a typed relationship between them.</div>'}</div></div>`;
  }
  function renderLens() {
    const dimension = state.lensDimension;
    const cards = state.nodes.map(node => {
      const values = dimensionNames.map(name => ({ name, value: relativeDimensionValue(node, name) })).sort((a,b) => b.value - a.value);
      const dominant = values[0]?.value ? values[0].name : "No dimension payload";
      const value = state.runtime?.connected ? Number(node.dimensionCounts?.[dimension]) || 0 : Math.round((Number(node.profile?.[dimension]) || 0) * 100);
      const compared = state.compareIds.includes(node.id);
      const bars = dimensionNames.map(name => `<i class="lens-heat ${name === dimension ? "focused" : ""}" title="${escapeHTML(dimensionValueLabel(node, name))}; heat is relative to the field maximum" style="--heat:${Math.max(5,Math.round(relativeDimensionValue(node, name)*100))}%"></i>`).join("");
      const dominantLabel = state.runtime?.connected ? `${value} ${dimension} entries · ${dimensionCoverage(node)}/9 populated dimensions` : `${value}% example`;
      return `<button class="lens-card ${node.id === state.selectedId ? "is-selected" : ""} ${compared ? "is-compared" : ""}" type="button" data-select="${escapeHTML(node.id)}" aria-pressed="${compared}"><span class="lens-card-top"><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)}</small></span><span class="lens-dominant"><i></i>${escapeHTML(dominant)} leads · ${escapeHTML(dominantLabel)}</span><span class="lens-heatmap" aria-label="Nine-dimension ${state.runtime?.connected ? "SIR payload" : "example"} heatmap">${bars}</span><span class="lens-dim-labels"><span>${node.behavior ? "Behavior" : "Structure"}</span><span>${state.runtime?.connected ? "SIR node" : node.webTarget ? "Web target" : "No target"}</span></span></button>`;
    }).join("");
    const compare = state.compareIds.map(nodeById).filter(Boolean);
    let comparison = state.runtime?.connected ? "Select up to two nodes to compare actual SIR dimension payload counts. These are not confidence scores." : "Select up to two nodes to compare the example profiles. The current runtime does not expose confidence scores.";
    if (compare.length === 1) comparison = `${compare[0].name} selected. Choose one more node to compare.`;
    if (compare.length === 2) comparison = `${compare[0].name}: ${richnessLabel(compare[0])} · ${compare[1].name}: ${richnessLabel(compare[1])}.`;
    const dimButtons = dimensionNames.map(name => `<button class="dimension-chip ${name === dimension ? "selected" : ""}" type="button" data-lens-dimension="${escapeHTML(name)}">${escapeHTML(name)}</button>`).join("");
    return `<div class="lens-view"><div class="view-intro"><div><span class="view-overline">FIELD-WIDE DIMENSION LENS</span><h3>${escapeHTML(dimension)} across the field</h3><p>${state.runtime?.connected ? "Counts are actual SIR payload entries; heat is normalized within this field and is not confidence." : "One dimension becomes the focus; sample shape and richness remain comparable."}</p></div><span class="view-count-pill">${state.nodes.length} nodes</span></div><div class="lens-controls" aria-label="Choose a focused dimension">${dimButtons}</div><div class="lens-grid">${cards || '<div class="flow-empty">Create a semantic node to reveal its dimensional profile.</div>'}</div><div class="lens-compare"><strong>Compare nodes · ${compare.length}/2</strong><p>${escapeHTML(comparison)}</p><button class="small-action" id="clear-compare" type="button" style="margin-top:8px">Clear comparison</button></div></div>`;
  }
  function renderRealizations() {
    if (state.runtime?.connected) {
      const cards = state.targets.map(target => {
        const score = Math.round(Number(target.preservationScore || 0) * 100);
        const files = target.outputFiles.length ? target.outputFiles.map(file => `<li><code>${escapeHTML(file.path)}</code><span>${escapeHTML(file.language)}</span></li>`).join("") : '<li><span>No output-file plan from coordinator.</span></li>';
        const bridge = target.needsBridge.length ? `Bridge required · ${target.needsBridge.join(", ")}` : "No declared external bridge";
        const stateLabel = target.planState === "degraded" ? `Plan only · ${score}% preservation` : "Plan only · current";
        return `<article class="artifact-card engine-plan-card ${target.planState === "degraded" ? "is-degraded" : ""}"><span class="artifact-icon">◇</span><span class="artifact-copy"><strong>${escapeHTML(labelCase(target.name))}<span> · ${escapeHTML(target.language)}</span></strong><small>${escapeHTML(bridge)} · ${target.degradationCount} coordinator finding(s)</small><ul class="plan-files">${files}</ul><small class="artifact-source-note">Coordinator plan only · no source files emitted</small></span><span class="artifact-status ${target.planState === "degraded" ? "status-degraded" : "status-planned"}">${escapeHTML(stateLabel)}</span><div class="artifact-actions"><button type="button" data-action="remove-target" data-target="${escapeHTML(target.id)}">Remove target</button><button type="button" data-action="realize">Refresh plan</button></div></article>`;
      }).join("");
      const available = state.availableTargets.filter(target => !target.present).map(target => `<button type="button" class="small-action" data-action="add-target" data-target="${escapeHTML(target.id)}">＋ ${escapeHTML(labelCase(target.id))} · ${escapeHTML(target.language)}</button>`).join("");
      return `<div class="realizations-view"><div class="view-intro"><div><span class="view-overline">LIVE SIR → REALIZATION PLANS</span><h3>Plans follow the semantic field.</h3><p>These target assessments come from the Orren coordinator. They describe intended outputs; this workspace does not emit files.</p></div><span class="view-count-pill">${state.targets.length} Engine plan${state.targets.length === 1 ? "" : "s"}</span></div><div class="runtime-plan-notice"><strong>${state.runtime.codegenAvailable ? "Source generator available" : "Source generation unavailable"}</strong><p>${escapeHTML(state.runtime.codegenMessage || "The coordinator has not written source files.")} No source files are emitted by this Visual Hub session.</p></div><div class="artifact-list">${cards || '<div class="flow-empty">No realization targets are declared for the live SIR field.</div>'}</div>${available ? `<section class="target-catalog"><strong>Add a target to the field</strong><p>The target applies to the whole SIR graph and produces a coordinator plan, not emitted files.</p><div>${available}</div></section>` : ""}<button class="small-action" id="refresh-plans" type="button">Refresh all plans</button></div>`;
    }
    if (!state.nodes.length) return `<div class="realizations-view"><div class="view-intro"><div><span class="view-overline">MEANING → OUTPUT</span><h3>Realizations</h3><p>Targets will appear here when semantic nodes request a realization.</p></div></div><div class="flow-empty">No targets yet. Create a node and add a target from its inspector.</div></div>`;
    const cards = state.nodes.map(node => {
      const hasPath = Boolean(node.webTarget);
      const path = hasPath ? derivedPath(node) : "No target · paths derive from semantic placement";
      const status = !hasPath ? "missing" : node.realization === "stale" ? "stale preview" : node.realization === "offline" ? "runtime offline" : "example current";
      return `<article class="artifact-card ${hasPath ? "" : "is-missing"}"><span class="artifact-icon">◇</span><span class="artifact-copy"><strong>${escapeHTML(node.name)} <span>· ${escapeHTML(node.kind)}</span></strong><code>${escapeHTML(path)}</code><small class="artifact-source-note">Illustrative path · no artifact emitted</small></span><span class="artifact-status ${hasPath ? "" : "status-missing"}">${status}</span>${node.id === state.selectedId ? `<div class="artifact-actions">${hasPath ? `<button type="button" data-action="realize" data-id="${escapeHTML(node.id)}">Request realization</button><button type="button" data-action="remove-target" data-id="${escapeHTML(node.id)}">Remove target</button>` : `<button type="button" data-action="add-target" data-id="${escapeHTML(node.id)}">Add web target</button>`}<button type="button" data-select="${escapeHTML(node.id)}">Inspect node</button></div>` : ""}</article>`;
    }).join("");
    const targets = state.nodes.filter(node => node.webTarget).length;
    return `<div class="realizations-view"><div class="view-intro"><div><span class="view-overline">MEANING → OUTPUT</span><h3>Realization follows intent.</h3><p>Paths update with semantic placement. This offline preview does not emit source artifacts.</p></div><span class="view-count-pill">${targets} example targets</span></div><div class="artifact-list">${cards}</div></div>`;
  }
  function renderProvenance() {
    const events = state.events.map(event => {
      const node = nodeById(event.nodeId);
      const name = node?.name || "Field";
      return `<article class="timeline-item"><span class="timeline-dot"></span><div class="timeline-copy"><strong>${escapeHTML(event.title)}</strong><p>${escapeHTML(event.description)} <span>· ${escapeHTML(event.source)} · ${escapeHTML(name)}</span></p></div><time class="timeline-time">${escapeHTML(event.time)}</time></article>`;
    }).join("");
    const sampleHash = `preview-${state.nodes.length.toString(16)}-${state.events.length.toString(16)}`;
    const fingerprint = state.runtime?.fingerprint || sampleHash;
    return `<div class="provenance-view"><div class="view-intro"><div><span class="view-overline">A MEANINGFUL HISTORY</span><h3>Where meaning came from</h3><p>${state.runtime?.connected ? "Session actions are applied to the live SIR graph. The journal lasts for this server process only." : "Local preview actions appear here. The runtime does not expose durable SIR history."}</p></div><span class="view-count-pill">${state.events.length} ${state.runtime?.connected ? "SIR events" : "preview events"}</span></div><div class="preview-source"><span>${state.runtime?.connected ? "SIR graph fingerprint" : "Preview state key"}</span><code>${escapeHTML(fingerprint)}</code><small>${escapeHTML(state.runtime?.fingerprintType || "Not a runtime source hash")}</small></div><div class="timeline">${events || '<div class="flow-empty">The next meaningful change will begin this trail.</div>'}</div></div>`;
  }

  function observerText(node) {
    if (state.selectedRelation) {
      const from = nodeById(state.selectedRelation.from), to = nodeById(state.selectedRelation.to);
      return `Reading the ${state.runtime?.connected ? "SIR" : "proposed"} ${state.selectedRelation.label || "relationship"} between ${from?.name || "a node"} and ${to?.name || "a node"}. Observer is read-only.`;
    }
    if (!node) return state.nodes.length ? (state.runtime?.connected ? "The Observer is reading the live SIR graph." : "The Observer is reading the shared local preview.") : "The field is quiet. Add a root idea when you are ready.";
    const facts = [`${state.nodes.length} nodes in ${state.runtime?.connected ? "the live SIR graph" : "local preview"}`];
    if (node.behavior) facts.push(state.runtime?.connected ? `${node.name} has behavioral SIR payloads` : `${node.name} carries example behavioral intent`);
    facts.push(state.runtime?.connected ? `${state.targets.length} field-wide realization plans` : node.webTarget ? "an example path is derived" : "no target is attached");
    if (state.connectMode) facts.push(state.linkSource ? "waiting for a relationship destination" : "relationship proposal is ready");
    return `Watching ${node.name} · ${facts.join(" · ")}.`;
  }
  function renderRelationInspector(relation) {
    const from = nodeById(relation.from), to = nodeById(relation.to);
    return `<section class="relationship-inspector"><span class="inspector-kicker">SELECTED RELATIONSHIP</span><h3>${escapeHTML(labelCase(relation.label || relation.type || "Relationship"))}</h3><div class="relation-endpoints"><span>${escapeHTML(from?.name || "Unknown source")}</span><b>→</b><span>${escapeHTML(to?.name || "Unknown destination")}</span></div><p>${escapeHTML(relation.intent || "This connection is a local example or a builder-proposed relationship.")}</p><small>Relationship type · ${escapeHTML(relation.type || "structural")}</small><button id="clear-relation-selection" class="small-action" type="button">Back to node</button></section>`;
  }
  function renderInspector() {
    const node = selectedNode();
    const content = $("#inspector-content");
    if (!node) {
      content.innerHTML = `<div class="empty-state" style="min-height:180px;padding:10px"><div class="empty-state-inner"><img class="empty-emblem" src="assets/orren-emblem.webp" alt=""><h3>No selection.</h3><p>Create the first idea and the Observer will follow its meaning.</p></div></div>`;
      return;
    }
    const live = Boolean(state.runtime?.connected);
    const confidence = node.confidence == null ? (live ? "Not modeled by the current SIR schema" : "Not provided by runtime") : `${Math.round(node.confidence * 100)}% example only`;
    const point = (index, radius) => {
      const angle = (Math.PI * 2 * index) / dimensionNames.length - Math.PI / 2;
      return `${(48 + Math.cos(angle) * radius).toFixed(1)},${(43 + Math.sin(angle) * radius).toFixed(1)}`;
    };
    const radarAxes = dimensionNames.map((name, index) => `<line x1="48" y1="43" x2="${point(index, 38).split(",")[0]}" y2="${point(index, 38).split(",")[1]}" />`).join("");
    const radarGrid = [.33, .66, 1].map(scale => `<polygon points="${dimensionNames.map((_, index) => point(index, 38 * scale)).join(" ")}" />`).join("");
    const radarData = dimensionNames.map((name, index) => point(index, 38 * Math.max(.09, relativeDimensionValue(node, name)))).join(" ");
    const radarLabel = live ? "SIR dimension payload density normalized within this field, not confidence" : "Illustrative nine-dimension profile, not a runtime confidence measure";
    const radar = `<svg class="radar-svg" viewBox="0 0 96 86" role="img" aria-label="${radarLabel}"><g class="radar-grid">${radarGrid}${radarAxes}</g><polygon class="radar-fill" points="${radarData}"/><polygon class="radar-outline" points="${radarData}"/>${dimensionNames.map((name, index) => `<circle class="radar-point" cx="${point(index, 38 * Math.max(.09, relativeDimensionValue(node, name))).split(",")[0]}" cy="${point(index, 38 * Math.max(.09, relativeDimensionValue(node, name))).split(",")[1]}" r="1.7"/>`).join("")}</svg>`;
    const dims = dimensionNames.map((name, index) => {
      const raw = node.profile?.[name];
      const value = Math.round(relativeDimensionValue(node, name) * 100);
      const label = live ? String(Number(node.dimensionCounts?.[name]) || 0) : Number.isFinite(raw) ? `${value}%` : "—";
      return `<div class="dimension-bar-row" title="${escapeHTML(dimensionValueLabel(node, name))}"><span class="dimension-swatch swatch-${index}"></span><span class="dimension-bar-name">${name}</span><span class="dimension-bar-track"><i class="bar-${index}" style="width:${value}%"></i></span><span class="dimension-bar-value">${label}</span></div>`;
    }).join("");
    const path = live ? node.path : derivedPath(node);
    const planRows = live ? state.targets.map(target => {
      const score = Math.round(Number(target.preservationScore || 0) * 100);
      const className = target.planState === "degraded" ? "degraded" : "current";
      const firstFile = target.outputFiles[0]?.path || "No output-file plan";
      return { name: labelCase(target.name), state: `Plan only · ${score}% preserved`, icon: "◇", path: `${target.outputFiles.length} planned file(s) · ${firstFile}`, className };
    }) : [];
    const localRows = [
      { name: "Web", state: node.webTarget ? node.realization === "stale" ? "Stale · preview" : node.realization === "offline" ? "Runtime offline" : "Example · current" : "Not requested", icon: "◉", path: node.webTarget ? path : "No target", className: node.webTarget && node.realization !== "offline" ? "current" : "waiting" },
      { name: "Android", state: "Example · degraded", icon: "♙", path: "Capability gap · sample only", className: "degraded" },
      { name: "Rust", state: "Example · not realized", icon: "◌", path: "No artifact in local preview", className: "waiting" }
    ];
    const statuses = (live ? planRows : localRows).map(target => `<div class="target-row"><span class="target-icon ${target.className}">${target.icon}</span><span class="target-copy"><strong>${escapeHTML(target.name)}</strong><small>${escapeHTML(target.path)}</small></span><span class="target-state ${target.className}">${escapeHTML(target.state)}</span></div>`).join("") || `<p class="target-empty">${live ? "No realization targets are declared for this SIR field." : "No target attached."}</p>`;
    const parent = node.parentId ? nodeById(node.parentId)?.name : "Field root";
    const selectedRelations = state.relations.filter(edge => edge.from === node.id || edge.to === node.id).length;
    const nodeTags = [node.behavior ? "Behavioral" : "Structural", node.parentId ? node.kind : "Root", live ? `${dimensionCoverage(node)}/9 dimensions` : node.webTarget ? "Web target" : selectedRelations ? "Related" : "Meaning"].map(tag => `<span>${escapeHTML(tag)}</span>`).join("");
    const payloadRows = live ? dimensionNames.flatMap(name => (node.dimensions?.[name] || []).map(payload => ({ name, text: typeof payload === "string" ? payload : JSON.stringify(payload) }))).map(row => `<li><strong>${escapeHTML(row.name)}</strong><code>${escapeHTML(row.text.length > 150 ? row.text.slice(0,147) + "…" : row.text)}</code></li>`).join("") : "";
    const payloadSection = live ? `<details class="semantic-payloads"><summary>Actual SIR payloads · ${payloadRows ? "expand" : "none on this node"}</summary>${payloadRows ? `<ul>${payloadRows}</ul>` : ""}</details>` : "";
    const runtimeTargetButton = live ? `<button class="small-action target-action" type="button" id="add-target">◇ Manage field targets</button><button class="small-action realize-action" type="button" id="realize">Refresh Engine plans</button>` : `<button class="small-action target-action" type="button" id="add-target">◇ ${node.webTarget ? "Target added" : "Add web target"}</button>${node.webTarget ? `<button class="small-action realize-action" type="button" id="realize">Request realization</button>` : ""}`;
    const boundary = live ? `Live SIR session · ${state.runtime.sessionOnly ? "changes last for this server process" : "session state"}. Coordinator plans are refreshed; ${state.runtime.codegenAvailable ? "source generation is available" : "no files are emitted because the source generator is unavailable"}.` : "This preview is not connected to the Python engine. Realize requests do not emit files.";
    content.innerHTML = `${state.selectedRelation ? renderRelationInspector(state.selectedRelation) : ""}<section class="selected-node-card"><div class="selected-node-head"><span class="selected-node-seal"><img src="assets/orren-emblem.webp" alt=""></span><span class="selected-node-name"><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)} · ${escapeHTML(parent ? `inside ${parent}` : "field root")}</small></span><span class="active-badge ${live ? "runtime-active" : ""}"><i></i>${live ? "Live SIR" : "Preview"}</span><button class="close-inspector" id="close-inspector" type="button" aria-label="Close detail" title="Close detail">×</button></div>${node.behavior ? `<p class="selected-behavior">“${escapeHTML(node.behavior)}”</p>` : '<p class="selected-behavior muted-behavior">Add behavior to give this node intent.</p>'}<div class="node-tags">${nodeTags}</div><div class="confidence-note" title="The committed SIR model does not define confidence values.">Confidence · ${escapeHTML(confidence)}</div>
      <div class="detail-grid"><section class="dimension-card"><div class="detail-title">Dimensions <button id="toggle-dimensions" type="button" aria-expanded="true">${live ? `${dimensionCoverage(node)}/9 populated` : "9 in view"}</button></div><div class="dimension-visual">${radar}<div class="dimension-bars" id="dimension-list">${dims}</div></div><small class="profile-note">${live ? "Counts are SIR payload entries; bars normalize within this field, not confidence." : "Illustrative sample profile · not runtime values"}</small></section><section class="realization-card"><div class="detail-title">${live ? "Field-wide Engine plans" : "Realization status"} <span class="sample-label">${live ? "PLAN ONLY" : "SAMPLE"}</span></div><div class="target-list">${statuses}</div></section></div>${payloadSection}
      <div class="derived-path-card"><span>${live ? "SIR semantic path" : "Path"} <span>${live ? "(actual node identifier)" : "(derived · local preview)"}</span></span><code class="${path ? "" : "path-missing"}">${escapeHTML(path || "Add a web target to derive this path")}</code><button class="copy-path" id="copy-path" type="button" title="Copy ${live ? "SIR semantic" : "derived"} path" ${path ? "" : "disabled"}>▢</button></div>
      <details class="inspector-section behavior-editor" open><summary><strong>REFINE MEANING</strong><span>Visual Producer · ${live ? "Engine" : "preview"}</span></summary><form class="intent-form" id="intent-form"><label class="sr-only" for="intent-input">Describe a behavior for ${escapeHTML(node.name)}</label><textarea id="intent-input" maxlength="180" placeholder="Describe an intent… e.g. Make it fetch the weather"></textarea><div class="intent-actions"><button class="small-action" type="submit">+ Add behavior</button>${runtimeTargetButton}</div></form></details><p class="runtime-boundary">${escapeHTML(boundary)}</p></section>`;
    $("#observer-readout").textContent = observerText(node);
    $("#observer-time").textContent = latest()?.time?.toUpperCase() || "JUST NOW";
    $("#create-context").textContent = node ? `inside ${node.name}` : "new root node";
  }

  function render() {
    const info = viewInfo[state.view];
    const root = state.nodes.find(node => !node.parentId || !nodeById(node.parentId));
    $("#workspace-name").textContent = root?.name || "Untitled field";
    $("#sidebar-workspace-name").textContent = root?.name || "Untitled field";
    $("#field-title").innerHTML = `${escapeHTML(root?.name || "Untitled field")} <span class="field-title-kind">semantic field</span>`;
    $("#field-caption").textContent = state.nodes.length ? `${state.nodes.length} semantic nodes · ${allRelationships().length} relationships · ${state.runtime?.connected ? `${state.runtime.sourceFile} · Orren Engine ${state.runtime.engineVersion}` : "local preview data"}` : "A clear field, ready for its first idea.";
    const runtimeConnected = Boolean(state.runtime?.connected);
    $(".app-shell").classList.toggle("engine-connected", runtimeConnected);
    const engineStatus = $("#engine-status");
    engineStatus.classList.toggle("is-connected", runtimeConnected);
    engineStatus.title = runtimeConnected ? (state.runtime.codegenAvailable ? "Orren Engine connected; coordinator plans are live." : `Orren Engine connected; source generation is unavailable. ${state.runtime.codegenMessage}`) : "Orren Engine API not connected; showing the illustrative local preview.";
    engineStatus.querySelector("span").textContent = runtimeConnected ? `Engine connected · ${state.targets.length} plan${state.targets.length === 1 ? "" : "s"}` : "Local preview · runtime offline";
    $(".field-mode").innerHTML = `<i></i>${runtimeConnected ? "SIR ENGINE · LIVE" : "LOCAL PREVIEW"}`;
    $(".surface-item.is-current .surface-state").textContent = runtimeConnected ? "Live SIR" : "Preview active";
    $(".agent-card .preview-tag").textContent = runtimeConnected ? "ENGINE" : "LOCAL";
    $(".sidebar-foot small").textContent = runtimeConnected ? "Live Engine session · memory only" : "Visual Hub · local preview";
    $("#prototype-runtime-status").textContent = runtimeConnected ? (state.runtime.codegenAvailable ? "LIVE SIR · ENGINE CONNECTED" : "LIVE SIR · PLAN ONLY · NO SOURCE EMITTER") : "LOCAL PREVIEW DATA · PYTHON ENGINE NOT CONNECTED";
    $("#action-status-text").textContent = runtimeConnected ? `Engine · ${state.targets.length} plan${state.targets.length === 1 ? "" : "s"}` : "Local preview";
    renderSidebarTree();
    $$(".view-link").forEach(button => {
      const active = button.dataset.view === state.view;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    $$(".mobile-view-nav [data-mobile-view]").forEach(button => button.classList.toggle("is-active", button.dataset.mobileView === state.view));
    $("#field-view").setAttribute("aria-labelledby", `tab-${state.view}`);
    $("#current-view-title").textContent = info.title;
    $("#current-view-subtitle").textContent = info.subtitle;
    $("#current-view-icon").textContent = info.icon;
    const html = { tree: renderTree, flow: renderFlow, lens: renderLens, realizations: renderRealizations, provenance: renderProvenance }[state.view]();
    $("#field-view").innerHTML = html;
    const relationships = allRelationships();
    $("#field-summary").textContent = `${state.nodes.length} ${state.nodes.length === 1 ? "node" : "nodes"} · ${relationships.length} ${relationships.length === 1 ? "relationship" : "relationships"}${runtimeConnected ? " · SIR" : ""}`;
    $("#node-count").textContent = String(state.nodes.length).padStart(2, "0");
    $("#artifact-count").textContent = String(runtimeConnected ? state.targets.length : state.nodes.filter(node => node.webTarget).length).padStart(2, "0");
    $("#connect-mode").classList.toggle("is-active", state.connectMode);
    $("#action-connect").classList.toggle("is-active", state.connectMode);
    $("#connect-hint").hidden = !state.connectMode;
    $("#connect-hint").firstChild.textContent = state.linkSource ? `Now choose a destination for ${nodeById(state.linkSource)?.name || "this node"}. ` : "Choose a starting node, then a destination; you'll review the relationship type. ";
    $$(".dimension-filter [data-filter]").forEach(button => button.classList.toggle("selected", button.dataset.filter === state.filter));
    $(".work-area").classList.toggle("inspector-is-closed", !state.inspectorOpen);
    $("#inspector").classList.toggle("is-open", state.inspectorOpen);
    $("#show-inspector").hidden = state.inspectorOpen;
    const mobileOrTablet = window.matchMedia("(max-width: 920px)").matches;
    const backdrop = $("#inspector-backdrop");
    backdrop.hidden = !(state.inspectorOpen && mobileOrTablet);
    backdrop.classList.toggle("is-visible", state.inspectorOpen && mobileOrTablet);
    renderInspector();
    if (state.view === "tree" && window.matchMedia("(max-width: 640px)").matches && state.selectedId) {
      requestAnimationFrame(() => {
        const canvas = $("#field-view"), selected = $(`.graph-node[data-select="${CSS.escape(state.selectedId)}"]`);
        if (!canvas || !selected) return;
        const viewRect = canvas.getBoundingClientRect(), nodeRect = selected.getBoundingClientRect();
        canvas.scrollTo({ left: Math.max(0, canvas.scrollLeft + nodeRect.left - viewRect.left - (canvas.clientWidth - nodeRect.width) / 2), top: Math.max(0, canvas.scrollTop + nodeRect.top - viewRect.top - (canvas.clientHeight - nodeRect.height) / 2), behavior: "smooth" });
      });
    }
  }
  function changeView(view) { if (!viewInfo[view]) return; state.view = view; render(); }
  function addNode(name, parentId) {
    const cleanName = name.trim().replace(/\s+/g, " ");
    if (!cleanName) return;
    const parent = nodeById(parentId);
    const id = `${slug(cleanName)}-${Date.now().toString(36).slice(-5)}`;
    const node = { id, name: cleanName, parentId: parent?.id || null, kind: parent ? "Structural node" : "Semantic root", confidence: null, behavior: "", webTarget: false, realization: "missing", profile: {} };
    state.nodes.push(node);
    state.selectedId = node.id;
    state.selectedRelation = null;
    state.inspectorOpen = true;
    addEvent(`${cleanName} added to the preview field`, parent ? `Placed inside ${parent.name}; the example path will follow this semantic placement.` : "A new root idea was created in the local preview.", node.id);
    render();
    showToast(parent ? `${cleanName} placed inside ${parent.name}.` : `${cleanName} entered the preview field.`);
  }
  function isDescendant(candidateId, parentId) {
    let cursor = nodeById(parentId);
    while (cursor) { if (cursor.id === candidateId) return true; cursor = nodeById(cursor.parentId); }
    return false;
  }
  function moveNode(nodeId, newParentId) {
    const node = nodeById(nodeId), parent = nodeById(newParentId);
    if (!node || !parent || node.id === parent.id || isDescendant(node.id, parent.id)) { showToast("That move would create a semantic loop."); return; }
    if (node.parentId === parent.id) { showToast(`${node.name} is already under ${parent.name}.`); return; }
    const before = node.webTarget ? derivedPath(node) : "";
    node.parentId = parent.id;
    if (node.kind === "Semantic root") node.kind = "Structural node";
    if (node.webTarget) node.realization = "stale";
    const after = node.webTarget ? derivedPath(node) : "";
    state.selectedId = node.id;
    state.selectedRelation = null;
    state.inspectorOpen = true;
    addEvent(`${node.name} reparenting proposed in preview`, node.webTarget ? `Derived path changed from ${before} to ${after}.` : `Moved beneath ${parent.name}; future paths follow the hierarchy.`, node.id);
    render();
    showToast(node.webTarget ? `Preview path updated · ${after}` : `${node.name} now lives under ${parent.name}.`);
  }
  function connectNodes(fromId, toId) {
    if (!fromId || !toId || fromId === toId) { showToast("Choose two different semantic nodes."); return; }
    if (state.relations.some(edge => edge.from === fromId && edge.to === toId)) { showToast("That relationship is already in the field."); return; }
    const from = nodeById(fromId), to = nodeById(toId);
    if (!from || !to) return;
    state.pendingRelation = { from: fromId, to: toId };
    state.connectMode = false;
    state.linkSource = null;
    $("#relation-summary").textContent = `Propose how ${from.name} and ${to.name} relate. Nothing is added until you choose a type and confirm.`;
    $("#relation-type").value = "feeds";
    $("#relation-note").value = "";
    render();
    $("#relation-dialog").showModal();
  }
  function addBehavior(nodeId, text) {
    const node = nodeById(nodeId), behavior = text.trim();
    if (!node || !behavior) { showToast("Describe the intent you want this node to carry."); return; }
    node.behavior = behavior;
    node.profile.Behavioral = Math.max(Number(node.profile.Behavioral) || 0, .9);
    if (node.webTarget && node.realization === "current") node.realization = "stale";
    addEvent(`${node.name} gained behavioral intent in preview`, `Intent captured: “${behavior}”. Existing target examples are now stale.`, node.id);
    render();
    showToast(`Behavior added to ${node.name} in the local preview.`);
  }
  function addTarget(nodeId) {
    const node = nodeById(nodeId);
    if (!node) return;
    if (node.webTarget) { showToast("A web target is already attached to this node."); return; }
    node.webTarget = true;
    node.realization = "missing";
    state.view = "realizations";
    addEvent(`Web target attached to ${node.name} in preview`, `Example path derived as ${derivedPath(node)}.`, node.id);
    render();
    showToast(`Example path derived · ${derivedPath(node)}. No artifact has been emitted.`);
  }
  function realize(nodeId) {
    const node = nodeById(nodeId);
    if (!node?.webTarget) { showToast("Add a web target before requesting realization."); return; }
    node.realization = "offline";
    addEvent(`Realization requested for ${node.name}`, `Request blocked: Python runtime is offline. The example path ${derivedPath(node)} is illustrative only.`, node.id, "Visual Producer · blocked");
    render();
    showToast("Runtime offline · no source artifact was generated.");
  }
  function closeInspector() { state.inspectorOpen = false; render(); }
  function openSearch() {
    const panel = $("#search-panel");
    panel.hidden = false;
    $("#field-search").focus();
  }
  function updateSearch() {
    const query = $("#field-search").value.trim().toLocaleLowerCase();
    const results = state.nodes.filter(node => !query || node.name.toLocaleLowerCase().includes(query) || node.kind.toLocaleLowerCase().includes(query) || node.behavior.toLocaleLowerCase().includes(query)).slice(0, 12);
    $("#search-results").innerHTML = results.length ? results.map(node => `<button class="search-result" type="button" role="option" data-search-select="${escapeHTML(node.id)}"><span class="structure-marker ${node.webTarget ? "target" : node.behavior ? "behavioral" : ""}">${glyphFor(node)}</span><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)}</small></button>`).join("") : `<span class="search-empty">No semantic nodes match that search.</span>`;
  }
  function handleSpeak() {
    const node = selectedNode();
    if (!node) { showToast("Create a node before adding behavioral intent."); return; }
    const editor = $("#inspector-content .behavior-editor");
    if (editor) editor.open = true;
    const input = $("#intent-input");
    if (!input) return;
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      input.focus();
      showToast("Speech surface is not linked here. Type your intent in the inspector instead.");
      return;
    }
    try {
      const recognition = new Recognition();
      recognition.lang = document.documentElement.lang || "en";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onresult = event => {
        input.value = event.results?.[0]?.[0]?.transcript || "";
        input.focus();
        showToast("Speech captured in the preview. Review it, then choose Add behavior.");
      };
      recognition.onerror = () => showToast("Browser speech capture could not start. You can type the intent instead.");
      recognition.start();
    } catch (_) {
      input.focus();
      showToast("Browser speech capture is unavailable. Type the intent instead.");
    }
  }

  $(".view-nav").addEventListener("click", event => {
    const button = event.target.closest("[data-view]");
    if (button) changeView(button.dataset.view);
  });
  $(".mobile-view-nav").addEventListener("click", event => {
    const button = event.target.closest("[data-mobile-view]");
    if (button) changeView(button.dataset.mobileView);
  });
  $(".view-nav").addEventListener("keydown", event => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const tabs = $$(".view-link");
    let index = tabs.findIndex(tab => tab.dataset.view === state.view);
    index = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowDown" ? 1 : -1) + tabs.length) % tabs.length;
    changeView(tabs[index].dataset.view);
    tabs[index].focus();
  });
  $("#sidebar-tree").addEventListener("click", event => {
    const button = event.target.closest("[data-select]");
    if (!button) return;
    state.selectedId = button.dataset.select;
    state.selectedRelation = null;
    state.inspectorOpen = true;
    render();
  });
  $("#sidebar-tree").addEventListener("keydown", event => {
    const node = event.target.closest("[data-sidebar-node]");
    if (!node || !["ArrowDown","ArrowUp","Home","End"].includes(event.key)) return;
    const nodes = $$("[data-sidebar-node]", $("#sidebar-tree"));
    const current = nodes.indexOf(node);
    const index = event.key === "Home" ? 0 : event.key === "End" ? nodes.length - 1 : (current + (event.key === "ArrowDown" ? 1 : -1) + nodes.length) % nodes.length;
    event.preventDefault();
    nodes[index]?.focus();
  });
  $("#sidebar-tree").addEventListener("dragstart", event => {
    const node = event.target.closest("[data-sidebar-node]");
    if (!node) return;
    draggedId = node.dataset.sidebarNode;
    node.setAttribute("aria-grabbed", "true");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedId);
  });
  $("#sidebar-tree").addEventListener("dragend", event => {
    const node = event.target.closest("[data-sidebar-node]");
    if (node) node.setAttribute("aria-grabbed", "false");
    draggedId = null;
  });
  $("#sidebar-tree").addEventListener("dragover", event => {
    if (event.target.closest("[data-sidebar-node]") && draggedId) { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }
  });
  $("#sidebar-tree").addEventListener("drop", event => {
    const target = event.target.closest("[data-sidebar-node]");
    if (!target) return;
    event.preventDefault();
    const sourceId = event.dataTransfer.getData("text/plain") || draggedId;
    if (sourceId) moveNode(sourceId, target.dataset.sidebarNode);
  });

  $("#node-form").addEventListener("submit", event => {
    event.preventDefault();
    const input = $("#node-name");
    if (!state.nodes.length) addNode(input.value, null);
    else addNode(input.value, selectedNode()?.id || state.nodes[0].id);
    input.value = "";
    input.focus();
  });
  $("#focus-create").addEventListener("click", () => { $("#node-name").focus(); $("#node-name").scrollIntoView({ block: "nearest", behavior: "smooth" }); });
  $("#action-create").addEventListener("click", () => { $("#node-name").focus(); $("#node-name").scrollIntoView({ block: "nearest", behavior: "smooth" }); });
  $("#empty-field").addEventListener("click", () => {
    state = { ...defaults(), nodes: [], relations: [], events: [], selectedId: null, selectedRelation: null, view: "tree", filter: "all", connectMode: false, linkSource: null, pendingRelation: null, compareIds: [], inspectorOpen: true };
    render();
    $("#node-name").focus();
    showToast("A clean local preview is ready for its first idea.");
  });
  $("#load-example").addEventListener("click", () => { state = defaults(); render(); showToast("The illustrative MyApp → UI → Button field is loaded."); });
  $("#filter-toggle").addEventListener("click", () => {
    const panel = $("#dimension-filter"), open = panel.hidden;
    panel.hidden = !open;
    $("#filter-toggle").setAttribute("aria-expanded", String(open));
  });
  $("#dimension-filter").addEventListener("click", event => {
    const button = event.target.closest("[data-filter]");
    if (!button) return;
    state.filter = button.dataset.filter;
    render();
    $("#dimension-filter").hidden = false;
    $("#filter-toggle").setAttribute("aria-expanded", "true");
  });
  $("#connect-mode").addEventListener("click", () => {
    state.connectMode = !state.connectMode;
    state.linkSource = null;
    render();
    showToast(state.connectMode ? "Choose the source and destination; then review the proposed relationship type." : "Relationship proposal closed.");
  });
  $("#action-connect").addEventListener("click", () => $("#connect-mode").click());
  $("#cancel-connect").addEventListener("click", () => { state.connectMode = false; state.linkSource = null; render(); });
  $("#action-search").addEventListener("click", () => { openSearch(); updateSearch(); });
  $("#field-search").addEventListener("input", updateSearch);
  $("#search-clear").addEventListener("click", () => { $("#field-search").value = ""; updateSearch(); $("#field-search").focus(); });
  $("#search-results").addEventListener("click", event => {
    const result = event.target.closest("[data-search-select]");
    if (!result) return;
    state.selectedId = result.dataset.searchSelect;
    state.selectedRelation = null;
    state.inspectorOpen = true;
    $("#search-panel").hidden = true;
    render();
  });
  $("#action-speak").addEventListener("click", handleSpeak);
  $("#action-realize").addEventListener("click", () => {
    const node = selectedNode();
    if (!node) { showToast("Create and select a semantic node first."); return; }
    if (!node.webTarget) { addTarget(node.id); showToast("Web target added to the preview. Runtime realization is unavailable."); return; }
    realize(node.id);
  });
  $("#field-view").addEventListener("click", event => {
    const empty = event.target.closest("[data-empty]");
    if (empty) {
      if (empty.dataset.empty === "create") { $("#node-name").focus(); return; }
      if (empty.dataset.empty === "speak") { handleSpeak(); return; }
      if (empty.dataset.empty === "example") { state = defaults(); render(); showToast("The illustrative example field is loaded."); return; }
    }
    if (event.target.closest("#clear-compare")) { state.compareIds = []; render(); return; }
    const flowFilter = event.target.closest("[data-flow-filter]");
    if (flowFilter) {
      const filter = flowFilter.dataset.flowFilter;
      $$(".flow-row", $("#field-view")).forEach(row => {
        const hasBehavior = row.querySelector(".intent-node");
        const hasRel = row.querySelector("[data-rel-index]");
        const structure = hasRel && row.querySelector("[data-rel-index]").textContent.trim() === "contains";
        row.hidden = filter === "behavior" ? !hasBehavior : filter === "relation" ? !hasRel || structure : filter === "structure" ? !structure : false;
      });
      $$("[data-flow-filter]", $("#field-view")).forEach(button => button.classList.toggle("selected", button === flowFilter));
      return;
    }
    const lensDimension = event.target.closest("[data-lens-dimension]");
    if (lensDimension) { state.lensDimension = lensDimension.dataset.lensDimension; render(); return; }
    const action = event.target.closest("[data-action]");
    if (action) {
      const id = action.dataset.id;
      if (action.dataset.action === "add-target") addTarget(id);
      if (action.dataset.action === "realize") realize(id);
      if (action.dataset.action === "remove-target") {
        const node = nodeById(id);
        if (node) { node.webTarget = false; node.realization = "missing"; addEvent(`Web target removed from ${node.name}`, "Only the local example target was removed; semantic meaning remains.", node.id); render(); showToast("Preview target removed. No runtime data changed."); }
      }
      return;
    }
    const relationButton = event.target.closest("[data-rel-index]");
    if (relationButton) {
      const index = Number(relationButton.dataset.relIndex);
      state.selectedRelation = allRelationships()[index] || null;
      if (state.selectedRelation) { state.selectedId = state.selectedRelation.to; state.inspectorOpen = true; render(); }
      return;
    }
    const select = event.target.closest("[data-select]");
    const id = select?.dataset.select;
    if (!id) return;
    if (state.connectMode) {
      if (!state.linkSource) { state.linkSource = id; state.selectedId = id; render(); showToast(`Source selected · ${nodeById(id)?.name}. Choose a destination.`); }
      else connectNodes(state.linkSource, id);
      return;
    }
    if (event.target.closest(".lens-card")) {
      if (state.compareIds.includes(id)) state.compareIds = state.compareIds.filter(item => item !== id);
      else state.compareIds = [...state.compareIds, id].slice(-2);
    }
    state.selectedId = id;
    state.selectedRelation = null;
    state.inspectorOpen = true;
    render();
  });
  $("#field-view").addEventListener("pointerover", event => {
    const node = event.target.closest("[data-select]");
    if (!node || state.view !== "flow") return;
    $$(".flow-row", $("#field-view")).forEach(row => row.classList.toggle("is-related-focus", row.dataset.linkFrom === node.dataset.select || row.dataset.linkTo === node.dataset.select));
  });
  $("#field-view").addEventListener("pointerout", event => {
    if (event.target.closest("[data-select]") && state.view === "flow") $$(".flow-row.is-related-focus", $("#field-view")).forEach(row => row.classList.remove("is-related-focus"));
  });
  $("#inspector-content").addEventListener("submit", event => {
    if (event.target.id !== "intent-form") return;
    event.preventDefault();
    addBehavior(state.selectedId, $("#intent-input").value);
  });
  $("#inspector-content").addEventListener("click", event => {
    if (event.target.closest("#copy-path")) {
      const currentPath = derivedPath(selectedNode());
      if (currentPath && navigator.clipboard?.writeText) navigator.clipboard.writeText(currentPath).then(() => showToast("Illustrative derived path copied."), () => showToast(currentPath));
      return;
    }
    if (event.target.closest("#close-inspector")) { closeInspector(); return; }
    if (event.target.closest("#clear-relation-selection")) { state.selectedRelation = null; render(); return; }
    if (event.target.closest("#toggle-dimensions")) {
      const list = $("#dimension-list");
      list.hidden = !list.hidden;
      event.target.closest("#toggle-dimensions").textContent = list.hidden ? "Inspect all 9" : "9 in view";
      return;
    }
    if (event.target.closest("#add-target")) { addTarget(state.selectedId); return; }
    if (event.target.closest("#realize")) { realize(state.selectedId); return; }
  });
  $("#relation-form").addEventListener("submit", event => {
    event.preventDefault();
    if (!state.pendingRelation) { $("#relation-dialog").close(); return; }
    const { from, to } = state.pendingRelation;
    const type = $("#relation-type").value;
    const note = $("#relation-note").value.trim();
    const edge = { from, to, type, label: type.replaceAll("_", " "), intent: note || `${nodeById(from)?.name || "Source"} ${type.replaceAll("_", " ")} ${nodeById(to)?.name || "destination"}.` };
    state.relations.push(edge);
    state.selectedId = to;
    state.selectedRelation = edge;
    state.inspectorOpen = true;
    addEvent(`${nodeById(from)?.name || "Node"} proposed to ${type.replaceAll("_", " ")} ${nodeById(to)?.name || "node"}`, note || "Relationship explicitly proposed by the builder.", to);
    state.pendingRelation = null;
    $("#relation-dialog").close();
    changeView("flow");
    showToast(`Relationship proposed · ${edge.label}. It remains a local preview action.`);
  });
  $("#cancel-relation").addEventListener("click", () => { state.pendingRelation = null; $("#relation-dialog").close(); });
  $("#inspector-backdrop").addEventListener("click", closeInspector);
  $("#show-inspector").addEventListener("click", () => { state.inspectorOpen = true; render(); });
  $("#sidebar-toggle").addEventListener("click", () => {
    const shell = $("#workspace-grid").closest(".app-shell");
    const collapsed = shell.classList.toggle("sidebar-collapsed");
    $("#sidebar-toggle").setAttribute("aria-expanded", String(!collapsed));
  });
  $("#collapse-structure").addEventListener("click", event => {
    const tree = $("#sidebar-tree"), open = tree.hidden;
    tree.hidden = !open;
    event.currentTarget.setAttribute("aria-expanded", String(open));
    event.currentTarget.textContent = open ? "−" : "+";
  });
  $("#inspector-menu").addEventListener("click", () => { state.inspectorOpen = false; render(); showToast("Inspector tucked away. Select a node to bring it back."); });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !$("#relation-dialog").open && state.connectMode) { state.connectMode = false; state.linkSource = null; render(); }
    if ((event.key === "/" || (event.metaKey && event.key.toLowerCase() === "k")) && !["INPUT","TEXTAREA","SELECT"].includes(document.activeElement?.tagName)) { event.preventDefault(); openSearch(); updateSearch(); }
  });
  window.addEventListener("resize", () => render());
  function applyRuntimeSnapshot(data) {
    if (!data || !Array.isArray(data.nodes)) return;
    const previousSelection = state.selectedId;
    state.nodes = data.nodes;
    state.relations = Array.isArray(data.relations) ? data.relations : [];
    state.events = Array.isArray(data.events) ? data.events : [];
    state.targets = Array.isArray(data.targets) ? data.targets : [];
    state.availableTargets = Array.isArray(data.availableTargets) ? data.availableTargets : [];
    state.runtime = data.runtime || null;
    state.selectedId = state.nodes.some(node => node.id === previousSelection) ? previousSelection : data.focusId || data.rootId || state.nodes[0]?.id || null;
    state.selectedRelation = null;
    state.pendingRelation = null;
    state.connectMode = false;
    state.linkSource = null;
    if (!state.runtime?.connected) {
      state.targets = [];
      state.availableTargets = [];
    }
    render();
  }
  function selectRuntimeNode(id) {
    if (!nodeById(id)) return;
    state.selectedId = id;
    state.selectedRelation = null;
    state.inspectorOpen = true;
    render();
  }
  function selectRuntimeRelation(from, to, type) {
    const relation = state.relations.find(edge => edge.from === from && edge.to === to && edge.type === type);
    if (!relation) return;
    state.selectedRelation = relation;
    state.selectedId = relation.to;
    state.view = "flow";
    state.inspectorOpen = true;
    render();
  }
  function clearRuntimeProposal() {
    state.pendingRelation = null;
    state.connectMode = false;
    state.linkSource = null;
    if ($("#relation-dialog").open) $("#relation-dialog").close();
  }
  render();
  window.OrrenVisualHub = Object.freeze({
    getState: () => state,
    applyRuntimeSnapshot,
    setView: changeView,
    selectNode: selectRuntimeNode,
    selectRelation: selectRuntimeRelation,
    clearProposal: clearRuntimeProposal,
    showToast
  });
})();
