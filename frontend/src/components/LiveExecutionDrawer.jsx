import React from 'react';
import { CheckCircle2, Circle, Clock, FileText, ArrowRight, Download, ShieldCheck, AlertCircle } from 'lucide-react';
import { downloadQueryDocx } from '../services/api';

export default function LiveExecutionDrawer({
  activeQuery = null,
  latestQuery = null,
  isProcessing = false,
  onViewTrace
}) {
  const queryToDisplay = activeQuery || latestQuery;

  const defaultPipelineSteps = [
    { label: 'Task dispatch & query intent classified', status: 'completed' },
    { label: 'Security firewall & 0 B Egress confirmed', status: 'completed' },
    { label: 'RBAC filtered ChromaDB vector retrieval', status: isProcessing ? 'active' : 'completed' },
    { label: 'DuckDB sensor telemetry SQL query', status: isProcessing ? 'active' : 'completed' },
    { label: 'Evidence verification & Causal Leap Guard', status: isProcessing ? 'active' : 'completed' },
    { label: 'Standardized 5-Section forensic report', status: queryToDisplay?.status === 'completed' ? 'completed' : isProcessing ? 'pending' : 'completed' }
  ];

  const agentTasks = (queryToDisplay?.agent_tasks && queryToDisplay.agent_tasks.length > 0)
    ? queryToDisplay.agent_tasks.map(t => ({
        label: `${t.agent_name}: ${t.task_type}`,
        status: t.status === 'completed' ? 'completed' : t.status === 'failed' ? 'failed' : 'active',
        subtext: t.result_summary || (t.status === 'completed' ? 'Executed locally' : 'In progress')
      }))
    : defaultPipelineSteps;

  return (
    <div className="clora-card p-4.5 space-y-4 shadow-xl border border-[#2e2a25]">
      <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2.5">
        <span className="text-[11px] font-mono uppercase tracking-widest text-[#6d675e] font-bold">
          LIVE EXECUTION ENGINE
        </span>
        <span className={`status-pill-${isProcessing ? 'copper' : 'sage'}`}>
          {isProcessing ? 'PROCESSING' : 'LOCAL READY'}
        </span>
      </div>

      <div className="space-y-1">
        <h4 className="text-xs font-semibold text-[#f5f2ed] truncate">
          {queryToDisplay?.question || 'Refinery Equipment Investigation'}
        </h4>
        <div className="flex items-center justify-between text-[11px] text-[#a09a90]">
          <div className="flex items-center gap-1.5">
            <FileText size={12} className="text-[#d9825b]" />
            <span className="font-mono text-[10px] truncate max-w-[170px]">
              {queryToDisplay?.id ? `Query ID: ${queryToDisplay.id.substring(0, 12)}...` : 'CDU Unit 2 Workspace'}
            </span>
          </div>
          {queryToDisplay?.created_at && (
            <span className="text-[10px] text-[#6d675e] font-mono">
              {new Date(queryToDisplay.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>

      {/* Stepper Timeline */}
      <div className="space-y-2.5 pt-1">
        {agentTasks.map((step, idx) => {
          const isCompleted = step.status === 'completed';
          const isActive = step.status === 'active' || (isProcessing && idx === agentTasks.length - 2);
          const isFailed = step.status === 'failed';

          return (
            <div key={idx} className="flex items-start gap-2.5 text-xs">
              <div className="pt-0.5 shrink-0">
                {isCompleted ? (
                  <CheckCircle2 size={14} className="text-[#10b981]" />
                ) : isFailed ? (
                  <AlertCircle size={14} className="text-[#f43f5e]" />
                ) : isActive ? (
                  <span className="w-3.5 h-3.5 rounded-full border-2 border-[#d9825b] flex items-center justify-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#d9825b] animate-ping" />
                  </span>
                ) : (
                  <Circle size={14} className="text-[#423d37]" />
                )}
              </div>
              <div className="space-y-0.5 flex-1 min-w-0">
                <div className={`font-medium truncate ${
                  isActive ? 'text-[#d9825b]' : isCompleted ? 'text-[#c8c2b8]' : isFailed ? 'text-[#f87171]' : 'text-[#6d675e]'
                }`}>
                  {step.label}
                </div>
                {step.subtext && (
                  <div className="text-[10px] text-[#8ca68c] font-mono truncate">
                    {step.subtext}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="pt-2 border-t border-[#2a2622] space-y-2">
        {queryToDisplay?.id && (
          <button
            onClick={() => downloadQueryDocx(queryToDisplay.id)}
            className="w-full py-2 px-3 rounded-lg bg-[#291f19] hover:bg-[#38261c] border border-[#d9825b]/50 text-xs font-semibold text-[#f5f2ed] flex items-center justify-center gap-2 transition-colors"
          >
            <Download size={13} className="text-[#d9825b]" />
            <span>Export Approval Note (.docx)</span>
          </button>
        )}

        <button
          onClick={onViewTrace}
          className="w-full text-[11px] font-semibold text-[#a09a90] hover:text-[#d9825b] flex items-center justify-center gap-1.5 transition-colors py-1"
        >
          <span>VIEW SOVEREIGN TRACE</span>
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}
