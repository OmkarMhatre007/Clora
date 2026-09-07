import React from 'react';
import {
  Layers,
  Database,
  Network,
  Bot,
  Cpu,
  ShieldCheck,
  FileText,
  Clock,
  Sparkles,
  Zap,
  Camera
} from 'lucide-react';

export default function Sidebar({ activeView = 'workbench', onViewChange, liveStats = {} }) {
  const navSections = [
    {
      title: 'OPERATIONS',
      items: [
        { id: 'workbench', label: 'Investigation Workbench', icon: Layers, badge: liveStats.queriesCount ? `${liveStats.queriesCount}` : null },
        { id: 'visual-inspection', label: 'Visual Inspection & BBox', icon: Camera, badge: '5-Level' },
        { id: 'data-sources', label: 'Data Sources & OCR', icon: Database, badge: liveStats.filesCount ? `${liveStats.filesCount}` : null },
        { id: 'graph', label: 'Topology Graph', icon: Network },
      ]
    },
    {
      title: 'LOCAL INTELLIGENCE',
      items: [
        { id: 'intelligence-agents', label: 'Multi-Agent Spine', icon: Bot },
        { id: 'intelligence-models', label: 'Compute & LLM Registry', icon: Cpu, badge: liveStats.activeModel ? '3B' : null },
      ]
    },
    {
      title: 'SOVEREIGNTY & AUDIT',
      items: [
        { id: 'sovereignty', label: 'Air-Gap Sentinel', icon: ShieldCheck, isProtected: true },
      ]
    }
  ];

  return (
    <aside className="w-64 bg-[#161412] border-r border-[#2a2622] flex flex-col justify-between p-3 select-none shrink-0 min-h-[calc(100vh-4rem)] shadow-lg">
      <div className="space-y-6">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1.5">
            <span className="px-3 text-[10px] font-bold tracking-widest text-[#6d675e] uppercase font-mono">
              {section.title}
            </span>
            <div className="space-y-1 mt-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id || (activeView === 'home' && item.id === 'workbench');
                return (
                  <button
                    key={item.id}
                    onClick={() => onViewChange && onViewChange(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-[#d9825b] text-white shadow-md font-semibold'
                        : 'text-[#a09a90] hover:text-[#f5f2ed] hover:bg-[#201d1a]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon size={16} className={isActive ? 'text-white' : 'text-[#8a8377]'} />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-md ${
                        isActive ? 'bg-black/30 text-white font-bold' : 'bg-[#221f1c] text-[#a09a90] border border-[#3b3630]'
                      }`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Status Footer */}
      <div className="p-3 rounded-xl bg-[#1d1a18] border border-[#2e2a25] space-y-1.5 text-[11px] text-[#8a8377]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
            <span className="font-semibold text-[#f5f2ed]">Air-Gap Verified</span>
          </div>
          <span className="font-mono text-[#6d675e] text-[10px]">MRPL SIH</span>
        </div>
        <div className="text-[10px] text-[#6d675e] font-mono flex items-center justify-between">
          <span>0 B Egress</span>
          <span>100% On-Prem</span>
        </div>
      </div>
    </aside>
  );
}
