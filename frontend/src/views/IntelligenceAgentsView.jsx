import React from 'react';
import { Bot, Layers, Database, ShieldCheck, Cpu, ArrowRight, CheckCircle2, Sliders, FileText } from 'lucide-react';

export default function IntelligenceAgentsView() {
  const agents = [
    {
      id: 'ag_planner',
      name: 'Planner & Intent Classifier',
      framework: 'LangGraph StateGraph / Deterministic Rule Classifier',
      status: 'ACTIVE LOCAL',
      latency: '24 ms',
      description: 'Parses engineering inquiry intent (ROOT_CAUSE_FAILURE_ANALYSIS, TELEMETRY_QUERY, PROCEDURE_LOOKUP, COMPARISON) and dispatches sub-tasks.',
      tools: ['Query Classifier', 'Workspace Router']
    },
    {
      id: 'ag_rag',
      name: 'Permission-Aware RAG Agent',
      framework: 'ChromaDB Local Collection + SentenceTransformers',
      status: 'ACTIVE LOCAL',
      latency: '45 ms',
      description: 'Executes RBAC-filtered semantic chunk retrieval across equipment manuals, P&IDs, and inspection reports.',
      tools: ['ChromaDB Store', 'RBAC Filter']
    },
    {
      id: 'ag_telemetry',
      name: 'DuckDB Sensor Telemetry Agent',
      framework: 'DuckDB In-Memory Analytical Engine',
      status: 'ACTIVE LOCAL',
      latency: '14 ms',
      description: 'Analyzes high-frequency vibration, temperature, and pressure sensor time-series tables under AST injection protection.',
      tools: ['DuckDB SQL AST Guard', 'CSV Table Aggregator']
    },
    {
      id: 'ag_vision',
      name: 'P&ID Vision & Diagram OCR Agent',
      framework: 'Tesseract v5 + PyMuPDF Dual-Engine',
      status: 'ACTIVE LOCAL',
      latency: '110 ms',
      description: 'Extracts equipment tag identifiers, line flows, valve positions, and tabular matrices from scanned sheets and drawings.',
      tools: ['PyMuPDF', 'Tesseract OCR', 'Deskew Filter']
    },
    {
      id: 'ag_verifier',
      name: 'Hallucination Firewall & Causal Verifier',
      framework: 'Claim NLI + Causal Leap Guardrail',
      status: 'ACTIVE LOCAL',
      latency: '32 ms',
      description: 'Validates that every claim is citation-grounded and applies causal hedging to prevent speculative root-cause leaps.',
      tools: ['Evidence Grounding Checker', 'Causal Leap Downgrader']
    },
    {
      id: 'ag_docx',
      name: 'MRPL Executive Approval Note Generator',
      framework: 'Python-docx Sovereign Formatter',
      status: 'ACTIVE LOCAL',
      latency: '18 ms',
      description: 'Compiles verified findings, evidence snippets, and mitigation actions into standard corporate executive Word DOCX notes.',
      tools: ['ApprovalNoteGenerator', 'DOCX Styler']
    }
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-mono font-bold tracking-widest text-[#6d675e] uppercase">
            INTELLIGENCE • MULTI-AGENT ORCHESTRATION
          </span>
          <h1 className="text-xl font-display font-bold text-[#f5f2ed]">
            Specialized Multi-Agent Spine
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="status-pill-sage">
            <Bot size={12} />
            <span>06 Sub-Agents Configured</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Agent Cards Grid */}
        <div className="lg:col-span-8 space-y-3">
          {agents.map((ag) => (
            <div key={ag.id} className="clora-card p-4.5 space-y-3 border border-[#2e2a25]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[#201d1a] border border-[#3b3630] flex items-center justify-center text-[#d9825b]">
                    <Bot size={16} />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-[#f5f2ed]">{ag.name}</h3>
                    <span className="text-[10px] text-[#6d675e] font-mono">{ag.framework}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="status-pill-sage">{ag.status}</span>
                  <span className="text-[10px] font-mono text-[#a09a90]">{ag.latency}</span>
                </div>
              </div>

              <p className="text-xs text-[#a09a90] leading-relaxed">
                {ag.description}
              </p>

              <div className="flex items-center gap-2 pt-1.5 border-t border-[#26231f] flex-wrap">
                <span className="text-[10px] text-[#6d675e] font-mono">Bound Tools:</span>
                {ag.tools.map((t, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-[#181614] border border-[#2b2723] text-[10px] text-[#c8c2b8] font-mono">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Right: Active Tool Connections */}
        <div className="lg:col-span-4 space-y-4">
          <div className="clora-card p-4.5 space-y-3.5 border border-[#2e2a25]">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2">
              <span className="text-xs font-semibold text-[#f5f2ed] uppercase tracking-wide">
                Active Tool Runtimes
              </span>
              <Sliders size={13} className="text-[#d9825b]" />
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#161412] border border-[#2b2723] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database size={14} className="text-[#10b981]" />
                  <span className="font-medium text-[#f5f2ed]">DuckDB In-Memory</span>
                </div>
                <span className="status-pill-emerald text-[9px]">READ-ONLY</span>
              </div>

              <div className="p-3 rounded-lg bg-[#161412] border border-[#2b2723] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Layers size={14} className="text-[#38bdf8]" />
                  <span className="font-medium text-[#f5f2ed]">ChromaDB Vector Store</span>
                </div>
                <span className="status-pill-sage text-[9px]">ACTIVE</span>
              </div>

              <div className="p-3 rounded-lg bg-[#161412] border border-[#2b2723] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText size={14} className="text-[#d9825b]" />
                  <span className="font-medium text-[#f5f2ed]">Word DOCX Formatter</span>
                </div>
                <span className="status-pill-copper text-[9px]">SOP-TEMPLATE</span>
              </div>

              <div className="p-3 rounded-lg bg-[#161412] border border-[#2b2723] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={14} className="text-[#10b981]" />
                  <span className="font-medium text-[#f5f2ed]">Ed25519 Attestor</span>
                </div>
                <span className="status-pill-emerald text-[9px]">SIGNING ON</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
