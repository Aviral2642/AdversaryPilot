"""Self-contained HTML template for AdversaryPilot report visualization.

Uses pure vanilla JS + Canvas for attack graph, SVG for heatmap.
Zero external dependencies — works fully offline.
"""

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AdversaryPilot Security Assessment Report</title>
<style>
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --bg-card: #1c2128;
    --border: #30363d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --accent: #58a6ff;
    --accent-dim: #1f6feb;
    --success: #3fb950;
    --danger: #f85149;
    --warning: #d29922;
    --info: #58a6ff;
    --purple: #bc8cff;
    --cyan: #39d2c0;
    --orange: #f0883e;
    --pink: #f778ba;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; background: var(--bg-primary); color: var(--text-primary); line-height: 1.5; }
.container { max-width: 1440px; margin: 0 auto; padding: 24px; }
a { color: var(--accent); text-decoration: none; }

/* Header */
.report-header { background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%); border: 1px solid var(--border); border-radius: 12px; padding: 32px; margin-bottom: 24px; position: relative; overflow: hidden; }
.report-header::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, var(--danger), var(--warning), var(--success)); }
.report-title { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.report-subtitle { color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; }
.header-meta { display: flex; flex-wrap: wrap; gap: 24px; }
.meta-item { display: flex; flex-direction: column; }
.meta-label { color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; }
.meta-value { font-size: 14px; font-weight: 500; }

/* Summary Cards */
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.summary-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 20px; text-align: center; }
.summary-card .value { font-size: 36px; font-weight: 700; line-height: 1.2; }
.summary-card .label { color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.value-danger { color: var(--danger); }
.value-warning { color: var(--warning); }
.value-success { color: var(--success); }
.value-info { color: var(--accent); }
.value-purple { color: var(--purple); }

/* Tabs */
.tab-bar { display: flex; gap: 4px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 4px; margin-bottom: 24px; overflow-x: auto; }
.tab-btn { background: transparent; color: var(--text-secondary); border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; white-space: nowrap; transition: all 0.2s; }
.tab-btn:hover { color: var(--text-primary); background: var(--bg-tertiary); }
.tab-btn.active { background: var(--accent-dim); color: #fff; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* Cards / Panels */
.panel { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 24px; overflow: hidden; }
.panel-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.panel-header h3 { font-size: 15px; font-weight: 600; }
.panel-body { padding: 20px; }

/* Attack Graph Canvas */
#graph-canvas { width: 100%; height: 650px; background: var(--bg-primary); border-radius: 6px; cursor: grab; }
#graph-canvas:active { cursor: grabbing; }
.graph-controls { display: flex; gap: 8px; padding: 12px 20px; border-top: 1px solid var(--border); }
.graph-controls button { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border); padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; }
.graph-controls button:hover { background: var(--border); }
.graph-legend { display: flex; gap: 16px; padding: 12px 20px; border-top: 1px solid var(--border); flex-wrap: wrap; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.legend-dot { width: 12px; height: 12px; border-radius: 50%; }

/* Layer Cards */
.layer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; }
.layer-card { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 8px; padding: 20px; position: relative; }
.layer-card.primary { border-color: var(--danger); }
.layer-card .layer-name { font-size: 16px; font-weight: 600; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
.layer-card .primary-badge { background: var(--danger); color: #fff; font-size: 10px; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; font-weight: 600; }
.layer-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.layer-stat { }
.layer-stat .stat-label { color: var(--text-muted); font-size: 11px; text-transform: uppercase; }
.layer-stat .stat-value { font-size: 18px; font-weight: 600; }
.progress-bar { height: 6px; background: var(--bg-tertiary); border-radius: 3px; margin: 12px 0; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.rec-list { list-style: none; margin-top: 12px; }
.rec-list li { padding: 8px 12px; background: var(--bg-tertiary); border-radius: 4px; margin-bottom: 6px; font-size: 13px; color: var(--text-secondary); border-left: 3px solid var(--border); }
.rec-list li.high { border-left-color: var(--danger); }
.rec-list li.moderate { border-left-color: var(--warning); }

/* Heatmap */
.heatmap-container { overflow-x: auto; }
.heatmap-table { border-collapse: collapse; width: 100%; }
.heatmap-table th { padding: 10px 14px; text-align: center; font-size: 12px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border); }
.heatmap-table td { padding: 14px; text-align: center; font-size: 14px; font-weight: 600; border-bottom: 1px solid var(--border); position: relative; min-width: 90px; }
.heatmap-table .row-header { text-align: left; font-weight: 600; color: var(--text-primary); text-transform: capitalize; }

/* Technique Table */
.tech-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.tech-table th { padding: 10px 12px; text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 11px; text-transform: uppercase; border-bottom: 1px solid var(--border); position: sticky; top: 0; background: var(--bg-secondary); }
.tech-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.tech-table tr:hover { background: var(--bg-tertiary); }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.badge-success { background: rgba(63,185,80,0.15); color: var(--success); }
.badge-danger { background: rgba(248,81,73,0.15); color: var(--danger); }
.badge-warning { background: rgba(210,153,34,0.15); color: var(--warning); }
.badge-info { background: rgba(88,166,255,0.15); color: var(--accent); }
.badge-neutral { background: rgba(139,148,158,0.15); color: var(--text-secondary); }
.score-bar { display: inline-block; height: 8px; border-radius: 4px; background: var(--bg-tertiary); width: 60px; position: relative; vertical-align: middle; margin-left: 6px; }
.score-fill { height: 100%; border-radius: 4px; }

/* Executive Summary */
.exec-summary { line-height: 1.8; }
.exec-summary p { margin-bottom: 12px; color: var(--text-secondary); }
.exec-summary .finding { padding: 16px; background: var(--bg-tertiary); border-radius: 6px; margin-bottom: 12px; border-left: 3px solid var(--accent); }
.exec-summary .finding.critical { border-left-color: var(--danger); }
.exec-summary .finding.moderate { border-left-color: var(--warning); }
.exec-summary .finding.low { border-left-color: var(--success); }
.exec-summary .finding h4 { font-size: 14px; margin-bottom: 4px; }
.exec-summary .finding p { color: var(--text-secondary); font-size: 13px; margin-bottom: 0; }

/* ATLAS Mapping */
.atlas-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.atlas-card { background: var(--bg-tertiary); border-radius: 6px; padding: 14px; }
.atlas-card .atlas-id { font-family: monospace; color: var(--purple); font-size: 13px; font-weight: 600; }
.atlas-card .atlas-name { font-size: 13px; margin-top: 4px; }
.atlas-card .atlas-techniques { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px; }
.atlas-tag { background: var(--bg-secondary); padding: 2px 8px; border-radius: 4px; font-size: 11px; color: var(--text-secondary); }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.stat-panel { background: var(--bg-tertiary); border-radius: 6px; padding: 16px; }
.stat-panel h4 { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; text-transform: uppercase; }
.stat-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.stat-row:last-child { border-bottom: none; }
.stat-key { color: var(--text-secondary); }

/* Raw Data */
.raw-data-pre { background: var(--bg-primary); padding: 16px; border-radius: 6px; overflow: auto; max-height: 600px; font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; font-size: 12px; line-height: 1.6; color: var(--text-secondary); }

/* Responsive */
@media (max-width: 768px) {
    .summary-grid { grid-template-columns: repeat(2, 1fr); }
    .layer-grid { grid-template-columns: 1fr; }
    .header-meta { gap: 12px; }
    .tab-bar { overflow-x: auto; }
}
</style>
</head>
<body>
<div class="container">
    <!-- Header -->
    <div class="report-header">
        <div class="report-title" id="report-title">AdversaryPilot Security Assessment</div>
        <div class="report-subtitle" id="report-subtitle"></div>
        <div class="header-meta" id="header-meta"></div>
    </div>

    <!-- Summary Cards -->
    <div class="summary-grid" id="summary-grid"></div>

    <!-- Tab Navigation -->
    <div class="tab-bar" id="tab-bar">
        <button class="tab-btn active" data-tab="executive">Executive Summary</button>
        <button class="tab-btn" data-tab="graph">Attack Graph</button>
        <button class="tab-btn" data-tab="layers">Layer Analysis</button>
        <button class="tab-btn" data-tab="heatmap">Risk Heatmap</button>
        <button class="tab-btn" data-tab="techniques">Technique Details</button>
        <button class="tab-btn" data-tab="atlas">ATLAS Mapping</button>
        <button class="tab-btn" data-tab="compliance">Compliance</button>
        <button class="tab-btn" data-tab="beliefs">Belief Evolution</button>
        <button class="tab-btn" data-tab="statistics">Statistics</button>
        <button class="tab-btn" data-tab="rawdata">Raw Data</button>
    </div>

    <!-- Tab Panels -->
    <div id="executive-panel" class="tab-panel active"></div>

    <div id="compliance-panel" class="tab-panel"></div>

    <div id="beliefs-panel" class="tab-panel"></div>

    <div id="graph-panel" class="tab-panel">
        <div class="panel">
            <div class="panel-header"><h3>Attack Technique Graph</h3><span id="graph-info" style="font-size:12px;color:var(--text-muted)"></span></div>
            <canvas id="graph-canvas"></canvas>
            <div class="graph-controls">
                <button onclick="resetGraph()">Reset View</button>
                <button onclick="toggleLabels()">Toggle Labels</button>
                <button onclick="togglePhysics()">Pause/Resume</button>
            </div>
            <div class="graph-legend">
                <div class="legend-item"><div class="legend-dot" style="background:var(--success)"></div>Success</div>
                <div class="legend-item"><div class="legend-dot" style="background:var(--danger)"></div>Failure</div>
                <div class="legend-item"><div class="legend-dot" style="background:var(--warning)"></div>Inconclusive</div>
                <div class="legend-item"><div class="legend-dot" style="background:var(--text-muted)"></div>Untried</div>
                <div class="legend-item"><div class="legend-dot" style="background:var(--purple)"></div>ATLAS Link</div>
            </div>
        </div>
    </div>

    <div id="layers-panel" class="tab-panel">
        <div class="layer-grid" id="layer-grid"></div>
    </div>

    <div id="heatmap-panel" class="tab-panel">
        <div class="panel">
            <div class="panel-header"><h3>Risk Heatmap: Surface x Goal</h3></div>
            <div class="panel-body heatmap-container" id="heatmap-body"></div>
        </div>
    </div>

    <div id="techniques-panel" class="tab-panel">
        <div class="panel">
            <div class="panel-header"><h3>Technique Details</h3><span id="tech-count" style="font-size:12px;color:var(--text-muted)"></span></div>
            <div style="overflow-x:auto"><table class="tech-table" id="tech-table"><thead></thead><tbody></tbody></table></div>
        </div>
    </div>

    <div id="atlas-panel" class="tab-panel">
        <div class="panel">
            <div class="panel-header"><h3>MITRE ATLAS Technique Mapping</h3></div>
            <div class="panel-body"><div class="atlas-grid" id="atlas-grid"></div></div>
        </div>
    </div>

    <div id="statistics-panel" class="tab-panel">
        <div class="stats-grid" id="stats-grid"></div>
    </div>

    <div id="rawdata-panel" class="tab-panel">
        <div class="panel">
            <div class="panel-header"><h3>Raw Report Data (JSON)</h3></div>
            <div class="panel-body"><pre class="raw-data-pre" id="raw-data"></pre></div>
        </div>
    </div>
</div>

<script>
// ============================================================================
// DATA INJECTION POINT
// ============================================================================
const DATA = {{DATA_JSON}};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
function esc(text) {
    if (text == null) return '';
    const d = document.createElement('div');
    d.textContent = String(text);
    return d.innerHTML;
}

function pct(v) { return (v * 100).toFixed(1) + '%'; }

function riskColor(score) {
    if (score >= 0.7) return 'var(--danger)';
    if (score >= 0.4) return 'var(--warning)';
    if (score > 0) return 'var(--success)';
    return 'var(--text-muted)';
}

function riskLabel(score) {
    if (score >= 0.7) return 'Critical';
    if (score >= 0.4) return 'Moderate';
    if (score > 0.1) return 'Low';
    return 'Minimal';
}

function outcomeClass(success) {
    if (success === true) return 'badge-success';
    if (success === false) return 'badge-danger';
    return 'badge-warning';
}

function outcomeText(success) {
    if (success === true) return 'Success';
    if (success === false) return 'Failure';
    return 'Inconclusive';
}

// ============================================================================
// HEADER + SUMMARY
// ============================================================================
function renderHeader() {
    const r = DATA.report;
    document.getElementById('report-title').textContent = r.title || 'AdversaryPilot Security Assessment';
    document.getElementById('report-subtitle').textContent = r.overall_risk_summary || '';

    const meta = document.getElementById('header-meta');
    const items = [
        ['Campaign', r.campaign_id],
        ['Target Type', r.target_type],
        ['Target Name', r.target_name || ''],
        ['Generated', r.generated_at ? new Date(r.generated_at).toLocaleString() : ''],
        ['Primary Weakness', r.primary_weak_layer || 'None'],
    ].filter(([,v]) => v);

    meta.innerHTML = items.map(([label, value]) =>
        `<div class="meta-item"><span class="meta-label">${esc(label)}</span><span class="meta-value">${esc(value)}</span></div>`
    ).join('');
}

function renderSummary() {
    const s = DATA.statistics || {};
    const grid = document.getElementById('summary-grid');
    const cards = [
        { value: s.total_techniques_tested || 0, label: 'Techniques Tested', cls: 'value-info' },
        { value: s.total_attempts || 0, label: 'Total Attempts', cls: 'value-purple' },
        { value: s.success_count || 0, label: 'Successful Attacks', cls: 'value-danger' },
        { value: pct(s.overall_success_rate || 0), label: 'Attack Success Rate', cls: (s.overall_success_rate || 0) > 0.3 ? 'value-danger' : 'value-success' },
        { value: s.layers_tested || 0, label: 'Layers Assessed', cls: 'value-info' },
        { value: riskLabel(s.max_risk_score || 0), label: 'Max Risk Level', cls: (s.max_risk_score || 0) >= 0.7 ? 'value-danger' : (s.max_risk_score || 0) >= 0.4 ? 'value-warning' : 'value-success' },
    ];
    grid.innerHTML = cards.map(c =>
        `<div class="summary-card"><div class="value ${c.cls}">${esc(String(c.value))}</div><div class="label">${esc(c.label)}</div></div>`
    ).join('');
}

// ============================================================================
// EXECUTIVE SUMMARY
// ============================================================================
function renderExecutive() {
    const panel = document.getElementById('executive-panel');
    const r = DATA.report;
    const s = DATA.statistics || {};
    const layers = DATA.layers || [];
    const techs = DATA.techniques || [];

    const primaryLayer = layers.find(l => l.is_primary_weakness);
    const testedLayers = layers.filter(l => l.techniques_tested > 0);
    const untestedLayers = layers.filter(l => l.techniques_tested === 0);
    const successfulTechs = techs.filter(t => t.success === true);
    const failedTechs = techs.filter(t => t.success === false);

    let html = '<div class="panel"><div class="panel-header"><h3>Executive Summary</h3></div><div class="panel-body exec-summary">';

    html += `<p>This assessment evaluated <strong>${s.total_techniques_tested || 0} attack techniques</strong> across
        <strong>${testedLayers.length} attack surface layers</strong> against the target system
        (${esc(r.target_type || 'unknown')}). A total of <strong>${s.total_attempts || 0} attack attempts</strong>
        were executed with an overall success rate of <strong>${pct(s.overall_success_rate || 0)}</strong>.</p>`;

    if (r.overall_risk_summary) {
        html += `<p>${esc(r.overall_risk_summary)}</p>`;
    }

    // Key findings
    html += '<h4 style="margin: 20px 0 12px; font-size: 15px;">Key Findings</h4>';

    if (primaryLayer) {
        const severity = primaryLayer.risk_score >= 0.7 ? 'critical' : primaryLayer.risk_score >= 0.4 ? 'moderate' : 'low';
        html += `<div class="finding ${severity}">
            <h4>Primary Weakness: ${esc(primaryLayer.layer.toUpperCase())} Layer</h4>
            <p>Risk score ${pct(primaryLayer.risk_score)} with ${pct(primaryLayer.success_rate)} attack success rate
            across ${primaryLayer.techniques_tested} techniques tested.
            Confidence interval: [${primaryLayer.confidence_interval[0].toFixed(2)}, ${primaryLayer.confidence_interval[1].toFixed(2)}].</p>
        </div>`;
    }

    if (successfulTechs.length > 0) {
        const topSuccesses = successfulTechs.sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, 5);
        html += `<div class="finding critical">
            <h4>${successfulTechs.length} Techniques Succeeded</h4>
            <p>Highest impact: ${topSuccesses.map(t => esc(t.name) + ' (' + pct(t.score || 0) + ')').join(', ')}.</p>
        </div>`;
    }

    if (untestedLayers.length > 0) {
        html += `<div class="finding moderate">
            <h4>${untestedLayers.length} Layer(s) Not Yet Tested</h4>
            <p>The following layers have no test coverage: ${untestedLayers.map(l => esc(l.layer)).join(', ')}.
            Additional testing is recommended.</p>
        </div>`;
    }

    if (failedTechs.length > 0) {
        html += `<div class="finding low">
            <h4>${failedTechs.length} Techniques Defended Successfully</h4>
            <p>The target successfully defended against ${failedTechs.length} attack techniques,
            indicating effective security controls in those areas.</p>
        </div>`;
    }

    // Recommendations
    const allRecs = layers.flatMap(l => (l.recommendations || []).map(r => ({ layer: l.layer, rec: r })));
    if (allRecs.length > 0) {
        html += '<h4 style="margin: 20px 0 12px; font-size: 15px;">Recommendations</h4>';
        allRecs.forEach(({ layer, rec }) => {
            const isHigh = rec.includes('HIGH');
            const isMod = rec.includes('MODERATE');
            html += `<div class="finding ${isHigh ? 'critical' : isMod ? 'moderate' : 'low'}">
                <h4>${esc(layer.toUpperCase())} Layer</h4>
                <p>${esc(rec)}</p>
            </div>`;
        });
    }

    // Comparability warnings
    if (DATA.report.comparability_warnings && DATA.report.comparability_warnings.length > 0) {
        html += '<h4 style="margin: 20px 0 12px; font-size: 15px;">Comparability Warnings</h4>';
        DATA.report.comparability_warnings.forEach(w => {
            html += `<div class="finding moderate"><p>${esc(w)}</p></div>`;
        });
    }

    html += '</div></div>';
    panel.innerHTML = html;
}

// ============================================================================
// ATTACK GRAPH (Vanilla JS Canvas Force-Directed)
// ============================================================================
let graphNodes = [];
let graphEdges = [];
let showLabels = true;
let physicsRunning = true;
let dragNode = null;
let panX = 0, panY = 0, scale = 1;
let lastMouse = null;

const SURFACE_COLORS = {
    guardrail: '#f0883e',
    model: '#58a6ff',
    data: '#bc8cff',
    retrieval: '#39d2c0',
    tool: '#f778ba',
    action: '#d29922'
};

function initGraph() {
    const canvas = document.getElementById('graph-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = 650;
    const W = canvas.width, H = canvas.height;

    // Build nodes from DATA
    const nodes = (DATA.graph?.nodes || []).map((n, i) => ({
        ...n,
        x: W/2 + (Math.random() - 0.5) * W * 0.6,
        y: H/2 + (Math.random() - 0.5) * H * 0.6,
        vx: 0, vy: 0,
        radius: 18 + (n.score || 0.3) * 12,
    }));

    const nodeMap = {};
    nodes.forEach(n => nodeMap[n.id] = n);

    const edges = (DATA.graph?.edges || []).filter(e =>
        nodeMap[e.source] && nodeMap[e.target]
    ).map(e => ({
        ...e,
        sourceNode: nodeMap[e.source],
        targetNode: nodeMap[e.target],
    }));

    graphNodes = nodes;
    graphEdges = edges;

    document.getElementById('graph-info').textContent = `${nodes.length} nodes, ${edges.length} edges`;

    // Deduplicate edges for cleaner layout
    const edgeSet = new Set();
    const uniqueEdges = edges.filter(e => {
        const key = [e.source, e.target].sort().join(':');
        if (edgeSet.has(key)) return false;
        edgeSet.add(key);
        return true;
    });

    // Force simulation
    function tick() {
        if (!physicsRunning) { draw(); requestAnimationFrame(tick); return; }
        const alpha = 0.3;

        // Center gravity
        nodes.forEach(n => {
            n.vx += (W/2 - n.x) * 0.001;
            n.vy += (H/2 - n.y) * 0.001;
        });

        // Repulsion (Barnes-Hut simplified)
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                let dx = nodes[j].x - nodes[i].x;
                let dy = nodes[j].y - nodes[i].y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                let force = 3000 / (dist * dist);
                let fx = dx / dist * force;
                let fy = dy / dist * force;
                nodes[i].vx -= fx; nodes[i].vy -= fy;
                nodes[j].vx += fx; nodes[j].vy += fy;
            }
        }

        // Attraction along edges
        uniqueEdges.forEach(e => {
            let dx = e.targetNode.x - e.sourceNode.x;
            let dy = e.targetNode.y - e.sourceNode.y;
            let dist = Math.sqrt(dx * dx + dy * dy) || 1;
            let force = (dist - 120) * 0.01;
            let fx = dx / dist * force;
            let fy = dy / dist * force;
            e.sourceNode.vx += fx; e.sourceNode.vy += fy;
            e.targetNode.vx -= fx; e.targetNode.vy -= fy;
        });

        // Layer clustering: group by surface vertically
        const surfaceOrder = ['guardrail', 'model', 'data', 'retrieval', 'tool', 'action'];
        nodes.forEach(n => {
            const idx = surfaceOrder.indexOf(n.surface || n.layer);
            if (idx >= 0) {
                const targetY = (idx + 1) / (surfaceOrder.length + 1) * H;
                n.vy += (targetY - n.y) * 0.005;
            }
        });

        // Apply velocity with damping
        nodes.forEach(n => {
            if (n === dragNode) return;
            n.vx *= 0.85; n.vy *= 0.85;
            n.x += n.vx * alpha;
            n.y += n.vy * alpha;
            n.x = Math.max(30, Math.min(W - 30, n.x));
            n.y = Math.max(30, Math.min(H - 30, n.y));
        });

        draw();
        requestAnimationFrame(tick);
    }

    function draw() {
        ctx.save();
        ctx.clearRect(0, 0, W, H);
        ctx.translate(panX, panY);
        ctx.scale(scale, scale);

        // Draw edges
        ctx.globalAlpha = 0.3;
        uniqueEdges.forEach(e => {
            ctx.beginPath();
            ctx.moveTo(e.sourceNode.x, e.sourceNode.y);
            ctx.lineTo(e.targetNode.x, e.targetNode.y);
            ctx.strokeStyle = '#bc8cff';
            ctx.lineWidth = 1;
            ctx.stroke();

            // Arrow
            const angle = Math.atan2(e.targetNode.y - e.sourceNode.y, e.targetNode.x - e.sourceNode.x);
            const r = e.targetNode.radius + 4;
            const ax = e.targetNode.x - Math.cos(angle) * r;
            const ay = e.targetNode.y - Math.sin(angle) * r;
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(ax - 8 * Math.cos(angle - 0.4), ay - 8 * Math.sin(angle - 0.4));
            ctx.lineTo(ax - 8 * Math.cos(angle + 0.4), ay - 8 * Math.sin(angle + 0.4));
            ctx.fillStyle = '#bc8cff';
            ctx.fill();
        });
        ctx.globalAlpha = 1;

        // Draw nodes
        nodes.forEach(n => {
            // Node circle
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);

            // Color by outcome
            if (n.success === true) ctx.fillStyle = '#3fb950';
            else if (n.success === false) ctx.fillStyle = '#f85149';
            else if (n.success === null) ctx.fillStyle = '#d29922';
            else ctx.fillStyle = '#6e7681';

            ctx.fill();

            // Surface ring
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius + 2, 0, Math.PI * 2);
            ctx.strokeStyle = SURFACE_COLORS[n.surface || n.layer] || '#555';
            ctx.lineWidth = 2.5;
            ctx.stroke();

            // Label
            if (showLabels) {
                ctx.font = '10px -apple-system, sans-serif';
                ctx.fillStyle = '#e6edf3';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                const label = n.label.length > 22 ? n.label.substring(0, 20) + '...' : n.label;
                ctx.fillText(label, n.x, n.y + n.radius + 5);
            }

            // Score inside node
            if (n.score != null) {
                ctx.font = 'bold 10px monospace';
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText((n.score * 100).toFixed(0), n.x, n.y);
            }
        });

        ctx.restore();
    }

    // Interaction
    canvas.addEventListener('mousedown', e => {
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX - rect.left - panX) / scale;
        const my = (e.clientY - rect.top - panY) / scale;
        dragNode = nodes.find(n => Math.hypot(n.x - mx, n.y - my) < n.radius + 4);
        lastMouse = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('mousemove', e => {
        const rect = canvas.getBoundingClientRect();
        if (dragNode) {
            dragNode.x = (e.clientX - rect.left - panX) / scale;
            dragNode.y = (e.clientY - rect.top - panY) / scale;
            dragNode.vx = 0; dragNode.vy = 0;
        } else if (lastMouse && e.buttons === 1) {
            panX += e.clientX - lastMouse.x;
            panY += e.clientY - lastMouse.y;
            lastMouse = { x: e.clientX, y: e.clientY };
        }
    });

    canvas.addEventListener('mouseup', () => { dragNode = null; lastMouse = null; });
    canvas.addEventListener('wheel', e => {
        e.preventDefault();
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        scale *= factor;
        scale = Math.max(0.3, Math.min(3, scale));
    });

    window._resetGraph = () => { panX = 0; panY = 0; scale = 1; };

    requestAnimationFrame(tick);
}

function resetGraph() { if (window._resetGraph) window._resetGraph(); }
function toggleLabels() { showLabels = !showLabels; }
function togglePhysics() { physicsRunning = !physicsRunning; }

// ============================================================================
// LAYER ANALYSIS
// ============================================================================
function renderLayers() {
    const grid = document.getElementById('layer-grid');
    const layers = DATA.layers || [];

    grid.innerHTML = layers.map(l => {
        const isPrimary = l.is_primary_weakness;
        const rColor = riskColor(l.risk_score);
        const recs = (l.recommendations || []).map(r => {
            const cls = r.includes('HIGH') ? 'high' : r.includes('MODERATE') ? 'moderate' : '';
            return `<li class="${cls}">${esc(r)}</li>`;
        }).join('');

        return `<div class="layer-card${isPrimary ? ' primary' : ''}">
            <div class="layer-name">
                ${esc(l.layer.toUpperCase())}
                ${isPrimary ? '<span class="primary-badge">Primary Weakness</span>' : ''}
            </div>
            <div class="layer-stats">
                <div class="layer-stat">
                    <div class="stat-label">Risk Score</div>
                    <div class="stat-value" style="color:${rColor}">${pct(l.risk_score)}</div>
                </div>
                <div class="layer-stat">
                    <div class="stat-label">Success Rate</div>
                    <div class="stat-value">${pct(l.success_rate)}</div>
                </div>
                <div class="layer-stat">
                    <div class="stat-label">Techniques</div>
                    <div class="stat-value">${l.techniques_tested}</div>
                </div>
                <div class="layer-stat">
                    <div class="stat-label">Confidence</div>
                    <div class="stat-value" style="font-size:13px">[${l.confidence_interval[0].toFixed(2)}, ${l.confidence_interval[1].toFixed(2)}]</div>
                </div>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:${l.risk_score * 100}%;background:${rColor}"></div></div>
            ${l.evidence_quality != null ? `<div style="font-size:12px;color:var(--text-muted)">Evidence quality: ${pct(l.evidence_quality)}</div>` : ''}
            ${recs ? `<ul class="rec-list">${recs}</ul>` : ''}
        </div>`;
    }).join('');
}

// ============================================================================
// RISK HEATMAP
// ============================================================================
function renderHeatmap() {
    const body = document.getElementById('heatmap-body');
    const heatmap = DATA.heatmap;
    if (!heatmap || !heatmap.surfaces || !heatmap.goals) {
        body.innerHTML = '<p style="color:var(--text-muted);padding:20px">No heatmap data available.</p>';
        return;
    }

    const surfaces = heatmap.surfaces;
    const goals = heatmap.goals;
    const matrix = heatmap.matrix; // surface -> goal -> { rate, count }

    let html = '<table class="heatmap-table"><thead><tr><th></th>';
    goals.forEach(g => { html += `<th>${esc(g)}</th>`; });
    html += '<th>Overall</th></tr></thead><tbody>';

    surfaces.forEach(s => {
        html += `<tr><td class="row-header">${esc(s)}</td>`;
        let sTotal = 0, sSuccess = 0;
        goals.forEach(g => {
            const cell = (matrix[s] && matrix[s][g]) || { rate: -1, count: 0, successes: 0 };
            if (cell.count > 0) {
                const intensity = cell.rate;
                const bg = intensity >= 0.5
                    ? `rgba(248,81,73,${0.2 + intensity * 0.6})`
                    : intensity > 0
                    ? `rgba(210,153,34,${0.2 + intensity * 0.4})`
                    : 'rgba(63,185,80,0.15)';
                html += `<td style="background:${bg}">${pct(cell.rate)}<br><span style="font-size:10px;color:var(--text-muted)">(${cell.successes}/${cell.count})</span></td>`;
                sTotal += cell.count; sSuccess += cell.successes;
            } else {
                html += `<td style="color:var(--text-muted)">-</td>`;
            }
        });
        // Row total
        if (sTotal > 0) {
            const rate = sSuccess / sTotal;
            const bg = rate >= 0.5 ? `rgba(248,81,73,${0.2 + rate * 0.6})` : rate > 0 ? `rgba(210,153,34,${0.2 + rate * 0.4})` : 'rgba(63,185,80,0.15)';
            html += `<td style="background:${bg};font-weight:700">${pct(rate)}</td>`;
        } else {
            html += `<td style="color:var(--text-muted)">-</td>`;
        }
        html += '</tr>';
    });

    html += '</tbody></table>';
    body.innerHTML = html;
}

// ============================================================================
// TECHNIQUE DETAILS TABLE
// ============================================================================
function renderTechniques() {
    const techs = DATA.techniques || [];
    document.getElementById('tech-count').textContent = `${techs.length} techniques`;

    const thead = document.querySelector('#tech-table thead');
    const tbody = document.querySelector('#tech-table tbody');

    thead.innerHTML = '<tr><th>ID</th><th>Name</th><th>Domain</th><th>Surface</th><th>Phase</th><th>Outcome</th><th>Score</th><th>ATLAS</th><th>Access</th><th>Cost</th></tr>';

    tbody.innerHTML = techs.sort((a, b) => (b.score || 0) - (a.score || 0)).map(t => {
        const scorePct = ((t.score || 0) * 100).toFixed(0);
        const scoreColor = t.success === true ? 'var(--success)' : t.success === false ? 'var(--danger)' : 'var(--warning)';
        const atlas = (t.atlas_refs || []).map(r => `<span class="badge badge-info">${esc(r)}</span>`).join(' ');

        return `<tr>
            <td><code style="font-size:11px;color:var(--cyan)">${esc(t.id)}</code></td>
            <td>${esc(t.name)}</td>
            <td><span class="badge badge-neutral">${esc(t.domain)}</span></td>
            <td><span class="badge badge-neutral">${esc(t.surface)}</span></td>
            <td><span class="badge badge-neutral">${esc(t.phase || '')}</span></td>
            <td><span class="badge ${outcomeClass(t.success)}">${outcomeText(t.success)}</span></td>
            <td>${scorePct}<span class="score-bar"><span class="score-fill" style="width:${scorePct}%;background:${scoreColor}"></span></span></td>
            <td>${atlas || '-'}</td>
            <td><span class="badge badge-neutral">${esc(t.access_required || '')}</span></td>
            <td>${t.base_cost != null ? t.base_cost.toFixed(2) : '-'}</td>
        </tr>`;
    }).join('');
}

// ============================================================================
// ATLAS MAPPING
// ============================================================================
function renderAtlas() {
    const grid = document.getElementById('atlas-grid');
    const atlasMap = DATA.atlas_mapping || {};

    if (Object.keys(atlasMap).length === 0) {
        grid.innerHTML = '<p style="color:var(--text-muted)">No ATLAS mappings available.</p>';
        return;
    }

    grid.innerHTML = Object.entries(atlasMap).sort(([a], [b]) => a.localeCompare(b)).map(([atlasId, info]) => {
        const tags = (info.techniques || []).map(t => {
            const cls = t.success === true ? 'badge-success' : t.success === false ? 'badge-danger' : 'badge-neutral';
            return `<span class="badge ${cls}" style="margin:2px">${esc(t.name || t.id)}</span>`;
        }).join('');

        return `<div class="atlas-card">
            <div class="atlas-id">${esc(atlasId)}</div>
            <div class="atlas-name">${esc(info.name || '')}</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">${esc(info.tactic || '')}</div>
            <div class="atlas-techniques">${tags}</div>
        </div>`;
    }).join('');
}

// ============================================================================
// STATISTICS
// ============================================================================
function renderStatistics() {
    const grid = document.getElementById('stats-grid');
    const s = DATA.statistics || {};

    const panels = [];

    // Campaign Overview
    if (s.campaign_overview) {
        panels.push({ title: 'Campaign Overview', rows: Object.entries(s.campaign_overview) });
    }

    // Per-Domain Stats
    if (s.per_domain) {
        Object.entries(s.per_domain).forEach(([domain, stats]) => {
            panels.push({ title: `${domain.toUpperCase()} Domain`, rows: Object.entries(stats) });
        });
    }

    // Per-Surface Stats
    if (s.per_surface) {
        Object.entries(s.per_surface).forEach(([surface, stats]) => {
            panels.push({ title: `${surface.charAt(0).toUpperCase() + surface.slice(1)} Surface`, rows: Object.entries(stats) });
        });
    }

    // Per-Phase Stats
    if (s.per_phase) {
        panels.push({ title: 'By Attack Phase', rows: Object.entries(s.per_phase).map(([phase, stats]) =>
            [phase, `${stats.success || 0}/${stats.total || 0} (${pct(stats.rate || 0)})`]
        )});
    }

    // Coverage
    if (s.coverage) {
        panels.push({ title: 'Coverage Analysis', rows: Object.entries(s.coverage) });
    }

    // Adaptive Planning
    if (s.adaptive) {
        panels.push({ title: 'Adaptive Planning', rows: Object.entries(s.adaptive) });
    }

    // Fallback: raw statistics
    if (panels.length === 0 && Object.keys(s).length > 0) {
        panels.push({ title: 'Statistics', rows: Object.entries(s).filter(([k]) =>
            typeof s[k] !== 'object'
        ).map(([k, v]) => [k.replace(/_/g, ' '), String(v)]) });
    }

    grid.innerHTML = panels.map(p =>
        `<div class="stat-panel"><h4>${esc(p.title)}</h4>` +
        p.rows.map(([k, v]) =>
            `<div class="stat-row"><span class="stat-key">${esc(String(k).replace(/_/g, ' '))}</span><span>${esc(String(v))}</span></div>`
        ).join('') +
        '</div>'
    ).join('');

    // Sensitivity Analysis
    const sens = DATA.sensitivity;
    if (sens && sens.weights && sens.weights.length > 0) {
        const sensPanel = document.createElement('div');
        sensPanel.className = 'stat-panel';
        sensPanel.style.gridColumn = '1 / -1';
        let sensHtml = '<h4>Sensitivity Analysis</h4>';
        sensHtml += '<p style="color:var(--text-secondary);margin-bottom:12px">Weight perturbation \u00b1' + ((sens.perturbation_pct || 0.2) * 100).toFixed(0) + '% (' + (sens.num_samples || 50) + ' samples). Higher rank correlation = more stable ranking.</p>';
        sensHtml += '<table class="data-table"><thead><tr><th>Weight</th><th>Rank Correlation (\u03c4)</th><th>Top-K Stability</th><th>Displaced Techniques</th></tr></thead><tbody>';
        sens.weights.forEach(w => {
            const tauColor = w.rank_correlation >= 0.9 ? 'var(--success)' : w.rank_correlation >= 0.7 ? 'var(--warning)' : 'var(--danger)';
            const isMost = w.name === sens.most_sensitive ? ' \u26a0\ufe0f Most Sensitive' : '';
            const isLeast = w.name === sens.least_sensitive ? ' \u2714 Most Stable' : '';
            sensHtml += '<tr><td><strong>' + esc(w.name.replace(/_/g, ' ')) + '</strong>' + isMost + isLeast + '</td>';
            sensHtml += '<td style="color:' + tauColor + ';font-weight:700">' + w.rank_correlation.toFixed(3) + '</td>';
            sensHtml += '<td>' + (w.top_k_stability * 100).toFixed(1) + '%</td>';
            sensHtml += '<td style="font-size:12px">' + (w.displaced || []).join(', ') + '</td></tr>';
        });
        sensHtml += '</tbody></table>';
        sensPanel.innerHTML = sensHtml;
        grid.appendChild(sensPanel);
    }
}

// ============================================================================
// BELIEF EVOLUTION
// ============================================================================
function renderBeliefs() {
    const panel = document.getElementById('beliefs-panel');
    const history = DATA.posterior_evolution;
    if (!history || !history.length) {
        panel.innerHTML = '<div class="panel"><div class="panel-header"><h3>Belief Evolution</h3></div><p style="padding:16px;color:var(--text-secondary)">No posterior evolution data available. Run an adaptive campaign to see belief changes over time.</p></div>';
        return;
    }
    let html = '<div class="panel"><div class="panel-header"><h3>Posterior Belief Evolution</h3><span style="font-size:14px;color:var(--text-muted)">' + history.length + ' snapshots</span></div>';

    // Collect all technique IDs across history
    const allTechIds = new Set();
    history.forEach(snap => {
        Object.keys(snap.posteriors || {}).forEach(tid => allTechIds.add(tid));
    });

    // Build table: rows = steps, columns = techniques
    const techIds = Array.from(allTechIds).slice(0, 15); // Limit to 15 for readability
    html += '<div style="overflow-x:auto;padding:0 16px 16px"><table class="data-table"><thead><tr><th>Step</th><th>Phase</th>';
    techIds.forEach(tid => {
        const shortId = tid.split('-').slice(-2).join('-');
        html += '<th style="font-size:11px;max-width:80px;overflow:hidden;text-overflow:ellipsis" title="' + esc(tid) + '">' + esc(shortId) + '</th>';
    });
    html += '</tr></thead><tbody>';

    history.forEach(snap => {
        html += '<tr><td>' + (snap.step || 0) + '</td><td>' + esc(snap.phase || '') + '</td>';
        techIds.forEach(tid => {
            const post = (snap.posteriors || {})[tid];
            if (post) {
                const mean = (post.mean || 0);
                const color = mean >= 0.6 ? 'var(--danger)' : mean >= 0.3 ? 'var(--warning)' : 'var(--success)';
                html += '<td style="color:' + color + ';font-weight:600;font-size:12px">' + mean.toFixed(2) + '</td>';
            } else {
                html += '<td style="color:var(--text-muted);font-size:12px">-</td>';
            }
        });
        html += '</tr>';
    });

    html += '</tbody></table></div>';

    // Canvas chart
    html += '<div style="padding:16px"><canvas id="beliefs-chart" width="800" height="300" style="width:100%;max-height:300px;background:var(--bg-secondary);border-radius:8px"></canvas></div>';
    html += '</div>';
    panel.innerHTML = html;

    // Draw simple line chart on canvas
    const canvas = document.getElementById('beliefs-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const pad = {top: 20, right: 20, bottom: 30, left: 40};
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;
    const steps = history.length;

    // Colors for different techniques
    const colors = ['#3b82f6','#ef4444','#22c55e','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#84cc16','#f97316','#6366f1'];

    // Draw axes
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, pad.top);
    ctx.lineTo(pad.left, h - pad.bottom);
    ctx.lineTo(w - pad.right, h - pad.bottom);
    ctx.stroke();

    // Y-axis labels
    ctx.fillStyle = '#999';
    ctx.font = '10px monospace';
    ctx.textAlign = 'right';
    [0, 0.25, 0.5, 0.75, 1.0].forEach(v => {
        const y = pad.top + plotH * (1 - v);
        ctx.fillText(v.toFixed(2), pad.left - 4, y + 3);
        ctx.strokeStyle = '#333';
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();
    });

    // Draw lines for each technique
    techIds.slice(0, 10).forEach((tid, idx) => {
        ctx.strokeStyle = colors[idx % colors.length];
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        let started = false;
        history.forEach((snap, si) => {
            const post = (snap.posteriors || {})[tid];
            if (post && post.mean !== undefined) {
                const x = pad.left + (si / Math.max(steps - 1, 1)) * plotW;
                const y = pad.top + plotH * (1 - post.mean);
                if (!started) { ctx.moveTo(x, y); started = true; }
                else ctx.lineTo(x, y);
            }
        });
        ctx.stroke();
    });
}

// ============================================================================
// COMPLIANCE
// ============================================================================
function renderCompliance() {
    const panel = document.getElementById('compliance-panel');
    const summaries = DATA.compliance || [];
    if (!summaries.length) {
        panel.innerHTML = '<div class="panel"><div class="panel-header"><h3>Compliance Frameworks</h3></div><p style="padding:16px;color:var(--text-secondary)">No compliance data available. Add compliance_refs to techniques in catalog.</p></div>';
        return;
    }
    let html = '';
    summaries.forEach(fw => {
        const pct = (fw.coverage_pct * 100).toFixed(0);
        const color = pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--warning)' : 'var(--danger)';
        html += '<div class="panel"><div class="panel-header"><h3>' + esc(fw.framework_name || fw.framework) + '</h3><span style="font-size:14px;color:' + color + ';font-weight:700">' + fw.tested_controls + '/' + fw.total_controls + ' controls tested (' + pct + '%)</span></div>';
        // Progress bar
        html += '<div style="background:var(--bg-tertiary);border-radius:4px;height:8px;margin:0 16px 16px"><div style="background:' + color + ';height:100%;border-radius:4px;width:' + pct + '%;transition:width 0.3s"></div></div>';
        // Control table
        html += '<table class="data-table"><thead><tr><th>Control</th><th>Name</th><th>Techniques Mapped</th><th>Tested</th><th>Risk</th></tr></thead><tbody>';
        (fw.control_results || []).forEach(c => {
            const badge = c.risk_level === 'high' ? 'background:var(--danger)' : c.risk_level === 'moderate' ? 'background:var(--warning)' : c.risk_level === 'low' ? 'background:var(--success)' : 'background:var(--text-muted)';
            html += '<tr><td><strong>' + esc(c.control_id) + '</strong></td><td>' + esc(c.control_name) + '</td><td>' + (c.techniques_mapped || []).length + '</td><td>' + (c.techniques_tested || []).length + '</td><td><span class="badge" style="' + badge + '">' + esc(c.risk_level) + '</span></td></tr>';
        });
        html += '</tbody></table></div>';
    });
    panel.innerHTML = html;
}

// ============================================================================
// RAW DATA
// ============================================================================
function renderRawData() {
    document.getElementById('raw-data').textContent = JSON.stringify(DATA, null, 2);
}

// ============================================================================
// TAB SWITCHING
// ============================================================================
let graphInitialized = false;
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        this.classList.add('active');
        const panel = document.getElementById(this.dataset.tab + '-panel');
        if (panel) panel.classList.add('active');

        if (this.dataset.tab === 'graph' && !graphInitialized) {
            graphInitialized = true;
            setTimeout(initGraph, 50);
        }
        if (this.dataset.tab === 'rawdata') renderRawData();
    });
});

// ============================================================================
// INITIALIZE
// ============================================================================
renderHeader();
renderSummary();
renderExecutive();
renderLayers();
renderHeatmap();
renderTechniques();
renderAtlas();
renderStatistics();
renderCompliance();
renderBeliefs();
</script>
</body>
</html>"""
