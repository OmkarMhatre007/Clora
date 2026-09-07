import React, { useState, useEffect } from 'react';
import {
  Network,
  FileText,
  ShieldCheck,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize2,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  Wrench,
  Package,
  Clock,
  Zap
} from 'lucide-react';
import {
  getKnowledgeGraphCytoscape,
  getBlastRadius,
  getSovereigntyAuditTrail
} from '../services/api';

export default function KnowledgeGraphView() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedNodeId, setSelectedNodeId] = useState('P-102A');
  const [blastRadiusResult, setBlastRadiusResult] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [calculatingBlast, setCalculatingBlast] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);

  // Layout node positions dynamically
  const [layoutNodes, setLayoutNodes] = useState([]);

  useEffect(() => {
    const loadGraph = async () => {
      setLoading(true);
      try {
        const [cytoscape, auditData] = await Promise.all([
          getKnowledgeGraphCytoscape(),
          getSovereigntyAuditTrail(6)
        ]);

        if (cytoscape && cytoscape.elements) {
          const rawNodes = cytoscape.elements.nodes || [];
          const rawEdges = cytoscape.elements.edges || [];
          setGraphData({ nodes: rawNodes, edges: rawEdges });

          // Compute deterministic visual 2D layout for nodes
          const total = rawNodes.length || 1;
          const cols = 4;
          const positioned = rawNodes.map((n, i) => {
            const row = Math.floor(i / cols);
            const col = i % cols;
            const x = 70 + col * 120 + (row % 2 === 1 ? 30 : 0);
            const y = 60 + row * 85;
            return {
              id: n.data.id,
              name: n.data.label || n.data.id,
              type: n.data.type || 'Asset',
              critical: n.data.id.includes('P-102A') || n.data.id.includes('FM-'),
              x: x,
              y: y,
              radius: n.data.id.includes('P-102A') ? 28 : 22
            };
          });
          setLayoutNodes(positioned);
        }

        if (auditData && auditData.entries) {
          setAuditEvents(auditData.entries);
        }
      } catch (err) {
        console.warn('Failed loading knowledge graph:', err);
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
  }, []);

  // Fetch live blast-radius when node changes
  useEffect(() => {
    if (!selectedNodeId) return;

    const fetchRadius = async () => {
      setCalculatingBlast(true);
      try {
        const res = await getBlastRadius(selectedNodeId, 2);
        if (res) {
          setBlastRadiusResult(res);
        }
      } catch (err) {
        console.warn('Failed calculating blast radius:', err);
      } finally {
        setCalculatingBlast(false);
      }
    };

    fetchRadius();
  }, [selectedNodeId]);

  const activeNodeData = layoutNodes.find(n => n.id === selectedNodeId) || layoutNodes[0] || { id: selectedNodeId, name: selectedNodeId, type: 'Equipment' };

  return (
    <div className="space-y-5">
      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-mono font-bold tracking-widest text-[#6d675e] uppercase">
            KNOWLEDGE • NETWORKX TOPOLOGY REASONING
          </span>
          <h1 className="text-xl font-display font-bold text-[#f5f2ed]">
            Refinery Asset Topology & Blast-Radius Engine
          </h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="status-pill-sage">
            <Activity size={12} />
            <span>NetworkX Graph Active</span>
          </span>
          <span className="status-pill-copper">
            <span>Blast Radius: Live</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Interactive Topology Canvas */}
        <div className="lg:col-span-7 clora-card p-5 space-y-3 flex flex-col justify-between border border-[#2e2a25]">
          <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2.5">
            <span className="text-xs font-semibold text-[#f5f2ed] uppercase tracking-wide">
              Topology Canvas ({layoutNodes.length} Nodes, {graphData.edges.length} Edges)
            </span>
            <div className="flex items-center gap-1.5 text-[#6d675e]">
              <button
                onClick={() => setZoomLevel(prev => Math.min(prev + 0.15, 1.6))}
                className="p-1 rounded hover:bg-[#26231f] text-[#a09a90]"
                title="Zoom In"
              >
                <ZoomIn size={14} />
              </button>
              <button
                onClick={() => setZoomLevel(prev => Math.max(prev - 0.15, 0.7))}
                className="p-1 rounded hover:bg-[#26231f] text-[#a09a90]"
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <button
                onClick={() => setZoomLevel(1)}
                className="p-1 rounded hover:bg-[#26231f] text-[#a09a90]"
                title="Reset Zoom"
              >
                <Maximize2 size={14} />
              </button>
            </div>
          </div>

          {/* SVG Canvas */}
          <div className="w-full h-[360px] bg-[#141211] rounded-xl border border-[#2c2823] relative flex items-center justify-center overflow-hidden">
            {/* Blast Radius Glowing Halo on Selected Node */}
            {selectedNodeId && (
              <div className="absolute top-4 left-4 bg-[#1e1c19]/90 border border-[#3d3832] rounded-lg px-2.5 py-1 text-[10px] text-[#f0a380] flex items-center gap-1.5 font-mono z-10">
                <span className="w-1.5 h-1.5 rounded-full bg-[#d9825b] animate-ping" />
                <span>Blast-Radius Engine: {selectedNodeId}</span>
              </div>
            )}

            <svg
              className="w-full h-full cursor-grab active:cursor-grabbing transition-transform duration-200"
              viewBox="0 0 520 340"
              style={{ transform: `scale(${zoomLevel})` }}
            >
              {/* Render Connection Edges */}
              {graphData.edges.map((edge, idx) => {
                const sourceNode = layoutNodes.find(n => n.id === edge.data.source);
                const targetNode = layoutNodes.find(n => n.id === edge.data.target);
                if (!sourceNode || !targetNode) return null;

                const isConnectedToSelected = edge.data.source === selectedNodeId || edge.data.target === selectedNodeId;

                return (
                  <g key={`edge_${idx}`}>
                    <line
                      x1={sourceNode.x}
                      y1={sourceNode.y}
                      x2={targetNode.x}
                      y2={targetNode.y}
                      stroke={isConnectedToSelected ? '#d9825b' : '#3d3730'}
                      strokeWidth={isConnectedToSelected ? '2' : '1.2'}
                      strokeDasharray={edge.data.relation === 'STANDBY_FOR' ? '4 4' : 'none'}
                    />
                  </g>
                );
              })}

              {/* Render Asset Nodes */}
              {layoutNodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isCritical = node.critical || node.id.includes('P-102A');
                const isStandby = node.id.includes('P-102B') || node.id.includes('P-101B');

                return (
                  <g
                    key={node.id}
                    onClick={() => setSelectedNodeId(node.id)}
                    className="cursor-pointer transition-all hover:scale-110"
                  >
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.radius}
                      fill="#1a1715"
                      stroke={isSelected ? '#d9825b' : isCritical ? '#f43f5e' : isStandby ? '#38bdf8' : '#6e8c6e'}
                      strokeWidth={isSelected ? '3' : '1.8'}
                      filter="drop-shadow(0 4px 8px rgba(0,0,0,0.6))"
                    />
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.radius - 5}
                      fill={isCritical ? 'rgba(244, 63, 94, 0.12)' : isSelected ? 'rgba(217, 130, 91, 0.15)' : 'rgba(110, 140, 110, 0.08)'}
                    />
                    <text
                      x={node.x}
                      y={node.y + 4}
                      textAnchor="middle"
                      fill="#f5f2ed"
                      fontSize="9.5"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      {node.id}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Selected Node Details Bar */}
          <div className="clora-surface p-3 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <span className="font-bold text-[#f5f2ed]">{activeNodeData.name || selectedNodeId}</span>
              <span className="text-[#6d675e]">•</span>
              <span className="text-[#a09a90]">{activeNodeData.type || 'Refinery Equipment'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[#d9825b] font-mono text-[11px]">
                {calculatingBlast ? 'Computing downstream impact...' : 'Downstream Path Mapped'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Live Blast Radius & Mitigation Plan */}
        <div className="lg:col-span-5 space-y-4">
          {/* Blast Radius Box */}
          <div className="clora-card p-4.5 space-y-3.5 border border-[#2e2a25]">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#f5f2ed]">
                <AlertTriangle size={14} className="text-[#d9825b]" />
                <span>Blast-Radius & Failure Cascade ({selectedNodeId})</span>
              </div>
              <span className="status-pill-copper text-[10px]">
                {blastRadiusResult?.blast_radius?.length || 0} Assets Affected
              </span>
            </div>

            {/* Affected Nodes List */}
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {blastRadiusResult?.blast_radius && blastRadiusResult.blast_radius.length > 0 ? (
                blastRadiusResult.blast_radius.map((br, idx) => (
                  <div
                    key={idx}
                    className="p-2 rounded-lg bg-[#181614] border border-[#2b2723] flex items-center justify-between text-xs font-mono"
                  >
                    <div className="space-y-0.5">
                      <div className="text-[#f5f2ed] font-bold">{br.node_id} ({br.entity_type})</div>
                      <div className="text-[10px] text-[#6d675e]">{br.name}</div>
                    </div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#291f19] text-[#d9825b] font-bold">
                      {br.hops} {br.hops === 1 ? 'hop' : 'hops'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="py-4 text-center text-[#6d675e] text-xs font-mono">
                  No downstream failure cascade for {selectedNodeId}
                </div>
              )}
            </div>

            {/* Standby Asset Available */}
            {blastRadiusResult?.standby_available && (
              <div className="p-2.5 rounded-lg bg-[#142319] border border-[#1f5433] flex items-center justify-between text-xs">
                <div className="space-y-0.5">
                  <div className="text-[#34d399] font-bold flex items-center gap-1.5">
                    <CheckCircle2 size={13} />
                    <span>Auto-Standby: {blastRadiusResult.standby_available.standby_id}</span>
                  </div>
                  <div className="text-[10px] text-[#8ca68c]">
                    {blastRadiusResult.standby_available.name}
                  </div>
                </div>
                <span className="status-pill-emerald text-[9px]">ONLINE READY</span>
              </div>
            )}
          </div>

          {/* Mitigation Plan & Parts Stock */}
          {blastRadiusResult?.mitigation_plan && (
            <div className="clora-card p-4.5 space-y-3 border border-[#2e2a25]">
              <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#f5f2ed]">
                  <Wrench size={14} className="text-[#38bdf8]" />
                  <span>SOP Mitigation & Inventory Parts</span>
                </div>
                <span className="text-[10px] text-[#38bdf8] font-mono">
                  Downtime: {blastRadiusResult.mitigation_plan.mitigations?.[0]?.downtime_hours || 18}h
                </span>
              </div>

              {/* Mitigation Cost & Procedure */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-[#181614] border border-[#2e2a25]">
                  <div className="text-[9px] text-[#6d675e]">PROCEDURE</div>
                  <div className="text-[#f5f2ed] font-bold truncate">
                    {blastRadiusResult.mitigation_plan.mitigations?.[0]?.procedure || 'SOP-CDU-SEC-014'}
                  </div>
                </div>
                <div className="p-2 rounded bg-[#181614] border border-[#2e2a25]">
                  <div className="text-[9px] text-[#6d675e]">EST. OVERHAUL COST</div>
                  <div className="text-[#d9825b] font-bold">
                    ₹{blastRadiusResult.mitigation_plan.mitigations?.[0]?.cost_inr?.toLocaleString() || '285,000'}
                  </div>
                </div>
              </div>

              {/* Parts Stock Availability */}
              <div className="space-y-1.5 pt-1">
                <div className="text-[10px] font-mono text-[#6d675e] uppercase">Required Spare Parts:</div>
                {(blastRadiusResult.mitigation_plan.required_parts || []).map((part, i) => (
                  <div key={i} className="p-2 rounded bg-[#181614] border border-[#2b2723] flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Package size={13} className="text-[#d9825b]" />
                      <span className="text-[#cbd5e1] font-mono text-[11px]">{part.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-[#10b981] font-bold">
                      {part.stock_available} in stock
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
