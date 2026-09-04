"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import cytoscape, { type Core, type EdgeSingular, type NodeSingular } from "cytoscape";
import type { CaseGraph, GraphNodePublic } from "@/lib/types";
import MaskedId from "./MaskedId";

/** Chromium's getComputedStyle serializes translucent CSS colors as
 * 8-digit hex (#rrggbbaa) — a form cytoscape's own color parser doesn't
 * recognize, which made every rgba() design token (borders, the device/
 * merchant fills) silently fail to apply. Round-tripping through a
 * throwaway canvas 2D context normalizes back to a form cytoscape
 * accepts (#rrggbb or rgba(...)), without hand-rolling a hex8 parser. */
function toCanvasColor(raw: string): string {
  try {
    const ctx = document.createElement("canvas").getContext("2d");
    if (!ctx) return raw;
    ctx.fillStyle = raw;
    return ctx.fillStyle;
  } catch {
    return raw;
  }
}

/** Cytoscape draws to canvas, not the DOM, so it can't resolve CSS
 * custom properties itself — read the real computed values once so the
 * graph stays on the same design tokens as the rest of the app instead
 * of a second, hardcoded color language. */
function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const get = (name: string, fallback: string) => toCanvasColor(style.getPropertyValue(name).trim() || fallback);
  return {
    cobalt: get("--cobalt", "#16a36a"),
    cobaltForeground: get("--cobalt-foreground", "#f2f5f3"),
    amber: get("--amber", "#d88a45"),
    graphite: get("--graphite", "rgba(8,16,12,0.6)"),
    graphiteForeground: get("--graphite-foreground", "#a5b0aa"),
    muted: get("--muted", "#a5b0aa"),
    border: get("--border", "rgba(180,220,200,0.14)"),
    foreground: get("--foreground", "#f2f5f3"),
    panel: get("--panel", "rgba(14,29,22,0.55)"),
    panelSolid: get("--panel-solid", "#101a15"),
    canvas: get("--canvas", "#050807"),
    riskHigh: get("--risk-high", "#f04438"),
    riskCritical: get("--risk-critical", "#f04438"),
    font: get("--font-mono", "monospace"),
  };
}

const NODE_TYPE_LABEL: Record<string, string> = {
  account: "Account",
  device: "Device",
  ip: "IP Address",
  merchant: "Merchant",
};

/** Fixed legend order — the real, complete set of entity types the graph
 * API returns (GraphNodePublic.node_type). Never invented categories. */
const NODE_TYPE_ORDER: GraphNodePublic["node_type"][] = ["account", "device", "ip", "merchant"];

const NODE_TYPE_SHAPE_GLYPH: Record<string, string> = {
  account: "●",
  device: "▢",
  ip: "◆",
  merchant: "▲",
};

/** A node's real transaction count, derived from real edge weights
 * (GraphBuilder increments an edge's weight once per transaction that
 * used that account+device/IP pair) — not a separate backend field,
 * genuinely summable from what the API already returned. */
function transactionCountFor(nodeId: string, graph: CaseGraph): number {
  return graph.edges
    .filter((e) => e.source === nodeId || e.target === nodeId)
    .reduce((sum, e) => sum + e.weight, 0);
}

/** Count of distinct entities directly linked to a node — derived from
 * the real edge list, not a separate backend field. */
function connectedCountFor(nodeId: string, graph: CaseGraph): number {
  const ids = new Set<string>();
  for (const e of graph.edges) {
    if (e.source === nodeId) ids.add(e.target);
    else if (e.target === nodeId) ids.add(e.source);
  }
  return ids.size;
}

type GraphMode = "compact" | "full";

export default function FraudRingGraph({
  graph,
  mode = "compact",
}: {
  graph: CaseGraph | null;
  /** "compact" (default) keeps the current small in-page footprint.
   * "full" is the dedicated /network/explore workspace — same component,
   * same data, more room and a heavier toolset. */
  mode?: GraphMode;
}) {
  const isFull = mode === "full";
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selected, setSelected] = useState<GraphNodePublic | null>(null);
  const [hover, setHover] = useState<{ node: GraphNodePublic; x: number; y: number } | null>(null);
  const [search, setSearch] = useState("");
  const searchQuery = search.trim().toLowerCase();
  const searchMiss =
    isFull && !!graph && searchQuery.length > 0 && !graph.nodes.some((n) => n.label.toLowerCase().includes(searchQuery));

  /** Highlights a node's closed neighborhood (itself + directly connected
   * nodes/edges) and dims everything else — used by both hover (nothing
   * selected) and click (persistent) focus, and by search. Never hides
   * elements, only mutes them, so the real relationships stay visible. */
  const focusNeighborhood = useCallback((nodeId: string | null) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("cy-related cy-faded");
    if (!nodeId) return;
    const node = cy.$id(nodeId);
    if (node.empty()) return;
    const neighborhood = node.closedNeighborhood();
    cy.elements().not(neighborhood).addClass("cy-faded");
    neighborhood.addClass("cy-related");
  }, []);

  useEffect(() => {
    if (!graph) return;

    function build() {
      const container = containerRef.current;
      if (!container || !graph) return;
      const tokens = readTokens();

      const countMap = new Map(graph.nodes.map((n) => [n.id, transactionCountFor(n.id, graph)]));
      const maxCount = Math.max(1, ...Array.from(countMap.values()));
      const baseSize = isFull ? 32 : 26;
      const growSize = isFull ? 26 : 16;
      const flaggedSize = isFull ? 64 : 54;
      function sizeFor(nodeId: string) {
        if (nodeId === graph!.flagged_node_id) return flaggedSize;
        const t = (countMap.get(nodeId) ?? 0) / maxCount;
        return baseSize + growSize * t;
      }

      const shapeByType: Record<string, cytoscape.Css.NodeShape> = {
        account: "ellipse",
        device: "round-rectangle",
        ip: "diamond",
        merchant: "triangle",
      };
      const fillByType: Record<string, string> = {
        account: tokens.cobalt,
        device: tokens.graphite,
        ip: tokens.muted,
        merchant: tokens.border,
      };
      const textByType: Record<string, string> = {
        account: tokens.cobaltForeground,
        device: tokens.graphiteForeground,
        ip: tokens.panelSolid,
        merchant: tokens.panelSolid,
      };

      const elements = [
        ...graph.nodes.map((n) => ({
          data: {
            id: n.id,
            label: n.label,
            node_type: n.node_type,
            is_suspicious: n.is_suspicious,
            flagged: n.id === graph.flagged_node_id,
          },
        })),
        ...graph.edges.map((e, i) => ({
          data: {
            id: `e${i}`,
            source: e.source,
            target: e.target,
            weight: e.weight,
          },
        })),
      ];

      const cy = cytoscape({
        container,
        elements,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "font-size": isFull ? 11 : 9,
              "font-family": tokens.font,
              "font-weight": 600,
              color: (ele: NodeSingular) => textByType[ele.data("node_type") as string] ?? tokens.foreground,
              "text-valign": "bottom",
              "text-halign": "center",
              "text-margin-y": 4,
              "text-wrap": "wrap",
              "text-max-width": isFull ? "90px" : "70px",
              "text-background-color": tokens.canvas,
              "text-background-opacity": 0.75,
              "text-background-padding": "2px",
              "text-background-shape": "roundrectangle",
              shape: (ele: NodeSingular) => shapeByType[ele.data("node_type") as string] ?? "ellipse",
              "background-color": (ele: NodeSingular) => fillByType[ele.data("node_type") as string] ?? tokens.muted,
              width: (ele: NodeSingular) => sizeFor(ele.id()),
              height: (ele: NodeSingular) => sizeFor(ele.id()),
              "border-width": (ele: NodeSingular) =>
                ele.data("flagged") ? 4 : ele.data("is_suspicious") ? 3 : 1.5,
              "border-color": (ele: NodeSingular) =>
                ele.data("flagged")
                  ? tokens.riskCritical
                  : ele.data("is_suspicious")
                    ? tokens.riskHigh
                    : tokens.border,
              "border-opacity": 1,
              "underlay-opacity": 0,
              "underlay-color": tokens.cobalt,
              "underlay-padding": 8,
              "underlay-shape": "ellipse",
              "transition-property": "underlay-opacity, border-width, opacity",
              "transition-duration": 120,
            },
          },
          {
            // A gentle emerald halo on hover — real feedback, not a
            // decorative pulse (see globals rule: motion needs a reason).
            selector: "node.cy-hover",
            style: { "underlay-opacity": 0.35, "underlay-color": tokens.cobalt },
          },
          {
            selector: "node:selected",
            style: {
              "border-color": tokens.cobalt,
              "border-width": 5,
              "underlay-opacity": 0.45,
              "underlay-color": tokens.cobalt,
            },
          },
          {
            selector: "node.cy-faded",
            style: { opacity: 0.22, "text-opacity": 0.35 },
          },
          {
            selector: "node.cy-related",
            style: { opacity: 1 },
          },
          {
            selector: "edge",
            style: {
              width: (ele: EdgeSingular) => 0.75 + Math.min(ele.data("weight") as number, 6) * 0.5,
              "line-color": tokens.border,
              "curve-style": "bezier",
              "target-arrow-shape": "none",
              opacity: 0.55,
              "transition-property": "line-color, opacity, width",
              "transition-duration": 120,
            },
          },
          {
            selector: "edge.cy-related",
            style: {
              "line-color": tokens.cobalt,
              opacity: 0.95,
              width: (ele: EdgeSingular) => 1.5 + Math.min(ele.data("weight") as number, 6) * 0.5,
            },
          },
          {
            selector: "edge.cy-faded",
            style: { opacity: 0.06 },
          },
        ],
        layout: {
          name: "cose",
          animate: false,
          fit: true,
          padding: isFull ? 56 : 20,
          nodeOverlap: isFull ? 28 : 18,
          nodeRepulsion: isFull ? 14000 : 9000,
          idealEdgeLength: isFull ? 130 : 85,
          edgeElasticity: 120,
          nestingFactor: 1.2,
          gravity: 70,
          numIter: 2500,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
          componentSpacing: isFull ? 120 : 70,
        } as cytoscape.LayoutOptions,
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
        minZoom: 0.25,
        maxZoom: isFull ? 3.5 : 2.5,
      });

      // Selection state lives on cytoscape's own :selected pseudostate
      // (tapping a node selects it, tapping the background unselects —
      // both built in); these events are the single place React state
      // syncs to it, so a search-driven `ele.select()` and a click both
      // flow through the same path instead of duplicating the logic.
      cy.on("select", "node", (evt) => {
        const id = evt.target.id();
        const node = graph.nodes.find((n) => n.id === id) ?? null;
        setSelected(node);
        setHover(null);
        focusNeighborhood(id);
      });
      cy.on("unselect", "node", () => {
        if (cy.$("node:selected").length) return;
        setSelected(null);
        focusNeighborhood(null);
      });

      cy.on("mouseover", "node", (evt) => {
        const target = evt.target as NodeSingular;
        target.addClass("cy-hover");
        const id = target.id();
        const node = graph.nodes.find((n) => n.id === id) ?? null;
        if (!node) return;
        // Hovering previews the same relationship focus a click gives —
        // but only when nothing is already pinned by selection, so a
        // hover never fights an analyst's active selection.
        if (!cy.$("node:selected").length) focusNeighborhood(id);
        const pos = target.renderedPosition();
        const rect = container.getBoundingClientRect();
        setHover({ node, x: rect.left + pos.x, y: rect.top + pos.y });
      });
      cy.on("mouseout", "node", (evt) => {
        (evt.target as NodeSingular).removeClass("cy-hover");
        setHover(null);
        if (!cy.$("node:selected").length) focusNeighborhood(null);
      });

      cyRef.current = cy;
    }

    build();

    // Canvas colors were baked in at build time from computed CSS custom
    // properties — rebuild if the OS/browser theme flips while this page
    // is open, so the graph doesn't stay stuck in the old theme's colors.
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onThemeChange = () => {
      cyRef.current?.destroy();
      build();
    };
    media.addEventListener("change", onThemeChange);

    // The container can still be mid-layout (e.g. sidebar/flex sizing not
    // settled, or a panel expanding) on the very first frame cytoscape
    // measures it — a 0-width container at build time doesn't just draw
    // small, cose lays every node out on top of itself, and resize()+fit()
    // alone can't recover real positions from that. Re-running the layout
    // (cheap for these graph sizes) is what actually fixes it, and it
    // doubles as keeping the graph sane if the container reflows later
    // (full mode's toolbar/legend, a sidebar toggle, etc.).
    let lastSize = 0;
    const resizeObserver = new ResizeObserver((entries) => {
      const cy = cyRef.current;
      if (!cy) return;
      const size = entries[0]?.contentRect.width ?? 0;
      if (size === lastSize) return;
      lastSize = size;
      cy.resize();
      cy.layout({ name: "cose", animate: false, fit: true, padding: isFull ? 56 : 20 } as cytoscape.LayoutOptions).run();
    });
    if (containerRef.current) resizeObserver.observe(containerRef.current);

    return () => {
      media.removeEventListener("change", onThemeChange);
      resizeObserver.disconnect();
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [graph, isFull, focusNeighborhood]);

  // Full-mode search: jump to and focus the first node whose (already
  // masked) label contains the query — pure client-side filtering over
  // data already on screen, nothing fetched or fabricated. Selecting the
  // element (rather than setting React state directly) routes through
  // the same "select" handler a click uses, so there's one source of
  // truth for what "selected" means.
  useEffect(() => {
    if (!isFull || !graph || !searchQuery) return;
    const cy = cyRef.current;
    if (!cy) return;
    const match = graph.nodes.find((n) => n.label.toLowerCase().includes(searchQuery));
    if (!match) return;
    const ele = cy.$id(match.id);
    if (ele.empty()) return;
    cy.elements().unselect();
    ele.select();
    cy.animate({ center: { eles: ele }, zoom: Math.max(cy.zoom(), 1.15) }, { duration: 260 });
  }, [searchQuery, isFull, graph]);

  function zoomBy(factor: number) {
    const cy = cyRef.current;
    if (!cy) return;
    cy.animate({ zoom: cy.zoom() * factor, center: { eles: cy.elements() } }, { duration: 150 });
  }
  function resetView() {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().unselect();
    setSelected(null);
    setHover(null);
    focusNeighborhood(null);
    cy.animate({ fit: { eles: cy.elements(), padding: isFull ? 56 : 20 } }, { duration: 200 });
  }

  if (!graph) {
    return (
      <div
        className={`flex items-center justify-center rounded-[var(--radius-panel)] border px-4 text-center text-sm ${
          isFull ? "h-full" : "h-32"
        }`}
        style={{ borderColor: "var(--border)", color: "var(--muted)" }}
      >
        No fraud ring detected for this transaction — no shared devices, IPs, or connected accounts
        were found.
      </div>
    );
  }

  return (
    <div className={isFull ? "flex h-full flex-col gap-3" : "flex flex-col gap-3"}>
      {isFull && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by masked identifier…"
            aria-label="Search graph entities"
            className="w-56 rounded-[var(--radius-control)] border px-3 py-1.5 text-xs outline-none"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", color: "var(--foreground)" }}
          />
          {searchMiss && (
            <span className="text-[11px]" style={{ color: "var(--muted)" }}>
              No match.
            </span>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            <GraphControlButton label="Zoom out" onClick={() => zoomBy(0.8)}>
              −
            </GraphControlButton>
            <GraphControlButton label="Zoom in" onClick={() => zoomBy(1.25)}>
              +
            </GraphControlButton>
            <GraphControlButton label="Reset view" onClick={resetView}>
              Reset
            </GraphControlButton>
          </div>
        </div>
      )}

      <div className={isFull ? "flex min-h-0 flex-1 gap-3" : "flex flex-col gap-3 sm:flex-row"}>
        <div className="relative min-w-0 flex-1">
          <div
            ref={containerRef}
            className={
              (isFull ? "h-full" : "h-72") +
              " w-full rounded-[var(--radius-panel)] border"
            }
            style={{
              borderColor: "var(--border)",
              background:
                "radial-gradient(600px 400px at 30% 20%, rgba(22,163,106,0.07), transparent 65%), var(--canvas)",
            }}
          />
          {hover && (
            <div
              className="pointer-events-none fixed z-30 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-[var(--radius-control)] border px-3 py-2 text-xs backdrop-blur-xl"
              style={{
                left: hover.x,
                top: hover.y,
                borderColor: "var(--border)",
                backgroundColor: "var(--panel-solid)",
                boxShadow: "var(--shadow-panel-raised)",
                minWidth: 160,
              }}
            >
              <div className="mb-1 flex items-center gap-1.5 font-semibold" style={{ color: "var(--foreground)" }}>
                <span aria-hidden="true">{NODE_TYPE_SHAPE_GLYPH[hover.node.node_type]}</span>
                {NODE_TYPE_LABEL[hover.node.node_type] ?? hover.node.node_type}
              </div>
              <div className="font-mono" style={{ color: "var(--muted)" }}>
                <MaskedId value={hover.node.label} />
              </div>
              <div className="mt-1" style={{ color: "var(--muted)" }}>
                {transactionCountFor(hover.node.id, graph)} txn · {hover.node.is_suspicious ? "Flagged" : "Normal"}
              </div>
            </div>
          )}
          <GraphLegend />
        </div>

        <div
          className={
            (isFull ? "w-72 shrink-0 overflow-y-auto" : "w-full shrink-0 sm:w-56") +
            " rounded-[var(--radius-panel)] border p-3 text-xs"
          }
          style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
        >
          {selected ? (
            <dl className="flex flex-col gap-2.5">
              <div
                className="mb-1 text-[11px] font-semibold uppercase tracking-wider"
                style={{ color: "var(--amber)" }}
              >
                {NODE_TYPE_LABEL[selected.node_type] ?? selected.node_type}
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Identifier</dt>
                <dd className="font-mono">
                  <MaskedId value={selected.label} />
                </dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Connected entities</dt>
                <dd className="font-mono">{connectedCountFor(selected.id, graph)}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Transactions</dt>
                <dd className="font-mono">{transactionCountFor(selected.id, graph)}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--muted)" }}>Flagged</dt>
                <dd className="font-mono" style={{ color: selected.is_suspicious ? "var(--risk-high)" : "var(--foreground)" }}>
                  {selected.is_suspicious ? "Yes" : "No"}
                </dd>
              </div>
              {graph.ring_id && (
                <div>
                  <dt style={{ color: "var(--muted)" }}>Ring</dt>
                  <dd className="font-mono">{graph.ring_id}</dd>
                </div>
              )}
            </dl>
          ) : (
            <p style={{ color: "var(--muted)" }}>
              {isFull ? "Click a node to inspect it. Hover to preview its connections." : "Click a node to see its details."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/** Header-row affordance for a compact graph's Panel ("Open Full View" →
 * the dedicated /network/explore workspace) — a plain Link, not a modal,
 * so it's a real route change. Exported so /case and /network can drop
 * it into their Panel's headerRight without duplicating the markup. */
export function OpenFullViewLink({ href }: { href: string }) {
  return (
    <Link
      href={href}
      className="hoverable-panel flex shrink-0 items-center gap-1.5 rounded-[var(--radius-control)] border px-2 py-1 text-[11px] font-semibold transition-colors"
      style={{ borderColor: "var(--border)", color: "var(--cobalt)" }}
      aria-label="Open the full-screen fraud network explorer"
    >
      <ExpandIcon />
      Open Full View
    </Link>
  );
}

function GraphControlButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="hoverable-panel flex h-7 min-w-7 cursor-pointer items-center justify-center rounded-[var(--radius-control)] border px-2 text-xs font-semibold transition-colors"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)", color: "var(--foreground)" }}
    >
      {children}
    </button>
  );
}

function ExpandIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
    </svg>
  );
}

function GraphLegend() {
  return (
    <div
      className="pointer-events-none absolute bottom-2 left-2 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[var(--radius-control)] border px-2.5 py-1.5 text-[10px] backdrop-blur-xl"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--panel-solid)", color: "var(--muted)" }}
    >
      {NODE_TYPE_ORDER.map((t) => (
        <span key={t} className="flex items-center gap-1">
          <span aria-hidden="true">{NODE_TYPE_SHAPE_GLYPH[t]}</span>
          {NODE_TYPE_LABEL[t]}
        </span>
      ))}
      <span className="flex items-center gap-1" style={{ color: "var(--risk-high)" }}>
        <span aria-hidden="true">◉</span>
        Flagged
      </span>
    </div>
  );
}
