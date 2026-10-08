(() => {
  const dimensionNames = ["Expression", "Cognitive", "Vibe", "Spatial", "Temporal", "Relational", "Conditional", "Behavioral", "Equilibrium"];
  const defaults = () => ({
    nodes: [
      { id: "myapp", name: "MyApp", parentId: null, kind: "Semantic root", confidence: 0.98, behavior: "", webTarget: false, realization: "missing", profile: { Expression: .94, Cognitive: .86, Vibe: .82, Spatial: .38, Temporal: .21, Relational: .57, Conditional: .18, Behavioral: .22, Equilibrium: .71 } },
      { id: "ui", name: "UI", parentId: "myapp", kind: "Structure", confidence: 0.93, behavior: "", webTarget: false, realization: "missing", profile: { Expression: .82, Cognitive: .72, Vibe: .88, Spatial: .75, Temporal: .25, Relational: .59, Conditional: .18, Behavioral: .29, Equilibrium: .66 } },
      { id: "logic", name: "Logic", parentId: "myapp", kind: "Structure", confidence: 0.91, behavior: "", webTarget: false, realization: "missing", profile: { Expression: .77, Cognitive: .88, Vibe: .65, Spatial: .43, Temporal: .58, Relational: .82, Conditional: .62, Behavioral: .68, Equilibrium: .7 } },
      { id: "dashboard", name: "Dashboard", parentId: "ui", kind: "Interface", confidence: 0.91, behavior: "", webTarget: false, realization: "missing", profile: { Expression: .88, Cognitive: .75, Vibe: .76, Spatial: .82, Temporal: .63, Relational: .78, Conditional: .3, Behavioral: .51, Equilibrium: .69 } },
      { id: "weather", name: "WeatherService", parentId: "logic", kind: "Service", confidence: 0.95, behavior: "Fetches the latest weather conditions.", webTarget: false, realization: "missing", profile: { Expression: .78, Cognitive: .89, Vibe: .7, Spatial: .43, Temporal: .85, Relational: .88, Conditional: .71, Behavioral: .91, Equilibrium: .74 } },
      { id: "button", name: "Button", parentId: "dashboard", kind: "Component", confidence: 0.94, behavior: "Triggers weather data fetch and updates the dashboard.", webTarget: true, realization: "current", profile: { Expression: .82, Behavioral: .91, Cognitive: .68, Vibe: .76, Spatial: .62, Relational: .58, Temporal: .71, Conditional: .63, Equilibrium: .69 } },
      { id: "card", name: "Card", parentId: "dashboard", kind: "Component", confidence: 0.91, behavior: "Presents the latest weather summary.", webTarget: false, realization: "missing", profile: { Expression: .85, Cognitive: .72, Vibe: .78, Spatial: .81, Temporal: .52, Relational: .69, Conditional: .28, Behavioral: .6, Equilibrium: .68 } },
      { id: "chart", name: "Chart", parentId: "dashboard", kind: "Component", confidence: 0.89, behavior: "Visualizes temperature across the day.", webTarget: false, realization: "missing", profile: { Expression: .81, Cognitive: .8, Vibe: .72, Spatial: .83, Temporal: .91, Relational: .74, Conditional: .24, Behavioral: .67, Equilibrium: .65 } }
    ],
    relations: [],
    events: [
      { title: "Button realized for web", description: "Current artifact at src/ui/dashboard/Button.tsx.", nodeId: "button", time: "just now", source: "Realizer" },
      { title: "Button gained behavioral meaning", description: "Triggers weather data fetch and updates the dashboard.", nodeId: "button", time: "2 min ago", source: "Producer" },
      { title: "WeatherService joined Logic", description: "A service now carries the weather flow.", nodeId: "weather", time: "5 min ago", source: "Producer" },
      { title: "Dashboard joined UI", description: "The semantic surface now contains Button, Card, and Chart.", nodeId: "dashboard", time: "7 min ago", source: "Producer" },
      { title: "MyApp entered the field", description: "The root meaning opened into interface and logic branches.", nodeId: "myapp", time: "10 min ago", source: "Producer" }
    ],
    selectedId: "button",
    view: "tree",
    filter: "all",
    connectMode: false,
    linkSource: null,
    compareIds: []
  });
  let state = defaults();
  let toastTimer;
  let draggedId = null;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  const nodeById = id => state.nodes.find(node => node.id === id);
  const selectedNode = () => nodeById(state.selectedId) || state.nodes[0] || null;
  const childNodes = parentId => state.nodes.filter(node => node.parentId === parentId);
  const latest = () => state.events[0];
  const slug = value => value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "node";
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
  function addEvent(title, description, nodeId, source = "Producer") {
    state.events.unshift({ title, description, nodeId, time: "just now", source });
    state.events = state.events.slice(0, 30);
  }
  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2600);
  }
  function profileScore(node) {
    const values = Object.values(node.profile || {});
    return Math.round((values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1)) * 100);
  }
  function nodeHasDimension(node, dimension) {
    if (dimension === "behavioral") return Boolean(node.behavior);
    if (dimension === "realization") return Boolean(node.webTarget);
    if (dimension === "relational") return state.relations.some(edge => edge.from === node.id || edge.to === node.id);
    return true;
  }
  function matchesFilter(node) {
    return state.filter === "all" || nodeHasDimension(node, state.filter);
  }
  function glyphFor(node) {
    if (node.webTarget) return "◇";
    if (node.behavior) return "◉";
    return node.parentId === null ? "✳" : "◈";
  }
  function nodeCard(node, compact = false) {
    const selected = node.id === state.selectedId;
    const activeSource = node.id === state.linkSource;
    const isDimmed = !matchesFilter(node);
    const details = [
      `<span class="mini-dimension">${node.parentId === null ? "root" : "structure"}</span>`,
      node.behavior ? '<span class="mini-dimension active-behavior">behavior</span>' : "",
      node.webTarget ? '<span class="mini-dimension active-realization">web target</span>' : ""
    ].filter(Boolean).join("");
    if (compact) {
      return `<button class="flow-node ${selected ? "is-selected" : ""}" data-select="${escapeHTML(node.id)}"><span class="node-glyph ${node.behavior ? "behavioral" : ""} ${node.webTarget ? "target" : ""}">${glyphFor(node)}</span><span class="flow-node-copy"><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)}</small></span></button>`;
    }
    return `<div class="tree-entry ${childNodes(node.id).length ? "has-children" : ""}" data-entry="${escapeHTML(node.id)}">
      <div class="tree-node ${selected ? "is-selected" : ""} ${isDimmed ? "is-dimmed" : ""} ${activeSource ? "is-link-source" : ""}" data-node="${escapeHTML(node.id)}" role="treeitem" aria-selected="${selected}" aria-grabbed="false" tabindex="0" draggable="true" aria-label="${escapeHTML(node.name)}, ${escapeHTML(node.kind)}${node.behavior ? ", has behavior" : ""}${node.webTarget ? ", has web realization target" : ""}">
        <div class="node-topline"><span class="node-glyph ${node.behavior ? "behavioral" : ""} ${node.webTarget ? "target" : ""}">${glyphFor(node)}</span><span class="node-title-wrap"><strong class="node-title">${escapeHTML(node.name)}</strong><small class="node-kind">${escapeHTML(node.kind)}</small></span><span class="node-profile" title="${profileScore(node)}% dimensional richness"><span>${profileScore(node)}</span></span></div>
        <div class="node-bottomline">${details}<span class="node-confidence">${Math.round(node.confidence * 100)}%</span></div>
      </div>
      ${childNodes(node.id).length ? `<div class="tree-children" role="group">${childNodes(node.id).map(child => nodeCard(child)).join("")}</div>` : ""}
    </div>`;
  }
  function renderTree() {
    const roots = state.nodes.filter(node => !node.parentId || !nodeById(node.parentId));
    if (!roots.length) return `<div class="empty-state"><div class="empty-state-inner"><div class="empty-orbit">✳</div><h3>A field, just beginning.</h3><p>Start with a root idea. Add meaning beneath it and Orren will derive the shape as it grows.</p><div class="empty-tip">Try <strong>MyApp → UI → Button</strong></div></div></div>`;
    return `<div class="tree-root" role="tree" aria-label="Semantic hierarchy"><div class="tree-branch">${roots.map(node => nodeCard(node)).join("")}</div></div>`;
  }
  function allRelationships() {
    const treeLinks = state.nodes.filter(node => node.parentId && nodeById(node.parentId)).map(node => ({ from: node.parentId, to: node.id, label: "contains", type: "structure" }));
    return [...treeLinks, ...state.relations.map(edge => ({ ...edge, type: "relation" }))];
  }
  function renderFlow() {
    const links = allRelationships();
    const behaviorNodes = state.nodes.filter(node => node.behavior);
    const realizationNodes = state.nodes.filter(node => node.webTarget);
    const rows = links.map(edge => {
      const from = nodeById(edge.from), to = nodeById(edge.to);
      if (!from || !to) return "";
      return `<div class="flow-row"><button class="flow-node ${state.selectedId === from.id ? "is-selected" : ""}" data-select="${escapeHTML(from.id)}"><span class="node-glyph">${glyphFor(from)}</span><span class="flow-node-copy"><strong>${escapeHTML(from.name)}</strong><small>${escapeHTML(from.kind)}</small></span></button><div class="flow-edge"><span>${escapeHTML(edge.label || "relates")}</span><b>→</b></div><button class="flow-node ${state.selectedId === to.id ? "is-selected" : ""}" data-select="${escapeHTML(to.id)}"><span class="node-glyph ${to.behavior ? "behavioral" : ""} ${to.webTarget ? "target" : ""}">${glyphFor(to)}</span><span class="flow-node-copy"><strong>${escapeHTML(to.name)}</strong><small>${escapeHTML(to.kind)}</small></span></button></div>`;
    });
    behaviorNodes.forEach(node => rows.push(`<div class="flow-row"><button class="flow-node ${state.selectedId === node.id ? "is-selected" : ""}" data-select="${escapeHTML(node.id)}"><span class="node-glyph behavioral">◉</span><span class="flow-node-copy"><strong>${escapeHTML(node.name)}</strong><small>behavioral node</small></span></button><div class="flow-edge"><span>behaves as</span><b>→</b></div><button class="flow-node"><span class="node-glyph behavioral">⌁</span><span class="flow-node-copy"><strong>${escapeHTML(node.behavior)}</strong><small>behavior · intent</small></span></button></div>`));
    realizationNodes.forEach(node => rows.push(`<div class="flow-row"><button class="flow-node ${state.selectedId === node.id ? "is-selected" : ""}" data-select="${escapeHTML(node.id)}"><span class="node-glyph target">◇</span><span class="flow-node-copy"><strong>${escapeHTML(node.name)}</strong><small>semantic target</small></span></button><div class="flow-edge"><span>realizes to</span><b>→</b></div><button class="flow-node"><span class="node-glyph target">⌘</span><span class="flow-node-copy"><strong>${escapeHTML(node.realization === "current" ? "Current artifact" : "Derived artifact")}</strong><small>${escapeHTML(derivedPath(node))}</small></span></button></div>`));
    return `<div class="flow-view"><div class="view-intro"><div><span class="view-overline">MOVEMENT · RELATIONSHIP · REALIZATION</span><h3>How the field moves</h3><p>Structure, behavior, and output stay connected to the same semantic source.</p></div><span class="view-count-pill">${links.length + behaviorNodes.length + realizationNodes.length} edges</span></div><div class="flow-stage">${rows.length ? rows.join("") : '<div class="flow-empty">No relationships yet. Add a second node, then use <strong>Draw a relation</strong> to connect them.</div>'}</div></div>`;
  }
  function renderLens() {
    const nodes = state.nodes;
    const cards = nodes.map(node => {
      const labels = dimensionNames.filter(name => (node.profile?.[name] || 0) > .55 || (name === "Behavioral" && node.behavior));
      const express = Math.round((node.profile?.Expression || 0) * 100);
      const vibe = Math.round((node.profile?.Vibe || 0) * 100);
      const behavior = Math.round((node.profile?.Behavioral || 0) * 100);
      const realization = node.webTarget ? 100 : Math.round((node.profile?.Equilibrium || 0) * 45);
      return `<button class="lens-card ${node.id === state.selectedId ? "is-selected" : ""}" data-select="${escapeHTML(node.id)}"><span class="lens-card-top"><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)}</small></span><span class="lens-profile" aria-label="Dimension profile"><i style="width:${express}%"></i><i style="width:${vibe}%"></i><i class="behavior" style="width:${behavior}%"></i><i class="realization" style="width:${realization}%"></i></span><span class="lens-dim-labels">${labels.slice(0,4).map(label => `<span>${escapeHTML(label)}</span>`).join("")}</span></button>`;
    }).join("");
    const compare = state.compareIds.map(nodeById).filter(Boolean);
    let comparison = "Select up to two nodes to compare their dimensional richness without expanding the whole field into a text dump.";
    if (compare.length === 1) comparison = `${compare[0].name} selected. Choose one more node from the cards above.`;
    if (compare.length === 2) comparison = `${compare[0].name}: ${profileScore(compare[0])}% profile · ${compare[1].name}: ${profileScore(compare[1])}% profile. The focused dimension is shown in the inspector.`;
    return `<div class="lens-view"><div class="view-intro"><div><span class="view-overline">PROGRESSIVE DIMENSIONAL DISPLAY</span><h3>Meaning has a shape.</h3><p>A quick profile first. The full nine dimensions stay one interaction away.</p></div><span class="view-count-pill">9 dimensions</span></div><div class="lens-controls"><button class="dimension-chip selected" data-filter="all">All meaning</button><button class="dimension-chip" data-filter="behavioral">Behavioral</button><button class="dimension-chip" data-filter="relational">Relational</button><button class="dimension-chip" data-filter="realization">Realization</button></div><div class="lens-grid">${cards || '<div class="flow-empty">Add a semantic node to illuminate its profile.</div>'}</div><div class="lens-compare"><strong>Node comparison · ${compare.length}/2</strong><p>${escapeHTML(comparison)}</p><button class="small-action" id="clear-compare" style="margin-top:8px">Clear comparison</button></div></div>`;
  }
  function renderRealizations() {
    if (!state.nodes.length) return `<div class="realizations-view"><div class="view-intro"><div><span class="view-overline">ARTIFACTS FOLLOW MEANING</span><h3>Realization view</h3><p>Targets appear here when a semantic node is ready to take form.</p></div></div><div class="empty-state"><div class="empty-state-inner"><div class="empty-orbit">◇</div><h3>No targets yet.</h3><p>Create a semantic node, select it, then add a web realization target. No implementation path needs to be entered.</p></div></div></div>`;
    const cards = state.nodes.map(node => {
      const hasPath = Boolean(node.webTarget);
      const path = hasPath ? derivedPath(node) : "No target · paths derive from the semantic tree";
      return `<article class="artifact-card ${hasPath ? "" : "is-missing"}"><span class="artifact-icon">◇</span><span class="artifact-copy"><strong>${escapeHTML(node.name)} <span style="color:#718098;font-weight:400">· ${escapeHTML(node.kind)}</span></strong><code>${escapeHTML(path)}</code></span><span class="artifact-status ${hasPath ? "" : "status-missing"}">${hasPath ? escapeHTML(node.realization) : "no target"}</span>${node.id === state.selectedId ? `<div class="artifact-actions">${hasPath ? `<button data-action="realize" data-id="${escapeHTML(node.id)}">${node.realization === "current" ? "Realize again" : "Realize target"}</button><button data-action="remove-target" data-id="${escapeHTML(node.id)}">Remove target</button>` : `<button data-action="add-target" data-id="${escapeHTML(node.id)}">Add web target</button>`}<button data-select="${escapeHTML(node.id)}">Inspect node</button></div>` : ""}</article>`;
    }).join("");
    const ready = state.nodes.filter(node => node.webTarget && node.realization === "current").length;
    return `<div class="realizations-view"><div class="view-intro"><div><span class="view-overline">ARTIFACTS FOLLOW MEANING</span><h3>Realization view</h3><p>Paths are derived from semantic hierarchy and update when structure changes.</p></div><span class="view-count-pill">${ready} current · ${state.nodes.filter(node => node.webTarget).length} targets</span></div><div class="artifact-list">${cards}</div></div>`;
  }
  function renderProvenance() {
    const events = state.events.map(event => {
      const node = nodeById(event.nodeId);
      const name = node?.name || "Field";
      return `<article class="timeline-item"><span class="timeline-dot"></span><div class="timeline-copy"><strong>${escapeHTML(event.title)}</strong><p>${escapeHTML(event.description)} <span style="color:#71839c">· ${escapeHTML(event.source)} · ${escapeHTML(name)}</span></p></div><time class="timeline-time">${escapeHTML(event.time)}</time></article>`;
    }).join("");
    return `<div class="provenance-view"><div class="view-intro"><div><span class="view-overline">A MEANINGFUL HISTORY</span><h3>Nothing disappears.</h3><p>Producer actions, structural refinements, and realizations stay connected to their semantic origin.</p></div><span class="view-count-pill">${state.events.length} events</span></div><div class="timeline">${events || '<div class="flow-empty">The next meaningful change will begin this trail.</div>'}</div></div>`;
  }
  const viewInfo = {
    tree: { title: "Semantic tree", subtitle: "Place meaning, not files or folders", icon: "◈" },
    flow: { title: "Flow graph", subtitle: "See structure, behavior, and output move", icon: "⌁" },
    lens: { title: "Dimension lens", subtitle: "Reveal the shape of meaning progressively", icon: "◉" },
    realizations: { title: "Realization view", subtitle: "Follow semantic intent into derived artifacts", icon: "◇" },
    provenance: { title: "Provenance trail", subtitle: "Trace each change back to its semantic origin", icon: "◷" }
  };
  function observerText(node) {
    if (!node) return state.nodes.length ? "The Observer is reading the shared field." : "The field is quiet. Add a root idea when you are ready.";
    const facts = [];
    facts.push(`${state.nodes.length} ${state.nodes.length === 1 ? "node" : "nodes"} visible`);
    if (node.behavior) facts.push(`${node.name} carries behavioral intent`);
    if (node.webTarget) facts.push(`its web artifact is ${node.realization}`);
    else facts.push("no implementation path has been requested");
    if (state.connectMode) facts.push(state.linkSource ? "waiting for the relationship destination" : "relationship drawing is ready");
    return `Watching ${node.name} · ${facts.join(" · ")}.`;
  }
  function renderInspector() {
    const node = selectedNode();
    const content = $("#inspector-content");
    if (!node) {
      content.innerHTML = `<div class="empty-state" style="min-height:180px;padding:10px"><div class="empty-state-inner"><div class="empty-orbit">◈</div><h3>No selection.</h3><p>Create the first idea and the Observer will follow its meaning.</p></div></div>`;
      return;
    }
    const confidence = Math.round(node.confidence * 100);
    const present = ["Expression", "Cognitive", "Vibe"].filter(name => node.profile?.[name] >= .6);
    if (node.behavior) present.push("Behavioral");
    if (state.relations.some(edge => edge.from === node.id || edge.to === node.id)) present.push("Relational");
    const point = (index, radius) => {
      const angle = (Math.PI * 2 * index) / dimensionNames.length - Math.PI / 2;
      return `${(48 + Math.cos(angle) * radius).toFixed(1)},${(43 + Math.sin(angle) * radius).toFixed(1)}`;
    };
    const radarAxes = dimensionNames.map((name, index) => `<line x1="48" y1="43" x2="${point(index, 38).split(",")[0]}" y2="${point(index, 38).split(",")[1]}" />`).join("");
    const radarGrid = [.33, .66, 1].map(scale => `<polygon points="${dimensionNames.map((_, index) => point(index, 38 * scale)).join(" ")}" />`).join("");
    const radarData = dimensionNames.map((name, index) => point(index, 38 * Math.max(.09, node.profile?.[name] || 0))).join(" ");
    const radar = `<svg class="radar-svg" viewBox="0 0 96 86" role="img" aria-label="Nine-dimension profile radar"><g class="radar-grid">${radarGrid}${radarAxes}</g><polygon class="radar-fill" points="${radarData}"/><polygon class="radar-outline" points="${radarData}"/>${dimensionNames.map((name, index) => `<circle class="radar-point" cx="${point(index, 38 * Math.max(.09, node.profile?.[name] || 0)).split(",")[0]}" cy="${point(index, 38 * Math.max(.09, node.profile?.[name] || 0)).split(",")[1]}" r="1.7"/>`).join("")}</svg>`;
    const dims = dimensionNames.map((name, index) => {
      const value = Math.round((node.profile?.[name] || 0) * 100);
      return `<div class="dimension-bar-row"><span class="dimension-swatch swatch-${index}"></span><span class="dimension-bar-name">${name}</span><span class="dimension-bar-track"><i class="bar-${index}" style="width:${value}%"></i></span><span class="dimension-bar-value">${(value / 100).toFixed(2)}</span></div>`;
    }).join("");
    const path = derivedPath(node);
    const statuses = [
      { name: "Web", state: node.webTarget ? node.realization : "Not realized", icon: "◉", path: node.webTarget ? path : "src/ui/dashboard/Button.tsx", className: node.webTarget && node.realization === "current" ? "current" : "waiting" },
      { name: "Android", state: "Degraded", icon: "♙", path: "app/src/main/java/…/Button.kt", className: "degraded" },
      { name: "Rust", state: "Not realized", icon: "◌", path: "src/button.rs", className: "waiting" }
    ].map(target => `<div class="target-row"><span class="target-icon ${target.className}">${target.icon}</span><span class="target-copy"><strong>${target.name}</strong><small>${escapeHTML(target.path)}</small></span><span class="target-state ${target.className}">${target.className === "current" ? "✓ " : target.className === "degraded" ? "⚠ " : "○ "}${escapeHTML(target.state)}</span></div>`).join("");
    content.innerHTML = `<section class="selected-node-card"><div class="selected-node-head"><span class="selected-node-seal"><img src="assets/orren-emblem.webp" alt=""></span><span class="selected-node-name"><strong>${escapeHTML(node.name)}</strong><small>${escapeHTML(node.kind)} · ${node.parentId ? `inside ${escapeHTML(nodeById(node.parentId)?.name || "Field")}` : "field root"}</small></span><span class="active-badge"><i></i>Active</span><button class="icon-button subtle selected-menu" aria-label="Node options">···</button><button class="close-inspector" aria-label="Close detail" title="Close detail">×</button></div>${node.behavior ? `<p class="selected-behavior">${escapeHTML(node.behavior)}</p>` : '<p class="selected-behavior muted-behavior">Add a behavior to give this node intent.</p>'}<div class="node-tags"><span>Behavioral</span><span>${escapeHTML(node.name === "Button" ? "UI" : node.kind)}</span><span>Interactive</span></div>
      <div class="detail-grid"><section class="dimension-card"><div class="detail-title">Dimensions <button id="toggle-dimensions" aria-expanded="true">9 in view</button></div><div class="dimension-visual">${radar}<div class="dimension-bars" id="dimension-list">${dims}</div></div></section><section class="realization-card"><div class="detail-title">Realization Status</div><div class="target-list">${statuses}</div></section></div>
      <div class="derived-path-card"><span>Path <span>(derived)</span></span><code class="${path ? "" : "path-missing"}">${escapeHTML(path || "Add a web target to derive this path")}</code><button class="copy-path" id="copy-path" title="Copy derived path" ${path ? "" : "disabled"}>▢</button></div>
      <details class="inspector-section behavior-editor"><summary><strong>REFINE MEANING</strong><span>Visual Producer</span></summary><form class="intent-form" id="intent-form"><label class="sr-only" for="intent-input">Describe a behavior for ${escapeHTML(node.name)}</label><textarea id="intent-input" maxlength="180" placeholder="Describe a behavior… e.g. Make it fetch the weather"></textarea><div class="intent-actions"><button class="small-action" type="submit">+ Add behavior</button><button class="small-action target-action" type="button" id="add-target">◇ ${node.webTarget ? "Target added" : "Add web target"}</button>${node.webTarget ? `<button class="small-action realize-action" type="button" id="realize">${node.realization === "current" ? "✓ Current" : "Realize"}</button>` : ""}</div></form></details>`;
    $("#observer-readout").textContent = observerText(node);
    $("#observer-time").textContent = latest()?.time?.toUpperCase() || "JUST NOW";
    $("#create-context").textContent = node ? `inside ${node.name}` : "new root node";
    $("#workspace-name").textContent = state.nodes.find(item => item.parentId === null)?.name || "Untitled field";
  }
  function render() {
    const info = viewInfo[state.view];
    $$(".view-link").forEach(button => {
      const active = button.dataset.view === state.view;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    $("#field-view").setAttribute("aria-labelledby", `tab-${state.view}`);
    $("#current-view-title").textContent = info.title;
    $("#current-view-subtitle").textContent = info.subtitle;
    $("#current-view-icon").textContent = info.icon;
    const html = { tree: renderTree, flow: renderFlow, lens: renderLens, realizations: renderRealizations, provenance: renderProvenance }[state.view]();
    $("#field-view").innerHTML = html;
    $("#field-summary").textContent = `${state.nodes.length} ${state.nodes.length === 1 ? "node" : "nodes"} · ${allRelationships().length} ${allRelationships().length === 1 ? "relationship" : "relationships"}`;
    $("#node-count").textContent = String(state.nodes.length).padStart(2, "0");
    $("#artifact-count").textContent = String(state.nodes.filter(node => node.webTarget).length).padStart(2, "0");
    $("#connect-mode").classList.toggle("is-active", state.connectMode);
    $("#connect-hint").hidden = !state.connectMode;
    $("#connect-hint").firstChild.textContent = state.linkSource ? `Now choose a destination for ${nodeById(state.linkSource)?.name || "this node"}. ` : "Choose a starting node, then choose the node it connects to. ";
    $$(".dimension-chip").forEach(button => button.classList.toggle("selected", button.dataset.filter === state.filter));
    renderInspector();
  }
  function changeView(view) { if (!viewInfo[view]) return; state.view = view; render(); }
  function addNode(name, parentId) {
    const cleanName = name.trim().replace(/\s+/g, " ");
    if (!cleanName) return;
    const parent = nodeById(parentId);
    const id = `${slug(cleanName)}-${Date.now().toString(36).slice(-5)}`;
    const node = { id, name: cleanName, parentId: parent?.id || null, kind: parent ? "Structure" : "Semantic root", confidence: .93, behavior: "", webTarget: false, realization: "missing", profile: { Expression: .87, Cognitive: .74, Vibe: .74, Spatial: .42, Temporal: .23, Relational: .28, Conditional: .19, Behavioral: .12, Equilibrium: .62 } };
    state.nodes.push(node);
    state.selectedId = node.id;
    addEvent(`${cleanName} added to the field`, parent ? `Placed inside ${parent.name}; descendants inherit derived realization paths.` : "New semantic root established; implementation paths remain derived.", node.id);
    render();
    showToast(parent ? `${cleanName} placed inside ${parent.name}.` : `${cleanName} entered the living field.`);
  }
  function isDescendant(candidateId, parentId) {
    let cursor = nodeById(parentId);
    while (cursor) {
      if (cursor.id === candidateId) return true;
      cursor = nodeById(cursor.parentId);
    }
    return false;
  }
  function moveNode(nodeId, newParentId) {
    const node = nodeById(nodeId), parent = nodeById(newParentId);
    if (!node || !parent || node.id === parent.id || isDescendant(node.id, parent.id)) { showToast("That move would make a semantic loop."); return; }
    if (node.parentId === parent.id) { showToast(`${node.name} is already inside ${parent.name}.`); return; }
    const before = node.webTarget ? derivedPath(node) : "";
    node.parentId = parent.id;
    node.kind = node.kind === "Semantic root" ? "Structure" : node.kind;
    const after = node.webTarget ? derivedPath(node) : "";
    state.selectedId = node.id;
    addEvent(`${node.name} moved under ${parent.name}`, node.webTarget ? `The semantic move changed its derived path from ${before} to ${after}.` : "The semantic hierarchy changed; any future path will follow this placement.", node.id);
    render();
    showToast(node.webTarget ? `Path updated · ${after}` : `${node.name} now lives inside ${parent.name}.`);
  }
  function connectNodes(fromId, toId) {
    if (!fromId || !toId || fromId === toId) { showToast("Choose two different semantic nodes."); return; }
    const exists = state.relations.some(edge => edge.from === fromId && edge.to === toId);
    if (exists) { showToast("That relationship is already in the field."); return; }
    const from = nodeById(fromId), to = nodeById(toId);
    if (!from || !to) return;
    state.relations.push({ from: fromId, to: toId, label: "relates to" });
    from.profile.Relational = Math.max(from.profile.Relational || 0, .82);
    to.profile.Relational = Math.max(to.profile.Relational || 0, .82);
    state.selectedId = toId;
    addEvent(`${from.name} connected to ${to.name}`, "A relationship proposal was added by the Visual Producer; the Observer exposes it in the Flow Graph.", toId);
    state.linkSource = null;
    state.connectMode = false;
    render();
    showToast(`Relationship proposed · ${from.name} → ${to.name}`);
  }
  function addBehavior(nodeId, text) {
    const node = nodeById(nodeId);
    const behavior = text.trim();
    if (!node || !behavior) { showToast("Describe the behavior you want this node to carry."); return; }
    node.behavior = behavior;
    node.profile.Behavioral = Math.max(node.profile.Behavioral || 0, .9);
    node.confidence = Math.min(.99, Math.max(node.confidence, .9));
    if (node.webTarget && node.realization === "current") node.realization = "stale";
    addEvent(`${node.name} gained behavioral meaning`, `Intent recorded: “${behavior}”. Existing targets, if any, are now stale.`, node.id);
    render();
    showToast(`Behavior added to ${node.name}. The field kept the intent.`);
  }
  function addTarget(nodeId) {
    const node = nodeById(nodeId);
    if (!node) return;
    if (node.webTarget) { showToast("A web target is already attached to this node."); return; }
    node.webTarget = true;
    node.profile.Equilibrium = Math.max(node.profile.Equilibrium || 0, .76);
    node.realization = "missing";
    addEvent(`Web target added to ${node.name}`, `Orren derived ${derivedPath(node)} from its current semantic placement.`, node.id);
    state.view = "realizations";
    render();
    showToast(`Web target added · ${derivedPath(node)}`);
  }
  function realize(nodeId) {
    const node = nodeById(nodeId);
    if (!node?.webTarget) { showToast("Add a web target before realizing this node."); return; }
    const path = derivedPath(node);
    node.realization = "current";
    addEvent(`${node.name} realized for web`, `Artifact is current at ${path}. The path is derived from semantic placement.`, node.id, "Realizer");
    render();
    showToast(`Realized · ${path}`);
  }
  $(".view-nav").addEventListener("click", event => {
    const button = event.target.closest("[data-view]");
    if (button) changeView(button.dataset.view);
  });
  $(".brand-nav").addEventListener("click", event => {
    const button = event.target.closest("[data-shell-view]");
    if (button) changeView(button.dataset.shellView);
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
  $("#node-form").addEventListener("submit", event => {
    event.preventDefault();
    const input = $("#node-name");
    if (!state.nodes.length) addNode(input.value, null);
    else addNode(input.value, selectedNode()?.id || state.nodes[0].id);
    input.value = "";
    input.focus();
  });
  $("#focus-create").addEventListener("click", () => { $("#node-name").focus(); $("#node-name").scrollIntoView({ block: "nearest", behavior: "smooth" }); });
  $("#empty-field").addEventListener("click", () => {
    state = { ...defaults(), nodes: [], relations: [], events: [], selectedId: null, view: "tree", filter: "all", connectMode: false, linkSource: null, compareIds: [] };
    render();
    $("#node-name").focus();
    showToast("A clean field is ready for its first idea.");
  });
  $("#load-example").addEventListener("click", () => { state = defaults(); render(); showToast("The MyApp → UI → Button example is in view."); });
  $("#filter-toggle").addEventListener("click", () => {
    const panel = $("#dimension-filter");
    const open = panel.hidden;
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
    showToast(state.connectMode ? "Draw a relationship: choose the source node." : "Relationship drawing closed.");
  });
  $("#cancel-connect").addEventListener("click", () => { state.connectMode = false; state.linkSource = null; render(); });
  $("#field-view").addEventListener("click", event => {
    const action = event.target.closest("[data-action]");
    if (action) {
      const id = action.dataset.id;
      if (action.dataset.action === "add-target") addTarget(id);
      if (action.dataset.action === "realize") realize(id);
      if (action.dataset.action === "remove-target") {
        const node = nodeById(id);
        if (node) { node.webTarget = false; node.realization = "missing"; addEvent(`Web target removed from ${node.name}`, "The realization target was removed; semantic meaning remains.", node.id); render(); showToast("Target removed. The semantic node is unchanged."); }
      }
      return;
    }
    const select = event.target.closest("[data-select]");
    const treeItem = event.target.closest("[data-node]");
    const id = select?.dataset.select || treeItem?.dataset.node;
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
    render();
  });
  $("#field-view").addEventListener("keydown", event => {
    const node = event.target.closest("[data-node]");
    if (node && ["Enter", " "].includes(event.key)) { event.preventDefault(); node.click(); }
  });
  $("#field-view").addEventListener("dragstart", event => {
    const node = event.target.closest("[data-node]");
    if (!node) return;
    draggedId = node.dataset.node;
    node.setAttribute("aria-grabbed", "true");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedId);
  });
  $("#field-view").addEventListener("dragend", event => {
    const node = event.target.closest("[data-node]");
    if (node) node.setAttribute("aria-grabbed", "false");
    draggedId = null;
  });
  $("#field-view").addEventListener("dragover", event => {
    if (event.target.closest("[data-node]") && draggedId) { event.preventDefault(); event.dataTransfer.dropEffect = "move"; }
  });
  $("#field-view").addEventListener("drop", event => {
    const target = event.target.closest("[data-node]");
    if (!target) return;
    event.preventDefault();
    const sourceId = event.dataTransfer.getData("text/plain") || draggedId;
    if (sourceId) moveNode(sourceId, target.dataset.node);
  });
  $("#field-view").addEventListener("click", event => {
    if (event.target.closest("#clear-compare")) { state.compareIds = []; render(); }
  });
  $("#inspector-content").addEventListener("submit", event => {
    if (event.target.id !== "intent-form") return;
    event.preventDefault();
    addBehavior(state.selectedId, $("#intent-input").value);
  });
  $("#inspector-content").addEventListener("click", event => {
    if (event.target.closest("#copy-path")) {
      const currentPath = derivedPath(selectedNode());
      if (currentPath && navigator.clipboard?.writeText) navigator.clipboard.writeText(currentPath).then(() => showToast("Derived path copied."), () => showToast(currentPath));
      return;
    }
    if (event.target.closest("#toggle-dimensions")) {
      const list = $("#dimension-list");
      list.hidden = !list.hidden;
      event.target.closest("#toggle-dimensions").textContent = list.hidden ? "Inspect all 9" : "Hide detail";
      return;
    }
    if (event.target.closest("#add-target")) { addTarget(state.selectedId); return; }
    if (event.target.closest("#realize")) { realize(state.selectedId); return; }
  });
  $("#field-view").addEventListener("click", event => {
    const clear = event.target.closest("#clear-compare");
    if (clear) { state.compareIds = []; render(); }
  });
  render();
})();
