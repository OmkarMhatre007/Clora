import React from 'react';
import { Cpu, Bot, BookOpen, Wrench, ShieldCheck, ArrowUpRight } from 'lucide-react';

export default function LocalIntelligenceCard({
  filesCount = 4,
  activeModel = 'llama3.2:3b',
  onNavigate
}) {
  return (
    <div className="clora-card p-4.5 space-y-4 shadow-xl border border-[#2e2a25]">
      <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2">
        <span className="text-[11px] font-mono uppercase tracking-widest text-[#6d675e] font-bold">
          SOVEREIGN COMPUTE PROFILE
        </span>
        <span className="text-[10px] text-[#8ca68c] font-mono flex items-center gap-1">
          <ShieldCheck size={11} className="text-[#10b981]" />
          <span>100% On-Premise</span>
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <button
          onClick={() => onNavigate && onNavigate('intelligence-models')}
          className="clora-surface p-2.5 space-y-1 text-left hover:border-[#d9825b] transition-all group"
        >
          <div className="flex items-center justify-between text-[11px] text-[#a09a90]">
            <div className="flex items-center gap-1.5">
              <Cpu size={13} className="text-[#d9825b]" />
              <span>Active Model</span>
            </div>
            <ArrowUpRight size={11} className="text-[#6d675e] group-hover:text-[#d9825b] transition-colors" />
          </div>
          <div className="text-sm font-display font-bold text-[#f5f2ed] truncate">{activeModel}</div>
          <div className="text-[10px] text-[#6d675e]">Quantized 1B-4B Local</div>
        </button>

        <button
          onClick={() => onNavigate && onNavigate('intelligence-agents')}
          className="clora-surface p-2.5 space-y-1 text-left hover:border-[#6e8c6e] transition-all group"
        >
          <div className="flex items-center justify-between text-[11px] text-[#a09a90]">
            <div className="flex items-center gap-1.5">
              <Bot size={13} className="text-[#6e8c6e]" />
              <span>Agents</span>
            </div>
            <ArrowUpRight size={11} className="text-[#6d675e] group-hover:text-[#6e8c6e] transition-colors" />
          </div>
          <div className="text-sm font-display font-bold text-[#f5f2ed]">05 Active</div>
          <div className="text-[10px] text-[#6d675e]">LangGraph Multi-Agent</div>
        </button>

        <button
          onClick={() => onNavigate && onNavigate('data-sources')}
          className="clora-surface p-2.5 space-y-1 text-left hover:border-[#38bdf8] transition-all group"
        >
          <div className="flex items-center justify-between text-[11px] text-[#a09a90]">
            <div className="flex items-center gap-1.5">
              <BookOpen size={13} className="text-[#38bdf8]" />
              <span>Data Files</span>
            </div>
            <ArrowUpRight size={11} className="text-[#6d675e] group-hover:text-[#38bdf8] transition-colors" />
          </div>
          <div className="text-sm font-display font-bold text-[#f5f2ed]">{filesCount} Ingested</div>
          <div className="text-[10px] text-[#6d675e]">Dual-Engine OCR & CSV</div>
        </button>

        <button
          onClick={() => onNavigate && onNavigate('graph')}
          className="clora-surface p-2.5 space-y-1 text-left hover:border-[#fbbf24] transition-all group"
        >
          <div className="flex items-center justify-between text-[11px] text-[#a09a90]">
            <div className="flex items-center gap-1.5">
              <Wrench size={13} className="text-[#fbbf24]" />
              <span>Topology</span>
            </div>
            <ArrowUpRight size={11} className="text-[#6d675e] group-hover:text-[#fbbf24] transition-colors" />
          </div>
          <div className="text-sm font-display font-bold text-[#f5f2ed]">14 Assets</div>
          <div className="text-[10px] text-[#6d675e]">Blast-Radius Ready</div>
        </button>
      </div>

      <div className="p-2.5 rounded-lg bg-[#181614] border border-[#2b2723] text-[10px] text-[#a09a90] space-y-1">
        <span className="text-[#d9825b] font-semibold uppercase tracking-wider block text-[9px]">
          EXECUTION GUARANTEE
        </span>
        <p className="leading-relaxed text-[#8a8377]">
          Every reasoning step, embedding extraction, and SQL table analysis executes strictly within host memory without cloud AI dependency.
        </p>
      </div>
    </div>
  );
}
