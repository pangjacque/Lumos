#!/usr/bin/env python3
"""
Lumos Card-Style Report Generator v2
Three layout modes:
  - Hierarchy: tree view of codebase (file → function/class)
  - Notebook: single notebook explorer with cells top-to-bottom + cross-boundary edges
  - Force: physics-based layout (all nodes)
"""

import argparse
import json
import os
import sys


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600&display=swap" rel="stylesheet">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lumos — Project Knowledge Graph</title>
<!-- No external JS dependencies needed for Hierarchy/Notebook views -->
<style>
:root {
  --bg-primary: #0d1117; --bg-secondary: #161b22; --bg-tertiary: #21262d;
  --border: #30363d; --border-hover: #484f58;
  --text-primary: #f0f6fc; --text-secondary: #c9d1d9; --text-tertiary: #8b949e; --text-muted: #484f58;
  --accent: #f5c542;
  --color-file: #58a6ff; --color-function: #79c0ff; --color-class: #a5d6ff;
  --color-notebook: #3fb950; --color-cell: #56d364; --color-cell-md: #2ea043;
  --color-document: #d29922; --color-doc-section: #e3b341; --color-metric: #bc8cff;
  --color-error: #f85149; --color-cross-edge: #f85149; --color-doc-edge: #d29922;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg-primary); color: var(--text-secondary); overflow: hidden; }
#app { display: flex; height: 100vh; }

/* Header */
#header { position: absolute; top:0; left:0; right:400px; z-index:20; padding:12px 20px; background: linear-gradient(180deg, rgba(13,17,23,0.97) 0%, rgba(13,17,23,0.85) 70%, rgba(13,17,23,0) 100%); display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
#header h1 { font-size:28px; font-weight:600; color:#e0e6ed; letter-spacing:-0.02em; text-transform:lowercase; font-family:'Plus Jakarta Sans',sans-serif; white-space:nowrap; margin:0; line-height:1; display:flex; align-items:center; }
#header h1 .hl { color:#e8ecf0; text-shadow:0 0 8px rgba(232,236,240,0.6), 0 0 20px rgba(232,236,240,0.3); }
#search { padding:6px 10px; background:var(--bg-tertiary); border:1px solid var(--border); border-radius:6px; color:var(--text-secondary); font-size:12px; width:180px; outline:none; }
#search:focus { border-color:var(--accent); }
#mode-tabs { display:flex; gap:2px; background:var(--bg-tertiary); border-radius:8px; padding:2px; }
#mode-tabs button { padding:5px 14px; border-radius:6px; border:none; background:transparent; color:var(--text-tertiary); font-size:12px; cursor:pointer; font-weight:500; }
#mode-tabs button.active { background:var(--accent); color:var(--bg-primary); font-weight:600; }
#notebook-select { padding:5px 10px; background:var(--bg-tertiary); border:1px solid var(--border); border-radius:6px; color:var(--text-secondary); font-size:12px; outline:none; display:none; }

/* Main area */
#graph-area { flex:1; position:relative; overflow:hidden; }
#canvas-container { width:100%; height:100%; position:relative; overflow:auto; }

/* === HIERARCHY VIEW === */
#hierarchy-view { display:none; padding:80px 30px 30px 30px; overflow:auto; height:100%; }
.file-group { margin-bottom:20px; }
.file-card { background:var(--bg-secondary); border:1px solid var(--border); border-radius:10px; overflow:hidden; }
.file-card:hover { border-color:var(--border-hover); }
.file-header { display:flex; align-items:center; gap:10px; padding:10px 14px; border-bottom:1px solid var(--border); cursor:pointer; }
.file-header .color-dot { width:10px; height:10px; border-radius:3px; flex-shrink:0; }
.file-header .file-name { font-size:14px; font-weight:600; color:var(--text-primary); }
.file-header .file-path { font-size:11px; color:var(--text-muted); margin-left:auto; font-family:'SF Mono',Monaco,monospace; }
.file-header .file-badge { font-size:10px; padding:2px 6px; border-radius:4px; background:rgba(88,166,255,0.1); color:var(--color-file); }
.file-children { padding:6px; display:flex; flex-wrap:wrap; gap:6px; }
.entity-card { background:var(--bg-tertiary); border:1px solid transparent; border-radius:6px; padding:8px 10px; min-width:180px; max-width:260px; flex:1; cursor:pointer; transition: border-color 0.15s, box-shadow 0.15s; position:relative; }
.entity-card:hover { border-color:var(--border-hover); box-shadow:0 2px 8px rgba(0,0,0,0.3); }
.entity-card.selected { border-color:var(--accent); box-shadow:0 0 0 2px rgba(245,197,66,0.25); }
.entity-card.has-cross-ref { border-left: 3px solid var(--color-cross-edge); }
.entity-type { font-size:9px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:2px; }
.entity-name { font-size:13px; font-weight:500; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.entity-detail { font-size:10px; color:var(--text-muted); margin-top:2px; }
.entity-summary { font-size:11px; color:var(--text-tertiary); margin-top:3px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.entity-cross-badge { position:absolute; top:6px; right:6px; font-size:9px; padding:1px 5px; border-radius:3px; background:rgba(248,81,73,0.12); color:var(--color-error); }

/* Docs section in hierarchy */
.section-divider { font-size:13px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; padding:20px 0 8px 4px; border-top:1px solid var(--border); margin-top:20px; }
.doc-card { background:var(--bg-secondary); border:1px solid var(--border); border-radius:10px; overflow:hidden; margin-bottom:8px; }
.doc-card:hover { border-color:var(--border-hover); }
.doc-header { display:flex; align-items:center; gap:10px; padding:10px 14px; cursor:pointer; }
.doc-header .color-dot { width:10px; height:10px; border-radius:3px; flex-shrink:0; }
.doc-header .doc-name { font-size:14px; font-weight:600; color:var(--text-primary); }
.doc-header .doc-type-badge { font-size:10px; padding:2px 6px; border-radius:4px; background:rgba(210,153,34,0.12); color:var(--color-document); }
.doc-header .doc-path { font-size:10px; color:var(--text-muted); font-family:'SF Mono',Monaco,monospace; margin-left:auto; }
.doc-sections { padding:6px; display:flex; flex-direction:column; gap:4px; border-top:1px solid var(--border); }
.doc-section-item { padding:6px 10px; background:var(--bg-tertiary); border-radius:6px; cursor:pointer; transition:border-color 0.15s; border-left:3px solid transparent; }
.doc-section-item:hover { background:var(--border); }
.doc-section-item.selected { border-left-color:var(--accent); }
.doc-section-item .sec-level { display:inline-block; width:16px; color:var(--text-muted); font-size:10px; }
.doc-section-item .sec-name { font-size:12px; color:var(--text-primary); }
.doc-section-item .sec-refs { margin-top:2px; }
.doc-section-item .sec-ref-tag { font-size:9px; padding:1px 5px; border-radius:3px; margin:1px; display:inline-block; }
.doc-section-item .sec-ref-tag.code-ref { background:rgba(88,166,255,0.1); color:var(--color-file); }
.doc-section-item .sec-ref-tag.nb-ref { background:rgba(63,185,80,0.1); color:var(--color-notebook); }

/* Directory tree */
.dir-group { margin-bottom:4px; }
.dir-header { display:flex; align-items:center; gap:8px; padding:8px 12px; background:var(--bg-tertiary); border:1px solid var(--border); border-radius:8px; cursor:pointer; margin-bottom:2px; transition:background 0.12s; }
.dir-header:hover { background:var(--border); }
.dir-header .dir-icon { font-size:14px; transition:transform 0.15s; }
.dir-header.collapsed .dir-icon { transform:rotate(-90deg); }
.dir-header .dir-name { font-size:13px; font-weight:600; color:var(--text-primary); }
.dir-header .dir-path { font-size:10px; color:var(--text-muted); font-family:'SF Mono',Monaco,monospace; margin-left:auto; }
.dir-header .dir-count { font-size:10px; color:var(--text-muted); padding:1px 6px; background:rgba(255,255,255,0.04); border-radius:4px; }
.dir-children { padding-left:20px; border-left:2px solid var(--border); margin-left:14px; margin-bottom:6px; }
.dir-children.collapsed-content { display:none; }

/* === NOTEBOOK VIEW === */
#notebook-view { display:none; padding:80px 30px 30px 30px; overflow:auto; height:100%; }
#notebook-layout { display:flex; gap:40px; }
#cell-column { flex:0 0 420px; display:flex; flex-direction:column; gap:4px; align-items:center; }
#code-column { flex:0 0 300px; padding-top:20px; }
#code-column h3 { font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px; padding-left:8px; }

.cell-card { width:400px; background:var(--bg-secondary); border:1px solid var(--border); border-radius:8px; overflow:hidden; cursor:pointer; transition: border-color 0.15s; position:relative; }
.cell-card:hover { border-color:var(--border-hover); }
.cell-card.selected { border-color:var(--accent); box-shadow:0 0 0 2px rgba(245,197,66,0.25); }
.cell-color-bar { position:absolute; left:0; top:0; bottom:0; width:3px; }
.cell-content { padding:8px 10px 8px 12px; }
.cell-header { display:flex; align-items:center; gap:6px; margin-bottom:3px; }
.cell-type-badge { font-size:9px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; padding:1px 5px; border-radius:3px; background:rgba(255,255,255,0.05); }
.cell-exec { font-size:10px; color:var(--text-muted); font-family:'SF Mono',Monaco,monospace; }
.cell-status { font-size:9px; padding:1px 5px; border-radius:3px; font-weight:500; margin-left:auto; }
.cell-status.error { background:rgba(248,81,73,0.15); color:var(--color-error); }
.cell-title { font-size:12px; font-weight:500; color:var(--text-primary); }
.cell-source { font-size:10px; font-family:'SF Mono',Monaco,monospace; color:var(--text-tertiary); background:var(--bg-primary); border-radius:4px; padding:6px 8px; margin-top:4px; max-height:80px; overflow:hidden; white-space:pre-wrap; line-height:1.4; }
.cell-tags { display:flex; gap:3px; flex-wrap:wrap; margin-top:4px; }
.cell-tag { font-size:9px; padding:1px 5px; background:rgba(255,255,255,0.04); border-radius:3px; color:var(--text-muted); }
.cell-tag.import-tag { background:rgba(248,81,73,0.1); color:var(--color-error); }

.cell-flow-arrow { text-align:center; color:var(--text-muted); font-size:16px; line-height:1; }
.cell-tag.dataflow-tag { background:rgba(63,185,80,0.12); color:var(--color-notebook); }
.cell-dataflow-in { font-size:10px; color:var(--color-notebook); margin-top:3px; padding:3px 6px; background:rgba(63,185,80,0.06); border-radius:4px; }

.code-ref-card { background:var(--bg-secondary); border:1px solid var(--border); border-radius:6px; padding:8px 10px; margin-bottom:6px; cursor:pointer; border-left:3px solid var(--color-cross-edge); transition: border-color 0.15s; }
.code-ref-card:hover { border-color:var(--border-hover); }
.code-ref-card .ref-type { font-size:9px; color:var(--text-muted); text-transform:uppercase; }
.code-ref-card .ref-name { font-size:12px; color:var(--text-primary); font-weight:500; }
.code-ref-card .ref-file { font-size:10px; color:var(--text-muted); font-family:'SF Mono',Monaco,monospace; }
.code-ref-card .ref-edge { font-size:10px; color:var(--color-error); margin-top:2px; }

/* SVG edges for notebook view */
#nb-edge-svg { position:absolute; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:0; }

/* Sidebar */
#sidebar { width:400px; background:var(--bg-secondary); border-left:1px solid var(--border); overflow-y:auto; display:flex; flex-direction:column; z-index:15; }
#sidebar-header { padding:14px 16px; border-bottom:1px solid var(--border); }
#sidebar-header h2 { font-size:15px; color:var(--text-primary); margin-bottom:2px; }
#sidebar-header .subtitle { font-size:11px; color:var(--text-tertiary); }
#detail-panel { padding:14px 16px; flex:1; overflow-y:auto; }
#detail-panel .empty { color:var(--text-muted); font-style:italic; margin-top:40px; text-align:center; font-size:13px; }
.ds { margin-bottom:12px; }
.ds h3 { font-size:10px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:5px; }
.ds .val { font-size:13px; color:var(--text-secondary); line-height:1.5; }
.ds .tag { display:inline-block; padding:2px 6px; background:var(--bg-tertiary); border-radius:4px; font-size:10px; margin:2px; color:var(--text-tertiary); }
.ds pre { font-size:10px; background:var(--bg-primary); border:1px solid var(--border); border-radius:6px; padding:8px; overflow-x:auto; white-space:pre-wrap; color:var(--text-tertiary); line-height:1.4; max-height:200px; overflow-y:auto; }
.ci { padding:6px 8px; margin:2px 0; background:var(--bg-tertiary); border-radius:5px; cursor:pointer; transition:background 0.12s; border-left:3px solid transparent; }
.ci:hover { background:var(--border); }
.ci .ct { font-size:9px; color:var(--text-muted); }
.ci .cn { font-size:11px; color:var(--text-secondary); }
.ci.cross { border-left-color:var(--color-cross-edge); }
.ci.doc { border-left-color:var(--color-doc-edge); }
#stats-bar { padding:10px 16px; border-top:1px solid var(--border); background:var(--bg-primary); display:flex; gap:12px; flex-wrap:wrap; }
.stat { font-size:11px; color:var(--text-tertiary); }
.stat .num { color:var(--accent); font-weight:600; }
</style>
</head>
<body>
<div id="app">
  <div id="graph-area">
    <div id="header">
      <h1>lu<span class="hl">m</span>os</h1>
      <div id="mode-tabs">
        <button class="active" data-mode="hierarchy">Hierarchy</button>
        <button data-mode="notebook">Notebook</button>
        <button data-mode="force">Force</button>
      </div>
      <select id="notebook-select"></select>
      <input id="search" type="text" placeholder="Search...">
    </div>
    <div id="canvas-container">
      <div id="hierarchy-view"></div>
      <div id="notebook-view"></div>
    </div>
  </div>
  <div id="sidebar">
    <div id="sidebar-header">
      <h2 id="project-name"></h2>
      <div class="subtitle" id="project-info"></div>
    </div>
    <div id="detail-panel"><div class="empty">Click a node to see details</div></div>
    <div id="stats-bar"></div>
  </div>
</div>

<script>
const G = __GRAPH_JSON__;
const nodeMap = {}; G.nodes.forEach(n => nodeMap[n.id]=n);
const TYPE_COLORS = {file:'#58a6ff',function:'#79c0ff',class:'#a5d6ff',module:'#388bfd',notebook:'#3fb950',cell:'#56d364',document:'#d29922',doc_section:'#e3b341',metric_def:'#bc8cff'};
const CROSS = new Set(['cross_boundary_import','cross_boundary_call','cross_boundary_method_call','cross_boundary_instantiate']);
const DOC_E = new Set(['doc_references_code','doc_references_notebook','metric_implemented_by','defines_metric']);
let selectedId = null;
let currentMode = 'hierarchy';

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

// ===================== DETAIL PANEL =====================
function showDetail(id) {
  selectedId = id;
  let n = nodeMap[id]; if(!n) return;
  let panel = document.getElementById('detail-panel');
  let conns = G.edges.filter(e=>e.source===id||e.target===id);
  let inc = conns.filter(e=>e.target===id), out = conns.filter(e=>e.source===id);
  let color = TYPE_COLORS[n.type]||'#8b949e';
  let h = '<div class="ds"><h3>Node</h3><div class="val"><strong style="color:'+color+'">'+esc(n.name)+'</strong></div><div class="val">';
  h += '<span class="tag">'+n.type+'</span>';
  ['language','doc_type','status','complexity','kernel'].forEach(k=>{if(n[k])h+='<span class="tag">'+n[k]+'</span>';});
  h += '</div></div>';
  if(n.file){h+='<div class="ds"><h3>Location</h3><div class="val" style="font-family:monospace;font-size:12px">'+esc(n.file);if(n.line_start)h+=':'+n.line_start+'-'+n.line_end;h+='</div></div>';}
  if(n.summary)h+='<div class="ds"><h3>Summary</h3><div class="val">'+esc(n.summary)+'</div></div>';
  if(n.args&&n.args.length)h+='<div class="ds"><h3>Arguments</h3><div class="val">'+n.args.map(a=>'<span class="tag">'+esc(a)+'</span>').join('')+'</div></div>';
  if(n.methods&&n.methods.length)h+='<div class="ds"><h3>Methods ('+n.methods.length+')</h3><div class="val">'+n.methods.map(m=>'<span class="tag">'+esc(m)+'</span>').join('')+'</div></div>';
  if(n.bases&&n.bases.length)h+='<div class="ds"><h3>Inherits</h3><div class="val">'+n.bases.map(b=>'<span class="tag">'+esc(b)+'</span>').join('')+'</div></div>';
  if(n.defs&&n.defs.length)h+='<div class="ds"><h3>Defines</h3><div class="val">'+n.defs.map(d=>'<span class="tag">'+esc(d)+'</span>').join('')+'</div></div>';
  if(n.imports&&n.imports.length)h+='<div class="ds"><h3>Imports</h3><div class="val">'+n.imports.map(i=>'<span class="tag">'+esc((i.module||'')+'.'+i.name)+'</span>').join('')+'</div></div>';
  if(n.magics&&n.magics.length)h+='<div class="ds"><h3>Magics</h3><div class="val">'+n.magics.map(m=>'<span class="tag">%'+esc(m.name)+'</span>').join('')+'</div></div>';
  if(n.error)h+='<div class="ds"><h3>Error</h3><div class="val" style="color:var(--color-error)">'+esc(n.error.error_name+': '+n.error.error_value)+'</div></div>';
  if(n.source_preview)h+='<div class="ds"><h3>Source</h3><pre>'+esc(n.source_preview)+'</pre></div>';
  if(n.body_preview)h+='<div class="ds"><h3>Content</h3><pre>'+esc(n.body_preview)+'</pre></div>';
  if(inc.length){h+='<div class="ds"><h3>Incoming ('+inc.length+')</h3>';inc.forEach(e=>{let sn=nodeMap[e.source];let cls=CROSS.has(e.type)?'cross':(DOC_E.has(e.type)?'doc':'');h+='<div class="ci '+cls+'" onclick="selectNode(\''+esc(e.source)+'\')"><div class="ct">'+e.type.replace(/_/g,' ')+'</div><div class="cn">'+(sn?esc(sn.name):esc(e.source))+'</div></div>';});h+='</div>';}
  if(out.length){h+='<div class="ds"><h3>Outgoing ('+out.length+')</h3>';out.forEach(e=>{let tn=nodeMap[e.target];let cls=CROSS.has(e.type)?'cross':(DOC_E.has(e.type)?'doc':'');h+='<div class="ci '+cls+'" onclick="selectNode(\''+esc(e.target)+'\')"><div class="ct">'+e.type.replace(/_/g,' ')+'</div><div class="cn">'+(tn?esc(tn.name):esc(e.target))+'</div></div>';});h+='</div>';}
  panel.innerHTML = h;
}

function selectNode(id) {
  showDetail(id);
  if (currentMode==='hierarchy') renderHierarchy();
  else if (currentMode==='notebook') renderNotebook();
  else renderForce();
}

// ===================== HIERARCHY VIEW =====================
// Build directory tree from file paths
function buildDirTree(fileNodes, containsEdges) {
  let root = {name:'', path:'', children:{}, files:[]};
  fileNodes.forEach(file => {
    let parts = (file.file||'').split('/');
    let fileName = parts.pop();
    // Skip __init__.py
    if (fileName === '__init__.py' || fileName === '__init__.pyi') return;
    let current = root;
    let pathSoFar = '';
    parts.forEach(part => {
      pathSoFar += (pathSoFar?'/':'') + part;
      if (!current.children[part]) current.children[part] = {name:part, path:pathSoFar, children:{}, files:[]};
      current = current.children[part];
    });
    let entities = containsEdges.filter(e=>e.source===file.id).map(e=>nodeMap[e.target]).filter(Boolean);
    current.files.push({node:file, entities:entities});
  });
  return root;
}

function countTreeEntities(dir) {
  let count = 0;
  dir.files.forEach(f => count += f.entities.length);
  Object.values(dir.children).forEach(child => count += countTreeEntities(child));
  return count;
}

function renderDirTree(dir, query, crossTargets, crossCounts, depth) {
  let html = '';
  // Sort: directories first, then files
  let dirs = Object.values(dir.children).sort((a,b)=>a.name.localeCompare(b.name));
  let files = dir.files.sort((a,b)=>(a.node.name||'').localeCompare(b.node.name||''));

  dirs.forEach(subdir => {
    let totalEntities = countTreeEntities(subdir);
    // Search: check if anything in this subtree matches
    if (query) {
      let subtreeHtml = renderDirTree(subdir, query, crossTargets, crossCounts, depth+1);
      if (!subtreeHtml.trim()) return;
      let dirId = 'dir-'+subdir.path.replace(/[^a-zA-Z0-9]/g,'-');
      html += '<div class="dir-group">';
      html += '<div class="dir-header" onclick="toggleDir(\''+dirId+'\')" id="dh-'+dirId+'">';
      html += '<span class="dir-icon">&#9662;</span>';
      html += '<span class="dir-name">'+esc(subdir.name)+'/</span>';
      html += '<span class="dir-count">'+totalEntities+' entities</span>';
      if (depth===0) html += '<span class="dir-path">'+esc(subdir.path)+'</span>';
      html += '</div>';
      html += '<div class="dir-children" id="dc-'+dirId+'">'+subtreeHtml+'</div>';
      html += '</div>';
      return;
    }
    let dirId = 'dir-'+subdir.path.replace(/[^a-zA-Z0-9]/g,'-');
    html += '<div class="dir-group">';
    html += '<div class="dir-header" onclick="toggleDir(\''+dirId+'\')" id="dh-'+dirId+'">';
    html += '<span class="dir-icon">&#9662;</span>';
    html += '<span class="dir-name">'+esc(subdir.name)+'/</span>';
    html += '<span class="dir-count">'+totalEntities+' entities</span>';
    if (depth===0) html += '<span class="dir-path">'+esc(subdir.path)+'</span>';
    html += '</div>';
    let collapsed = depth > 1 ? ' collapsed-content' : '';
    html += '<div class="dir-children'+collapsed+'" id="dc-'+dirId+'">';
    html += renderDirTree(subdir, query, crossTargets, crossCounts, depth+1);
    html += '</div></div>';
    // If collapsed by default, also mark header
    if (depth > 1) {
      html = html.replace('id="dh-'+dirId+'"', 'id="dh-'+dirId+'" class="dir-header collapsed"');
    }
  });

  files.forEach(({node: file, entities}) => {
    // Search filter
    let fileMatch = !query || file.name.toLowerCase().includes(query) || (file.file||'').toLowerCase().includes(query);
    let childMatches = entities.filter(c=>!query || c.name.toLowerCase().includes(query));
    if (query && !fileMatch && childMatches.length===0) return;
    let shownChildren = query ? childMatches : entities;
    // Skip files with no entities (unless search matches the file itself)
    if (!shownChildren.length && !fileMatch) return;

    html += '<div class="file-group"><div class="file-card">';
    html += '<div class="file-header" onclick="selectNode(\''+esc(file.id)+'\')">';
    html += '<div class="color-dot" style="background:var(--color-file)"></div>';
    html += '<span class="file-name">'+esc(file.name)+'</span>';
    if (shownChildren.length) html += '<span class="file-badge">'+shownChildren.length+' entities</span>';
    html += '</div>';
    if (shownChildren.length) {
      html += '<div class="file-children">';
      shownChildren.sort((a,b)=>{if(a.type==='class'&&b.type!=='class')return -1;if(b.type==='class'&&a.type!=='class')return 1;return a.name.localeCompare(b.name);});
      shownChildren.forEach(child => {
        let color = TYPE_COLORS[child.type]||'#8b949e';
        let hasCross = crossTargets.has(child.id);
        let cls = 'entity-card' + (selectedId===child.id?' selected':'') + (hasCross?' has-cross-ref':'');
        html += '<div class="'+cls+'" onclick="selectNode(\''+esc(child.id)+'\')">';
        html += '<div class="entity-type" style="color:'+color+'">'+child.type+'</div>';
        html += '<div class="entity-name">'+esc(child.name)+'</div>';
        if (child.type==='function' && child.args && child.args.length) html += '<div class="entity-detail">('+child.args.slice(0,4).map(esc).join(', ')+(child.args.length>4?', ...':'')+')</div>';
        if (child.type==='class' && child.methods) html += '<div class="entity-detail">'+child.methods.length+' methods'+(child.bases&&child.bases.length?' · extends '+child.bases[0]:'')+'</div>';
        if (child.summary) html += '<div class="entity-summary">'+esc(child.summary)+'</div>';
        if (hasCross) html += '<div class="entity-cross-badge">'+crossCounts[child.id]+' notebook ref'+(crossCounts[child.id]>1?'s':'')+'</div>';
        html += '</div>';
      });
      html += '</div>';
    }
    html += '</div></div>';
  });
  return html;
}

function toggleDir(dirId) {
  let header = document.getElementById('dh-'+dirId);
  let content = document.getElementById('dc-'+dirId);
  if (!header||!content) return;
  header.classList.toggle('collapsed');
  content.classList.toggle('collapsed-content');
}

function renderHierarchy() {
  let view = document.getElementById('hierarchy-view');
  let query = document.getElementById('search').value.toLowerCase();
  let fileNodes = G.nodes.filter(n=>n.type==='file');
  let containsEdges = G.edges.filter(e=>e.type==='contains');
  let crossTargets = new Set();
  G.edges.filter(e=>CROSS.has(e.type)).forEach(e=>crossTargets.add(e.target));
  let crossCounts = {};
  G.edges.filter(e=>CROSS.has(e.type)).forEach(e=>{crossCounts[e.target]=(crossCounts[e.target]||0)+1;});

  let tree = buildDirTree(fileNodes, containsEdges);
  let html = renderDirTree(tree, query, crossTargets, crossCounts, 0);
  if (!html.trim()) html = '<div style="text-align:center;color:var(--text-muted);padding:60px">No code files found</div>';
  view.innerHTML = html;
}

// ===================== NOTEBOOK VIEW =====================
function renderNotebook() {
  let view = document.getElementById('notebook-view');
  let nbSelect = document.getElementById('notebook-select');
  let nbFile = nbSelect.value;
  if (!nbFile) { view.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:60px">Select a notebook above</div>'; return; }

  // Get notebook node and its cells
  let nbNode = G.nodes.find(n=>n.type==='notebook'&&n.file===nbFile);
  if (!nbNode) { view.innerHTML='<div style="text-align:center;color:var(--text-muted);padding:60px">Notebook not found</div>'; return; }
  let cellIds = G.edges.filter(e=>e.source===nbNode.id&&e.type==='contains').map(e=>e.target);
  let cells = cellIds.map(id=>nodeMap[id]).filter(Boolean).sort((a,b)=>(a.cell_index||0)-(b.cell_index||0));

  // Find cross-boundary edges from this notebook's cells
  let crossEdges = G.edges.filter(e=>CROSS.has(e.type)&&cellIds.includes(e.source));
  // Unique code targets
  let codeTargetIds = [...new Set(crossEdges.map(e=>e.target))];
  let codeTargets = codeTargetIds.map(id=>nodeMap[id]).filter(Boolean);
  // Map: cell_id → list of cross edges
  let cellCrossMap = {};
  crossEdges.forEach(e=>{if(!cellCrossMap[e.source])cellCrossMap[e.source]=[];cellCrossMap[e.source].push(e);});
  // Map: cell_id → incoming data flow edges (variable dependencies)
  let cellDataFlowIn = {};
  G.edges.filter(e=>e.type==='cell_data_flow'&&cellIds.includes(e.target)).forEach(e=>{
    if(!cellDataFlowIn[e.target])cellDataFlowIn[e.target]=[];
    cellDataFlowIn[e.target].push(e);
  });
  // Map: cell_id → outgoing data flow edges
  let cellDataFlowOut = {};
  G.edges.filter(e=>e.type==='cell_data_flow'&&cellIds.includes(e.source)).forEach(e=>{
    if(!cellDataFlowOut[e.source])cellDataFlowOut[e.source]=[];
    cellDataFlowOut[e.source].push(e);
  });

  let html = '<div id="notebook-layout">';
  // Left: cells column
  html += '<div id="cell-column">';
  cells.forEach((cell, idx) => {
    let isCode = cell.cell_type === 'code';
    let color = isCode ? (cell.status==='error'?'var(--color-error)':'var(--color-cell)') : 'var(--color-cell-md)';
    let cls = 'cell-card' + (selectedId===cell.id?' selected':'');
    html += '<div class="'+cls+'" onclick="selectNode(\''+esc(cell.id)+'\')" data-cellid="'+esc(cell.id)+'">';
    html += '<div class="cell-color-bar" style="background:'+color+'"></div>';
    html += '<div class="cell-content">';
    // Header
    html += '<div class="cell-header">';
    html += '<span class="cell-type-badge" style="color:'+color+'">'+(isCode?'code':'markdown')+'</span>';
    if (cell.execution_count!=null) html += '<span class="cell-exec">In['+cell.execution_count+']</span>';
    if (cell.status==='error') html += '<span class="cell-status error">error</span>';
    html += '</div>';
    // Title
    html += '<div class="cell-title">'+esc(cell.name)+'</div>';
    // Source preview
    if (cell.source_preview) {
      let src = cell.source_preview.slice(0,200);
      html += '<div class="cell-source">'+esc(src)+'</div>';
    }
    // Incoming data flow — which variables this cell depends on and from where
    let inFlows = cellDataFlowIn[cell.id]||[];
    if (inFlows.length) {
      html += '<div class="cell-dataflow-in">&#8592; depends on: ';
      inFlows.forEach((e,i)=>{
        let srcNode = nodeMap[e.source];
        let varName = (e.detail&&e.detail.variable)||'?';
        let srcLabel = srcNode ? srcNode.name : '?';
        if(i>0) html+=', ';
        html += '<strong>'+esc(varName)+'</strong> from '+esc(srcLabel);
      });
      html += '</div>';
    }
    // Tags: imports, magics, defs, outgoing data flow
    let crossRefs = cellCrossMap[cell.id]||[];
    let outFlows = cellDataFlowOut[cell.id]||[];
    if (crossRefs.length || outFlows.length || (cell.magics&&cell.magics.length) || (cell.defs&&cell.defs.length)) {
      html += '<div class="cell-tags">';
      crossRefs.forEach(e=>{let tn=nodeMap[e.target];html+='<span class="cell-tag import-tag">'+esc(e.type.replace(/_/g,' '))+': '+(tn?esc(tn.name):esc(e.target))+'</span>';});
      if(cell.defs)cell.defs.slice(0,5).forEach(d=>{html+='<span class="cell-tag dataflow-tag">def '+esc(d)+'</span>';});
      if(cell.magics)cell.magics.forEach(m=>{html+='<span class="cell-tag">%'+esc(m.name)+'</span>';});
      html += '</div>';
    }
    html += '</div></div>';
    // Flow arrow
    if (idx < cells.length-1) html += '<div class="cell-flow-arrow">&#9661;</div>';
  });
  html += '</div>';

  // Right: code references column
  html += '<div id="code-column">';
  html += '<h3>Codebase References ('+codeTargets.length+')</h3>';
  codeTargets.forEach(ct => {
    let edgesTo = crossEdges.filter(e=>e.target===ct.id);
    let cellNames = edgesTo.map(e=>{let cn=nodeMap[e.source];return cn?cn.name:e.source;});
    html += '<div class="code-ref-card" onclick="selectNode(\''+esc(ct.id)+'\')">';
    html += '<div class="ref-type" style="color:'+(TYPE_COLORS[ct.type]||'#8b949e')+'">'+ct.type+'</div>';
    html += '<div class="ref-name">'+esc(ct.name)+'</div>';
    if (ct.file) html += '<div class="ref-file">'+esc(ct.file)+(ct.line_start?':'+ct.line_start:'')+'</div>';
    html += '<div class="ref-edge">Called from: '+cellNames.map(esc).join(', ')+'</div>';
    html += '</div>';
  });
  if (!codeTargets.length) html += '<div style="color:var(--text-muted);font-size:12px;padding:8px">No cross-boundary references found in this notebook</div>';
  html += '</div></div>';

  view.innerHTML = html;
}

// ===================== MODE SWITCHING =====================
function switchMode(mode) {
  if (mode==='force') {
    // Open the separate force-graph report
    window.location.href = window.location.href.replace('report-cards.html','report.html');
    return;
  }
  currentMode = mode;
  document.querySelectorAll('#mode-tabs button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  document.getElementById('hierarchy-view').style.display = mode==='hierarchy'?'block':'none';
  document.getElementById('notebook-view').style.display = mode==='notebook'?'block':'none';
  document.getElementById('notebook-select').style.display = mode==='notebook'?'inline-block':'none';
  document.getElementById('search').style.display = mode==='notebook'?'none':'inline-block';
  if (mode==='hierarchy') renderHierarchy();
  else if (mode==='notebook') renderNotebook();
}
document.querySelectorAll('#mode-tabs button').forEach(btn=>{btn.addEventListener('click',()=>switchMode(btn.dataset.mode));});

// ===================== NOTEBOOK SELECTOR =====================
let notebooks = G.nodes.filter(n=>n.type==='notebook').sort((a,b)=>(a.file||'').localeCompare(b.file||''));
let nbSelect = document.getElementById('notebook-select');
nbSelect.innerHTML = '<option value="">-- Select notebook --</option>' + notebooks.map(n=>'<option value="'+esc(n.file)+'">'+esc(n.file)+'</option>').join('');
nbSelect.addEventListener('change', ()=>renderNotebook());

// ===================== SEARCH =====================
document.getElementById('search').addEventListener('input', ()=>{
  if(currentMode==='hierarchy') renderHierarchy();
});

// ===================== STATS =====================
let stats=G.stats;
document.getElementById('stats-bar').innerHTML=
  '<div class="stat"><span class="num">'+stats.total_nodes+'</span> nodes</div>'+
  '<div class="stat"><span class="num">'+stats.total_edges+'</span> edges</div>'+
  Object.entries(stats.node_types||{}).map(([k,v])=>'<div class="stat"><span class="num">'+v+'</span> '+k+'</div>').join('')+
  (stats.edge_types?.cross_boundary_import?'<div class="stat"><span class="num">'+((stats.edge_types.cross_boundary_import||0)+(stats.edge_types.cross_boundary_call||0)+(stats.edge_types.cross_boundary_method_call||0))+'</span> cross-boundary</div>':'');

document.getElementById('project-name').textContent=(G.project.root||'').split('/').pop();
document.getElementById('project-info').textContent=G.project.total_files+' files · '+Object.entries(G.project.languages||{}).filter(([k])=>k!=='unknown').map(([k,v])=>v+' '+k).join(', ');

// Init
switchMode('hierarchy');
</script>
</body>
</html>"""


def generate_report(project_root):
    graph_path = os.path.join(project_root, ".lumos", "knowledge-graph.json")
    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    graph_json = json.dumps(graph_data)
    html = HTML_TEMPLATE.replace("__GRAPH_JSON__", graph_json)
    report_path = os.path.join(project_root, ".lumos", "report-cards.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Lumos Card-Style Report Generator v2")
    parser.add_argument("project_root", nargs="?", default=".", help="Project root directory")
    args = parser.parse_args()
    project_root = os.path.abspath(args.project_root)
    report_path = generate_report(project_root)
    print(json.dumps({"status": "success", "report": report_path}))


if __name__ == "__main__":
    main()
