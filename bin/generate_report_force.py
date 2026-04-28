#!/usr/bin/env python3
"""
Lumos Report Generator
Generates a self-contained HTML report with an interactive knowledge graph
visualization using force-graph (canvas-based, loaded via CDN).
"""

import argparse
import json
import os
import sys


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lumos — Project Knowledge Graph</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/force-graph@1.47.3/dist/force-graph.min.js"></script>
<style>
/* Theme variables */
:root, [data-theme="dark"] {
  --bg-page: #0d1117; --bg-header: #0d1117; --bg-sidebar: #161b22; --bg-card: #21262d;
  --border: #30363d; --border-hover: #484f58;
  --text-primary: #f0f6fc; --text-secondary: #c9d1d9; --text-muted: #8b949e; --text-dim: #484f58;
  --accent: #f5c542;
  --legend-bg: rgba(22,27,34,0.97);
  --graph-bg: #0d1117;
  --filter-bg: rgba(255,255,255,0.05);
}
[data-theme="light"] {
  --bg-page: #ffffff; --bg-header: #f6f8fa; --bg-sidebar: #f6f8fa; --bg-card: #e8ecf0;
  --border: #d0d7de; --border-hover: #8b949e;
  --text-primary: #1f2328; --text-secondary: #424a53; --text-muted: #656d76; --text-dim: #8b949e;
  --accent: #c8910d;
  --legend-bg: rgba(246,248,250,0.97);
  --graph-bg: #ffffff;
  --filter-bg: rgba(0,0,0,0.04);
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg-page); color: var(--text-secondary); overflow: hidden; }

/* Header */
#header { position: fixed; top: 0; left: 0; right: 0; z-index: 1000; padding: 12px 20px; background: var(--bg-header); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }

#app { position: relative; height: calc(100vh - 50px); margin-top: 50px; }
#graph-container { width: 100%; height: 100%; position: relative; }
#sidebar { position: fixed; right: 0; top: 50px; bottom: 0; width: 340px; background: var(--bg-sidebar); border-left: 1px solid var(--border); overflow-y: auto; display: flex; flex-direction: column; z-index: 500; transition: transform 0.2s; }
#sidebar.collapsed { transform: translateX(100%); }
#sidebar-toggle { position: fixed; top: 55px; z-index: 501; padding: 6px 8px; background: var(--bg-card); border: 1px solid var(--border); border-right: none; border-radius: 6px 0 0 6px; cursor: pointer; color: var(--text-muted); font-size: 12px; }
#header h1 { font-size: 28px; font-weight: 600; color: #e0e6ed; letter-spacing: -0.02em; text-transform: lowercase; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; line-height: 1; display: flex; align-items: center; }
#header h1 .hl { color: #e8ecf0; text-shadow: 0 0 8px rgba(232,236,240,0.6), 0 0 20px rgba(232,236,240,0.3); }
[data-theme="light"] #header h1 { color: rgba(31,35,40,0.55); }
[data-theme="light"] #header h1 .hl { color: #1f2328; text-shadow: 0 0 8px rgba(31,35,40,0.25), 0 0 20px rgba(31,35,40,0.1); }
#search { padding: 8px 12px; background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px; color: var(--text-secondary); font-size: 14px; width: 240px; outline: none; }
#search:focus { border-color: var(--accent); }
#theme-btn { padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-muted); font-size: 14px; cursor: pointer; line-height: 1; }

/* Filters */
#filters { display: flex; gap: 8px; flex-wrap: wrap; }
.filter-btn { padding: 4px 12px; border-radius: 12px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-muted); font-size: 12px; cursor: pointer; transition: all 0.2s; }
.filter-btn.active { border-color: var(--color); color: var(--color); background: var(--filter-bg); }
.filter-btn:hover { border-color: var(--text-muted); }

/* Sidebar */
#sidebar-header { padding: 16px; border-bottom: 1px solid var(--border); }
#sidebar-header h2 { font-size: 16px; color: var(--text-primary); margin-bottom: 4px; }
#sidebar-header .subtitle { font-size: 12px; color: var(--text-muted); }

#detail-panel { padding: 16px; flex: 1; }
#detail-panel .empty { color: var(--text-dim); font-style: italic; margin-top: 40px; text-align: center; }
.detail-section { margin-bottom: 16px; }
.detail-section h3 { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.detail-section .value { font-size: 14px; color: var(--text-secondary); line-height: 1.5; }
.detail-section .tag { display: inline-block; padding: 2px 8px; background: var(--bg-card); border-radius: 4px; font-size: 11px; margin: 2px; color: var(--text-muted); }

.connection-item { padding: 8px; margin: 4px 0; background: var(--bg-card); border-radius: 6px; cursor: pointer; transition: background 0.2s; }
.connection-item:hover { background: var(--border); }
.connection-item .conn-type { font-size: 11px; color: var(--text-muted); }
.connection-item .conn-name { font-size: 13px; color: var(--text-secondary); }

#stats-bar { padding: 12px 16px; border-top: 1px solid var(--border); background: var(--bg-page); display: flex; gap: 16px; flex-wrap: wrap; }
.stat { font-size: 12px; color: var(--text-muted); }
.stat .num { color: var(--accent); font-weight: 600; }

/* Legend */
#legend { position: fixed; top: 62px; left: 16px; background: var(--legend-bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; z-index: 1000; }
#legend h4 { font-size: 11px; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; }
.legend-item { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 12px; color: var(--text-muted); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }
</style>
</head>
<body>
<div id="header">
  <h1>lu<span class="hl">m</span>os</h1>
  <div style="display:flex;gap:2px;background:var(--bg-card);border-radius:8px;padding:2px;">
    <a href="report-cards.html" style="padding:5px 14px;border-radius:6px;background:transparent;color:var(--text-muted);font-size:12px;text-decoration:none;cursor:pointer;font-weight:500;">Hierarchy</a>
    <a href="report-cards.html#notebook" style="padding:5px 14px;border-radius:6px;background:transparent;color:var(--text-muted);font-size:12px;text-decoration:none;cursor:pointer;font-weight:500;">Notebook</a>
    <span style="padding:5px 14px;border-radius:6px;background:var(--accent);color:var(--bg-page);font-size:12px;font-weight:600;">Force</span>
  </div>
  <select id="nb-filter" style="padding:6px 10px;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;color:var(--text-secondary);font-size:12px;outline:none;"></select>
  <input id="search" type="text" placeholder="Search nodes...">
  <div id="filters">
    <button class="filter-btn active" data-filter="all" style="--color:var(--accent)">All</button>
    <button class="filter-btn active" data-filter="code" style="--color:#58a6ff">Code</button>
    <button class="filter-btn active" data-filter="notebook" style="--color:#3fb950">Notebooks</button>
    <button class="filter-btn active" data-filter="doc" style="--color:#d29922">Docs</button>
    <button class="filter-btn active" data-filter="cross" style="--color:#f85149">Cross-boundary</button>
  </div>
  <button id="theme-btn" onclick="toggleTheme()" title="Toggle light/dark theme">&#9789;</button>
</div>
<div id="legend">
  <h4>Node Types</h4>
  <div class="legend-item"><div class="legend-dot" style="background:#58a6ff"></div> Code (file/function/class)</div>
  <div class="legend-item"><div class="legend-dot" style="background:#3fb950"></div> Notebook / Cell</div>
  <div class="legend-item"><div class="legend-dot" style="background:#d29922"></div> Document / Section</div>
  <div class="legend-item"><div class="legend-dot" style="background:#bc8cff"></div> Metric Definition</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f85149"></div> Error Cell</div>
  <h4 style="margin-top:8px">Edge Types</h4>
  <div class="legend-item"><div style="width:24px;height:2px;background:#3fb950;border-radius:1px"></div> Data flow (var dependency, hover for name)</div>
  <div class="legend-item"><div style="width:24px;height:2px;background:#f85149;border-radius:1px;border-top:2px dashed #f85149;height:0"></div> Cross-boundary (notebook→code)</div>
  <div class="legend-item"><div style="width:24px;height:2px;background:#a371f7;border-radius:1px"></div> Py4J bridge (Python→Scala/JVM)</div>
  <div class="legend-item"><div style="width:24px;height:0;border-top:1px dashed #484f58"></div> Cell sequence (document order)</div>
  <div class="legend-item"><div style="width:24px;height:2px;background:#d29922;border-radius:1px"></div> Doc reference</div>
  <div class="legend-item"><div style="width:24px;height:1px;background:#4a6a8a"></div> Contains / Imports</div>
</div>
<div id="app">
  <div id="graph-container">
  </div>
  <button id="sidebar-toggle" onclick="toggleSidebar()">&#9654;</button>
  <div id="sidebar">
    <div id="sidebar-header">
      <h2 id="project-name">Project</h2>
      <div class="subtitle" id="project-info"></div>
    </div>
    <div id="detail-panel">
      <div class="empty">Click a node to see details</div>
    </div>
    <div id="stats-bar"></div>
  </div>
</div>

<script>
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const btn = document.getElementById('sidebar-toggle');
  sb.classList.toggle('collapsed');
  const collapsed = sb.classList.contains('collapsed');
  btn.textContent = collapsed ? '\u25C0' : '\u25B6';
  btn.style.right = collapsed ? '0px' : '340px';
}
// Set initial toggle position
document.getElementById('sidebar-toggle').style.right = '340px';
// --- Embedded graph data ---
// --- Theme toggle ---
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  document.getElementById('theme-btn').textContent = next === 'dark' ? '\u263D' : '\u2600';
  // Update graph background
  if (typeof graph !== 'undefined') {
    graph.backgroundColor(getComputedStyle(html).getPropertyValue('--bg-page').trim());
  }
  localStorage.setItem('lumos-theme', next);
}
// Restore saved theme
(function() {
  const saved = localStorage.getItem('lumos-theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
    document.getElementById('theme-btn').textContent = saved === 'dark' ? '\u263D' : '\u2600';
  }
})();

const GRAPH_DATA = __GRAPH_JSON__;

// --- Color scheme ---
const NODE_COLORS = {
  file: '#58a6ff',
  function: '#79c0ff',
  class: '#a5d6ff',
  module: '#388bfd',
  notebook: '#3fb950',
  cell: '#56d364',
  document: '#d29922',
  doc_section: '#e3b341',
  metric_def: '#bc8cff',
  config: '#8b949e',
  data_source: '#f78166',
  feature_def: '#ffa657',
};

const NODE_SIZES = {
  file: 6,
  function: 4,
  class: 6,
  module: 8,
  notebook: 8,
  cell: 3,
  document: 7,
  doc_section: 4,
  metric_def: 5,
};

const EDGE_COLORS = {
  cross_boundary_import: '#f85149',
  cross_boundary_call: '#ff7b72',
  cross_boundary_method_call: '#ffa198',
  cross_boundary_instantiate: '#ff7b72',
  py4j_bridge: '#a371f7',
  py4j_method_call: '#bc8cff',
  doc_references_code: '#d29922',
  doc_references_notebook: '#e3b341',
  metric_implemented_by: '#bc8cff',
  contains: '#4a6a8a',
  cell_flow: '#3a5a7a',
  cell_data_flow: '#2ea043',
  imports: '#4a6a8a',
  inherits: '#6a8aaa',
  defines_metric: '#bc8cff',
};

const CROSS_BOUNDARY_TYPES = new Set([
  'cross_boundary_import', 'cross_boundary_call',
  'cross_boundary_method_call', 'cross_boundary_instantiate',
]);
const DOC_EDGE_TYPES = new Set([
  'doc_references_code', 'doc_references_notebook', 'metric_implemented_by', 'defines_metric',
]);
const CODE_TYPES = new Set(['file', 'function', 'class', 'module']);
const NOTEBOOK_TYPES = new Set(['notebook', 'cell']);
const DOC_TYPES = new Set(['document', 'doc_section', 'metric_def']);

// --- Transform graph data for force-graph ---
function transformData(graphData) {
  const nodes = graphData.nodes.map(n => ({
    id: n.id,
    name: n.name || n.id,
    type: n.type,
    color: n.status === 'error' ? '#f85149' : (NODE_COLORS[n.type] || '#8b949e'),
    size: NODE_SIZES[n.type] || 4,
    data: n,
  }));

  const nodeIds = new Set(nodes.map(n => n.id));
  const links = graphData.edges
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map(e => ({
      source: e.source,
      target: e.target,
      type: e.type,
      color: EDGE_COLORS[e.type] || '#21262d',
      width: CROSS_BOUNDARY_TYPES.has(e.type) ? 2 : (DOC_EDGE_TYPES.has(e.type) ? 1.5 : 0.5),
      data: e,
    }));

  return { nodes, links };
}

// --- State ---
let activeFilters = { code: true, notebook: true, doc: true, cross: true };
let searchQuery = '';
let selectedNode = null;
let selectedLink = null;
let highlightedNodeIds = new Set();
let selectedNotebookFile = ''; // empty = show all

// --- Notebook filter setup ---
const allNotebooks = GRAPH_DATA.nodes.filter(n => n.type === 'notebook').sort((a,b) => (a.file||'').localeCompare(b.file||''));
const nbFilterEl = document.getElementById('nb-filter');
nbFilterEl.innerHTML = '<option value="">All notebooks</option>' + allNotebooks.map(n => '<option value="'+n.file+'">'+n.file+'</option>').join('');

// Cached notebook scope — recomputed only on dropdown change
let cachedScope = null;

function computeNotebookScope(nbFile) {
  if (!nbFile) return null;
  const nbNode = GRAPH_DATA.nodes.find(n => n.type === 'notebook' && n.file === nbFile);
  if (!nbNode) return null;
  const cellIds = new Set();
  const crossTargetIds = new Set();
  const docNodeIds = new Set();
  const parentFileIds = new Set();
  GRAPH_DATA.edges.forEach(e => { if (e.source === nbNode.id && e.type === 'contains') cellIds.add(e.target); });
  GRAPH_DATA.edges.forEach(e => { if (CROSS_BOUNDARY_TYPES.has(e.type) && cellIds.has(e.source)) crossTargetIds.add(e.target); });
  GRAPH_DATA.edges.forEach(e => { if (DOC_EDGE_TYPES.has(e.type) && crossTargetIds.has(e.target)) docNodeIds.add(e.source); });
  GRAPH_DATA.edges.forEach(e => { if (e.type === 'contains' && crossTargetIds.has(e.target)) parentFileIds.add(e.source); });
  return new Set([nbNode.id, ...cellIds, ...crossTargetIds, ...docNodeIds, ...parentFileIds]);
}

nbFilterEl.addEventListener('change', function() {
  selectedNotebookFile = this.value;
  cachedScope = computeNotebookScope(selectedNotebookFile);
  graph.nodeColor(graph.nodeColor());
  graph.linkColor(graph.linkColor());
});

// --- Filtering ---
function isNodeVisible(node) {
  if (searchQuery && !node.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !node.id.toLowerCase().includes(searchQuery.toLowerCase())) {
    return false;
  }
  // Notebook scope filter (uses cached scope)
  if (cachedScope && !cachedScope.has(node.id)) return false;
  if (!activeFilters.code && CODE_TYPES.has(node.type)) return false;
  if (!activeFilters.notebook && NOTEBOOK_TYPES.has(node.type)) return false;
  if (!activeFilters.doc && DOC_TYPES.has(node.type)) return false;
  return true;
}

function isLinkVisible(link) {
  if (!activeFilters.cross && CROSS_BOUNDARY_TYPES.has(link.type)) return false;
  const sourceNode = typeof link.source === 'object' ? link.source : null;
  const targetNode = typeof link.target === 'object' ? link.target : null;
  if (sourceNode && !isNodeVisible(sourceNode)) return false;
  if (targetNode && !isNodeVisible(targetNode)) return false;
  return true;
}

// --- Detail panel ---
function showNodeDetail(node) {
  selectedNode = node;
  const panel = document.getElementById('detail-panel');
  const d = node.data;

  const connections = GRAPH_DATA.edges.filter(e => e.source === node.id || e.target === node.id);
  const incoming = connections.filter(e => e.target === node.id);
  const outgoing = connections.filter(e => e.source === node.id);

  let html = '';

  // Name & type
  html += '<div class="detail-section"><h3>Node</h3>';
  html += '<div class="value"><strong>' + escHtml(d.name) + '</strong></div>';
  html += '<div class="value"><span class="tag">' + d.type + '</span>';
  if (d.language) html += '<span class="tag">' + d.language + '</span>';
  if (d.doc_type) html += '<span class="tag">' + d.doc_type + '</span>';
  if (d.status) html += '<span class="tag">' + d.status + '</span>';
  if (d.complexity) html += '<span class="tag">' + d.complexity + '</span>';
  html += '</div></div>';

  // File info
  if (d.file) {
    html += '<div class="detail-section"><h3>Location</h3>';
    html += '<div class="value">' + escHtml(d.file);
    if (d.line_start) html += ':' + d.line_start + '-' + d.line_end;
    html += '</div></div>';
  }

  // Summary
  if (d.summary) {
    html += '<div class="detail-section"><h3>Summary</h3>';
    html += '<div class="value">' + escHtml(d.summary) + '</div></div>';
  }

  // Cell-specific info
  if (d.type === 'cell' && d.cell_type === 'code') {
    if (d.defs && d.defs.length) {
      html += '<div class="detail-section"><h3>Defines</h3>';
      html += '<div class="value">' + d.defs.map(x => '<span class="tag">' + escHtml(x) + '</span>').join('') + '</div></div>';
    }
    if (d.imports && d.imports.length) {
      html += '<div class="detail-section"><h3>Imports</h3>';
      html += '<div class="value">' + d.imports.map(x => '<span class="tag">' + escHtml(x.module + '.' + x.name) + '</span>').join('') + '</div></div>';
    }
    if (d.magics && d.magics.length) {
      html += '<div class="detail-section"><h3>Magics</h3>';
      html += '<div class="value">' + d.magics.map(x => '<span class="tag">' + escHtml(x.name) + '</span>').join('') + '</div></div>';
    }
    if (d.error) {
      html += '<div class="detail-section"><h3>Error</h3>';
      html += '<div class="value" style="color:#f85149">' + escHtml(d.error.error_name + ': ' + d.error.error_value) + '</div></div>';
    }
  }

  // Source preview
  if (d.source_preview) {
    html += '<div class="detail-section"><h3>Source</h3>';
    html += '<div class="value"><pre style="font-size:11px;overflow-x:auto;white-space:pre-wrap;color:#8b949e">' + escHtml(d.source_preview) + '</pre></div></div>';
  }
  if (d.body_preview) {
    html += '<div class="detail-section"><h3>Content</h3>';
    html += '<div class="value"><pre style="font-size:11px;overflow-x:auto;white-space:pre-wrap;color:#8b949e">' + escHtml(d.body_preview) + '</pre></div></div>';
  }

  // Function args
  if (d.args && d.args.length) {
    html += '<div class="detail-section"><h3>Arguments</h3>';
    html += '<div class="value">' + d.args.map(x => '<span class="tag">' + escHtml(x) + '</span>').join('') + '</div></div>';
  }

  // Methods (for classes)
  if (d.methods && d.methods.length) {
    html += '<div class="detail-section"><h3>Methods</h3>';
    html += '<div class="value">' + d.methods.map(x => '<span class="tag">' + escHtml(x) + '</span>').join('') + '</div></div>';
  }

  // Connections
  if (incoming.length) {
    html += '<div class="detail-section"><h3>Incoming (' + incoming.length + ')</h3>';
    incoming.forEach(e => {
      const srcNode = GRAPH_DATA.nodes.find(n => n.id === e.source);
      html += '<div class="connection-item" onclick="focusNode(\'' + escAttr(e.source) + '\')">';
      html += '<div class="conn-type">' + e.type + '</div>';
      html += '<div class="conn-name">' + escHtml(srcNode ? srcNode.name : e.source) + '</div>';
      html += '</div>';
    });
    html += '</div>';
  }

  if (outgoing.length) {
    html += '<div class="detail-section"><h3>Outgoing (' + outgoing.length + ')</h3>';
    outgoing.forEach(e => {
      const tgtNode = GRAPH_DATA.nodes.find(n => n.id === e.target);
      html += '<div class="connection-item" onclick="focusNode(\'' + escAttr(e.target) + '\')">';
      html += '<div class="conn-type">' + e.type + '</div>';
      html += '<div class="conn-name">' + escHtml(tgtNode ? tgtNode.name : e.target) + '</div>';
      html += '</div>';
    });
    html += '</div>';
  }

  panel.innerHTML = html;
}

function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { return String(s).replace(/'/g, "\\'").replace(/"/g, '\\"'); }

function focusNode(nodeId) {
  const node = graphData.nodes.find(n => n.id === nodeId);
  if (node) {
    graph.centerAt(node.x, node.y, 500);
    graph.zoom(3, 500);
    showNodeDetail(node);
  }
}

// --- Initialize ---
const graphData = transformData(GRAPH_DATA);

const graph = new ForceGraph(document.getElementById('graph-container'))
  .backgroundColor(getComputedStyle(document.documentElement).getPropertyValue('--bg-page').trim())
  .graphData(graphData)
  .nodeColor(n => isNodeVisible(n) ? n.color : 'transparent')
  .nodeVal(n => isNodeVisible(n) ? n.size : 0)
  .nodeLabel(n => isNodeVisible(n) ? n.name : '')
  .nodeCanvasObject((node, ctx, globalScale) => {
    if (!isNodeVisible(node)) return;
    const size = node.size;
    const fontSize = Math.max(10 / globalScale, 1.5);
    const isSelected = node === selectedNode;
    const isHighlighted = highlightedNodeIds.has(node.id);
    const d = node.data;

    // Draw highlight ring for edge-selected nodes
    if (isHighlighted) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
      ctx.strokeStyle = '#f5c542';
      ctx.lineWidth = 2.5;
      ctx.stroke();
      // Glow effect
      ctx.shadowColor = '#f5c542';
      ctx.shadowBlur = 12;
    }

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = isSelected ? '#f5c542' : (isHighlighted ? '#f5c542' : node.color);
    ctx.fill();
    ctx.shadowBlur = 0;

    // For cells: draw cell index number inside the node
    if (d.type === 'cell' && d.cell_index != null) {
      ctx.font = 'bold ' + Math.max(size * 1.2, 3) + 'px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#0d1117';
      ctx.fillText(d.cell_index, node.x, node.y);
    }

    // Draw label if zoomed in enough
    if (globalScale > 1.2) {
      ctx.font = fontSize + 'px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#8b949e';
      ctx.fillText(node.name, node.x, node.y + size + 2);
    }
  })
  .linkColor(l => {
    if (!isLinkVisible(l)) return 'transparent';
    if (l === selectedLink) return '#f5c542';
    if (l.type === 'cell_data_flow') return '#3fb950';
    if (l.type === 'cell_flow') return '#30363d';
    return l.color;
  })
  .linkWidth(l => {
    if (!isLinkVisible(l)) return 0;
    if (l === selectedLink) return 4;
    if (l.type === 'cell_data_flow') return 2.5;
    if (l.type === 'cell_flow') return 0.5;
    return l.width;
  })
  .linkDirectionalParticles(0)
  .linkDirectionalArrowLength(l => !isLinkVisible(l) ? 0 : ((l.type === 'cell_data_flow' || CROSS_BOUNDARY_TYPES.has(l.type)) ? 6 : 0))
  .linkDirectionalArrowRelPos(1)
  .linkDirectionalArrowColor(l => !isLinkVisible(l) ? 'transparent' : (l.type === 'cell_data_flow' ? '#3fb950' : l.color))
  .linkLineDash(l => CROSS_BOUNDARY_TYPES.has(l.type) ? [4, 2] : (l.type === 'cell_flow' ? [2, 3] : null))
  .linkLabel(l => {
    if (l.type === 'cell_data_flow' && l.data && l.data.detail) return l.data.detail.variable || '';
    if (CROSS_BOUNDARY_TYPES.has(l.type) && l.data && l.data.detail) return l.data.detail.name || l.data.detail.call || '';
    return '';
  })
  .onLinkClick(link => {
    if (!isLinkVisible(link)) return;
    selectedLink = link;
    selectedNode = null;
    const srcId = typeof link.source === 'object' ? link.source.id : link.source;
    const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
    highlightedNodeIds = new Set([srcId, tgtId]);
    // Show edge details in sidebar
    const srcNode = GRAPH_DATA.nodes.find(n => n.id === srcId);
    const tgtNode = GRAPH_DATA.nodes.find(n => n.id === tgtId);
    let html = '<div class="detail-section"><h3>Edge</h3>';
    html += '<div class="value"><span class="tag">' + link.type.replace(/_/g, ' ') + '</span></div></div>';
    html += '<div class="detail-section"><h3>Source</h3>';
    html += '<div class="value" style="cursor:pointer;color:#f5c542" onclick="graph.onNodeClick()(' + JSON.stringify(link.source) + ')">' + escHtml(srcNode ? srcNode.name : srcId) + '</div>';
    html += '<div class="value"><span class="tag">' + (srcNode ? srcNode.type : '') + '</span></div></div>';
    html += '<div class="detail-section"><h3>Target</h3>';
    html += '<div class="value" style="cursor:pointer;color:#f5c542" onclick="graph.onNodeClick()(' + JSON.stringify(link.target) + ')">' + escHtml(tgtNode ? tgtNode.name : tgtId) + '</div>';
    html += '<div class="value"><span class="tag">' + (tgtNode ? tgtNode.type : '') + '</span></div></div>';
    if (link.data && link.data.detail) {
      html += '<div class="detail-section"><h3>Detail</h3><div class="value">';
      Object.entries(link.data.detail).forEach(([k,v]) => { html += '<span class="tag">' + k + ': ' + escHtml(v) + '</span>'; });
      html += '</div></div>';
    }
    document.getElementById('detail-panel').innerHTML = html;
    // Trigger re-render to show highlights
    graph.nodeColor(graph.nodeColor());
    graph.linkColor(graph.linkColor());
    graph.linkWidth(graph.linkWidth());
  })
  .onNodeClick(node => {
    if (!isNodeVisible(node)) return;
    selectedLink = null;
    highlightedNodeIds = new Set();
    showNodeDetail(node);
    graph.nodeColor(graph.nodeColor());
    graph.linkColor(graph.linkColor());
    graph.linkWidth(graph.linkWidth());
  })
  .onBackgroundClick(() => {
    selectedNode = null;
    selectedLink = null;
    highlightedNodeIds = new Set();
    document.getElementById('detail-panel').innerHTML = '<div class="empty">Click a node to see details</div>';
    graph.nodeColor(graph.nodeColor());
    graph.linkColor(graph.linkColor());
    graph.linkWidth(graph.linkWidth());
  })
  .d3AlphaDecay(0.02)
  .d3VelocityDecay(0.3)
  .warmupTicks(50)
  .cooldownTicks(100);

// --- Search ---
document.getElementById('search').addEventListener('input', e => {
  searchQuery = e.target.value;
  graph.nodeColor(graph.nodeColor()); // force re-render
  graph.linkColor(graph.linkColor());
});

// --- Filters ---
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const filter = btn.dataset.filter;
    if (filter === 'all') {
      const allActive = Object.values(activeFilters).every(v => v);
      Object.keys(activeFilters).forEach(k => activeFilters[k] = !allActive);
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', !allActive));
    } else {
      activeFilters[filter] = !activeFilters[filter];
      btn.classList.toggle('active');
      // Update "all" button
      const allBtn = document.querySelector('[data-filter="all"]');
      allBtn.classList.toggle('active', Object.values(activeFilters).every(v => v));
    }
    graph.nodeColor(graph.nodeColor());
    graph.linkColor(graph.linkColor());
  });
});

// --- Stats ---
const stats = GRAPH_DATA.stats;
document.getElementById('stats-bar').innerHTML =
  '<div class="stat"><span class="num">' + stats.total_nodes + '</span> nodes</div>' +
  '<div class="stat"><span class="num">' + stats.total_edges + '</span> edges</div>' +
  Object.entries(stats.node_types || {}).map(([k,v]) => '<div class="stat"><span class="num">' + v + '</span> ' + k + '</div>').join('') +
  (stats.edge_types && stats.edge_types.cross_boundary_import ? '<div class="stat"><span class="num">' + (
    (stats.edge_types.cross_boundary_import || 0) +
    (stats.edge_types.cross_boundary_call || 0) +
    (stats.edge_types.cross_boundary_method_call || 0)
  ) + '</span> cross-boundary</div>' : '');

// --- Project info ---
document.getElementById('project-name').textContent = GRAPH_DATA.project.root.split('/').pop();
document.getElementById('project-info').textContent =
  GRAPH_DATA.project.total_files + ' files · ' +
  Object.entries(GRAPH_DATA.project.languages || {}).filter(([k]) => k !== 'unknown').map(([k,v]) => v + ' ' + k).join(', ');
</script>
</body>
</html>"""


def generate_report_force(project_root: str) -> str:
    """Generate the force-directed view of the knowledge graph as a self-contained HTML."""
    graph_path = os.path.join(project_root, ".lumos", "knowledge-graph.json")

    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    graph_json = json.dumps(graph_data)
    html = HTML_TEMPLATE.replace("__GRAPH_JSON__", graph_json)

    report_path = os.path.join(project_root, ".lumos", "report-force.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    return report_path


def main():
    parser = argparse.ArgumentParser(description="Lumos Force Report Generator")
    parser.add_argument("project_root", nargs="?", default=".",
                        help="Project root directory")
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    report_path = generate_report_force(project_root)

    print(json.dumps({
        "status": "success",
        "report": report_path,
    }))


if __name__ == "__main__":
    main()
