"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { type Core, type EdgeSingular, type NodeSingular } from "cytoscape";
import type { CaseGraph, GraphNodePublic } from "@/lib/types";

/** Cytoscape draws to canvas, not the DOM, so it can't resolve CSS
 * custom properties itself — read the real computed values once so the
 * graph stays on the same design tokens as the rest of the app instead
 * of a second, hardcoded color language. */
function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const get = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;
  return {
    cobalt: get("--cobalt", "#3538cd"),
    cobaltForeground: get("--cobalt-foreground", "#ffffff"),
    graphite: get("--graphite", "#1c2030"),
    graphiteForeground: get("--graphite-foreground", "#b7bdd0"),
    muted: get("--muted", "#626a80"),
    border: get("--border", "#dfe2ec"),
    foreground: get("--foreground", "#171b2c"),
    panel: get("--panel", "#ffffff"),
    riskHigh: get("--risk-high", "#c23b22"),
    riskCritical: get("--risk-critical", "#9c1c1c"),
    font: get("--font-mono", "monospace"),
  };
}

const NODE_TYPE_LABEL: Record<string, string> = {
  account: "Account",
  device: "Device",
  ip: "IP Address",
  merchant: "Merchant",
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

export default function FraudRingGraph({ graph }: { graph: CaseGraph | null }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selected, setSelected] = useState<GraphNodePublic | null>(null);

  useEffect(() => {
    if (!graph) return;

    function build() {
      const container = containerRef.current;
      if (!container || !graph) return;
      const tokens = readTokens();

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
        ip: tokens.panel,
        merchant: tokens.foreground,
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
              "font-size": 9,
              "font-family": tokens.font,
              color: (ele: NodeSingular) => textByType[ele.data("node_type") as string] ?? tokens.foreground,
              "text-valign": "center",
              "text-halign": "center",
              "text-wrap": "wrap",
              "text-max-width": "70px",
              shape: (ele: NodeSingular) => shapeByType[ele.data("node_type") as string] ?? "ellipse",
              "background-color": (ele: NodeSingular) => fillByType[ele.data("node_type") as string] ?? tokens.muted,
              width: (ele: NodeSingular) => (ele.data("flagged") ? 60 : 42),
              height: (ele: NodeSingular) => (ele.data("flagged") ? 60 : 42),
              "border-width": (ele: NodeSingular) =>
                ele.data("flagged") ? 4 : ele.data("is_suspicious") ? 3 : 1,
              "border-color": (ele: NodeSingular) =>
                ele.data("flagged")
                  ? tokens.riskCritical
                  : ele.data("is_suspicious")
                    ? tokens.riskHigh
                    : tokens.border,
            },
          },
          {
            selector: "edge",
            style: {
              width: (ele: EdgeSingular) => 1 + Math.min(ele.data("weight") as number, 6),
              "line-color": tokens.border,
              "curve-style": "bezier",
              "target-arrow-shape": "none",
              opacity: 0.8,
            },
          },
          {
            selector: "node:selected",
            style: { "border-color": tokens.cobalt, "border-width": 4 },
          },
        ],
        layout: { name: "cose", animate: false, padding: 24 },
        userZoomingEnabled: true,
        userPanningEnabled: true,
        boxSelectionEnabled: false,
      });

      cy.on("tap", "node", (evt) => {
        const id = evt.target.id();
        setSelected(graph.nodes.find((n) => n.id === id) ?? null);
      });
      cy.on("tap", (evt) => {
        if (evt.target === cy) setSelected(null);
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

    return () => {
      media.removeEventListener("change", onThemeChange);
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [graph]);

  if (!graph) {
    return (
      <div
        className="flex h-32 items-center justify-center rounded-[var(--radius-panel)] border px-4 text-center text-sm"
        style={{ borderColor: "var(--border)", color: "var(--muted)" }}
      >
        No fraud ring detected for this transaction — no shared devices, IPs, or connected accounts
        were found.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <div
        ref={containerRef}
        className="h-72 flex-1 rounded-[var(--radius-panel)] border"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--canvas)" }}
      />
      <div
        className="w-full shrink-0 rounded-[var(--radius-panel)] border p-3 text-xs sm:w-56"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--panel)" }}
      >
        {selected ? (
          <dl className="flex flex-col gap-2.5">
            <div>
              <dt style={{ color: "var(--muted)" }}>Type</dt>
              <dd className="font-medium">{NODE_TYPE_LABEL[selected.node_type] ?? selected.node_type}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Identifier</dt>
              <dd className="font-mono">{selected.label}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Transactions</dt>
              <dd className="font-mono">{transactionCountFor(selected.id, graph)}</dd>
            </div>
            <div>
              <dt style={{ color: "var(--muted)" }}>Flagged</dt>
              <dd className="font-mono">{selected.is_suspicious ? "Yes" : "No"}</dd>
            </div>
          </dl>
        ) : (
          <p style={{ color: "var(--muted)" }}>Click a node to see its details.</p>
        )}
      </div>
    </div>
  );
}
