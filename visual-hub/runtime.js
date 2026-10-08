(() => {
  const hub = window.OrrenVisualHub;
  if (!hub) return;
  let connected = false;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  async function request(path, options = {}) {
    const response = await fetch(path, { cache: "no-store", ...options });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `Orren Engine returned HTTP ${response.status}.`);
    return payload;
  }

  async function mutate(action, options = {}) {
    const previousIds = new Set(hub.getState().nodes.map(node => node.id));
    try {
      const snapshot = await request("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action)
      });
      hub.applyRuntimeSnapshot(snapshot);
      if (action.action === "create") {
        const created = snapshot.nodes.find(node => !previousIds.has(node.id));
        if (created) hub.selectNode(created.id);
        const input = $("#node-name");
        if (input) { input.value = ""; input.focus(); }
        hub.showToast(created ? `${created.name} created in the live SIR graph.` : "SIR graph updated.");
      } else if (action.action === "move") {
        hub.selectNode(action.nodeId);
        hub.showToast("Hierarchy changed in SIR; semantic paths were recomputed.");
      } else if (action.action === "relate") {
        hub.clearProposal();
        hub.selectRelation(action.from, action.to, action.type);
        hub.showToast("Typed relationship added to the SIR graph.");
      } else if (action.action === "behavior") {
        const input = $("#intent-input");
        if (input) input.value = "";
        hub.showToast("Behavioral statement added to SIR and realization plans refreshed.");
      } else if (action.action === "realize") {
        hub.setView("realizations");
        hub.showToast(snapshot.runtime.codegenAvailable ? "Coordinator plans refreshed; no source files were written." : "Coordinator plans refreshed. Source generation is unavailable; no files were written.");
      } else if (action.action === "add_target" || action.action === "remove_target") {
        hub.setView("realizations");
        hub.showToast(action.action === "add_target" ? "Target added to the SIR field; its plan is ready." : "Target removed from SIR; the coordinator plans were refreshed.");
      } else if (action.action === "reset") {
        hub.setView("tree");
        hub.showToast(action.mode === "empty" ? "A new in-memory SIR root is ready." : "The MyApp .orn example is loaded in the Engine.");
      }
      return snapshot;
    } catch (error) {
      hub.showToast(error.message || "The Orren Engine action could not be completed.");
      return null;
    }
  }

  function stop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
  }

  document.addEventListener("submit", event => {
    if (!connected) return;
    const form = event.target;
    if (form.id === "node-form") {
      stop(event);
      const state = hub.getState();
      mutate({ action: "create", name: $("#node-name").value, parentId: state.selectedId || state.nodes.find(node => !node.parentId)?.id });
    } else if (form.id === "intent-form") {
      stop(event);
      const state = hub.getState();
      mutate({ action: "behavior", nodeId: state.selectedId, text: $("#intent-input").value });
    } else if (form.id === "relation-form") {
      stop(event);
      const state = hub.getState();
      if (!state.pendingRelation) return;
      mutate({
        action: "relate",
        from: state.pendingRelation.from,
        to: state.pendingRelation.to,
        type: $("#relation-type").value,
        note: $("#relation-note").value.trim()
      });
    }
  }, true);

  document.addEventListener("click", event => {
    if (!connected) return;
    const target = event.target.closest("button");
    if (!target) return;
    if (target.id === "load-example") {
      stop(event);
      mutate({ action: "reset", mode: "example" });
      return;
    }
    if (target.id === "empty-field") {
      stop(event);
      mutate({ action: "reset", mode: "empty" });
      return;
    }
    if (target.id === "add-target") {
      stop(event);
      hub.setView("realizations");
      return;
    }
    if (target.id === "action-realize" || target.id === "realize" || target.id === "refresh-plans") {
      stop(event);
      mutate({ action: "realize", nodeId: hub.getState().selectedId });
      return;
    }
    const action = target.dataset.action;
    if (action === "add-target") {
      stop(event);
      mutate({ action: "add_target", target: target.dataset.target });
    } else if (action === "remove-target") {
      stop(event);
      mutate({ action: "remove_target", target: target.dataset.target });
    } else if (action === "realize") {
      stop(event);
      mutate({ action: "realize", nodeId: hub.getState().selectedId });
    }
  }, true);

  document.addEventListener("drop", event => {
    if (!connected) return;
    const target = event.target.closest("[data-sidebar-node]");
    if (!target) return;
    const sourceId = event.dataTransfer?.getData("text/plain");
    if (!sourceId) return;
    stop(event);
    mutate({ action: "move", nodeId: sourceId, parentId: target.dataset.sidebarNode });
  }, true);

  async function boot() {
    try {
      const snapshot = await request("/api/field");
      connected = Boolean(snapshot.runtime?.connected);
      if (!connected) throw new Error("Orren Engine API did not report a live session.");
      hub.applyRuntimeSnapshot(snapshot);
      const liveNote = snapshot.runtime.codegenAvailable
        ? `Connected to Orren Engine ${snapshot.runtime.engineVersion}.`
        : `SIR engine connected. ${snapshot.runtime.codegenMessage}`;
      console.info(`[Orren Visual Hub] ${liveNote}`);
    } catch (error) {
      connected = false;
      console.warn("[Orren Visual Hub] Engine bridge unavailable; keeping the illustrative local preview.", error);
      const status = $("#engine-status");
      if (status) status.title = `Engine API unavailable: ${error.message}. Local preview remains usable.`;
    }
  }

  boot();
})();
