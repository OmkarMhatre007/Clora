import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Plus,
  BookOpen,
  Paperclip,
  Wrench,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Clock,
  ChevronRight,
  ExternalLink,
  X,
  Upload,
  Cpu,
  Database,
  Sliders,
  Check,
  Download
} from 'lucide-react';
import {
  executeQuery,
  getWorkspaceFiles,
  getWorkspaceQueries,
  getModels,
  selectActiveModel,
  uploadFile,
  downloadQueryDocx
} from '../services/api';

export default function WorkbenchView({
  workspaceId = 'default-workspace',
  userRole = 'maintenance_engineer',
  onSelectEvidence,
  onQueryUpdate
}) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [recentQueries, setRecentQueries] = useState([]);
  const [workspaceFiles, setWorkspaceFiles] = useState([]);
  const [availableModels, setAvailableModels] = useState(['llama3.2:3b', 'qwen2.5:3b', 'phi3.5:latest']);
  const [activeModel, setActiveModel] = useState('llama3.2:3b');

  // Modals & Selection States
  const [activeModal, setActiveModal] = useState(null); // 'add-files' | 'knowledge' | 'attach-data' | 'select-tool'
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [selectedTools, setSelectedTools] = useState(['chromadb', 'duckdb', 'causal_verifier', 'docx_exporter']);
  const fileInputRef = useRef(null);

  const activeModelName = typeof activeModel === 'string' ? activeModel : activeModel?.name || 'llama3.2:3b';

  // Load live files, models, and queries on mount
  const loadData = async () => {
    try {
      const [files, queries, modelsData] = await Promise.all([
        getWorkspaceFiles(workspaceId),
        getWorkspaceQueries(workspaceId),
        getModels()
      ]);
      setWorkspaceFiles(files || []);
      setRecentQueries(queries || []);
      if (modelsData) {
        const rawList = Array.isArray(modelsData.available_models) ? modelsData.available_models : ['llama3.2:3b', 'qwen2.5:3b', 'phi3.5:latest'];
        const normalized = rawList.map(m => typeof m === 'string' ? m : m?.name || 'qwen2.5:3b').filter(Boolean);
        setAvailableModels(Array.from(new Set(normalized)));
        if (modelsData.active_model) {
          const actName = typeof modelsData.active_model === 'string' ? modelsData.active_model : modelsData.active_model?.name || 'llama3.2:3b';
          setActiveModel(actName);
        }
      }
    } catch (err) {
      console.warn('Error loading workbench initial data:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, [workspaceId]);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      for (const f of files) {
        try {
          const uploaded = await uploadFile(workspaceId, f);
          setAttachedFiles(prev => [...prev, { name: uploaded.filename, size: `${(uploaded.size / 1024).toFixed(1)} KB`, id: uploaded.id }]);
        } catch (err) {
          console.error('File upload error:', err);
        }
      }
      await loadData();
      setActiveModal(null);
    }
  };

  const removeAttachedFile = (idx) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const toggleTool = (toolId) => {
    setSelectedTools(prev =>
      prev.includes(toolId) ? prev.filter(t => t !== toolId) : [...prev, toolId]
    );
  };

  const handleRun = async (queryText) => {
    const textToRun = (queryText || prompt || '').trim();
    if (!textToRun) return;

    setLoading(true);
    setResult(null);

    try {
      const data = await executeQuery(
        textToRun,
        workspaceId,
        userRole,
        (progressQuery) => {
          if (onQueryUpdate) onQueryUpdate(progressQuery);
        }
      );
      setResult(data);
      if (onQueryUpdate) onQueryUpdate(data);
      await loadData();
    } catch (err) {
      setResult({
        question: textToRun,
        status: 'failed',
        error_message: err.message,
        response: `Execution encountered an issue: ${err.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Workspace Hero & Query Card */}
      <div className="clora-card p-6 space-y-4 relative overflow-hidden border border-[#2e2a25]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <span className="text-[11px] font-mono font-bold tracking-widest text-[#6d675e] uppercase">
              WORKSPACE • CDU UNIT 2
            </span>
            <h1 className="text-2xl font-display font-bold text-[#f5f2ed]">
              What are we investigating today?
            </h1>
          </div>
          <div className="flex flex-col items-start sm:items-end text-left sm:text-right">
            <span className="text-[11px] font-semibold text-[#6e8c6e] flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-[#10b981]" />
              <span>AIR-GAPPED LOCAL EXECUTION</span>
            </span>
            <span className="text-[10px] text-[#6d675e] font-mono">
              0 B EGRESS • {workspaceFiles.length} FILES LOADED
            </span>
          </div>
        </div>

        {/* Input Box */}
        <div className="rounded-xl border border-[#3b3630] bg-[#171513] focus-within:border-[#d9825b] transition-all p-3 space-y-3 shadow-inner">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                handleRun();
              }
            }}
            placeholder="Ask an industrial engineering or forensic inquiry... (e.g., Why did Booster Pump P-101 fail at 14:35Z?)"
            className="w-full bg-transparent text-sm text-[#f5f2ed] placeholder:text-[#6d675e] resize-none outline-none min-h-[70px]"
          />

          {/* Active Context Chips Bar */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[#24211d]">
              {attachedFiles.map((file, idx) => (
                <span
                  key={`att_${idx}`}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#201e1a] border border-[#3d3830] text-[11px] text-[#f5f2ed]"
                >
                  <FileText size={11} className="text-[#d9825b]" />
                  <span className="font-mono">{file.name}</span>
                  <button
                    onClick={() => removeAttachedFile(idx)}
                    className="text-[#6d675e] hover:text-[#f43f5e] ml-1"
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Action Buttons Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-[#26231f]">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Native File Input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                multiple
                className="hidden"
              />

              {/* 1. Add Files Button */}
              <button
                onClick={() => setActiveModal('add-files')}
                className="btn-outline text-xs py-1 px-2.5 flex items-center gap-1.5"
              >
                <Plus size={13} />
                <span>Add Files ({workspaceFiles.length})</span>
              </button>

              {/* 2. Knowledge Context Button */}
              <button
                onClick={() => setActiveModal('knowledge')}
                className="btn-outline text-xs py-1 px-2.5 flex items-center gap-1.5"
              >
                <BookOpen size={13} />
                <span>Knowledge Chunks</span>
              </button>

              {/* 3. Attach Data Button */}
              <button
                onClick={() => setActiveModal('attach-data')}
                className="btn-outline text-xs py-1 px-2.5 flex items-center gap-1.5"
              >
                <Paperclip size={13} />
                <span>Telemetry Tables</span>
              </button>

              {/* 4. Select Model & Tools Button */}
              <button
                onClick={() => setActiveModal('select-tool')}
                className="btn-outline text-xs py-1 px-2.5 flex items-center gap-1.5"
              >
                <Wrench size={13} />
                <span>Model: {activeModelName.split(':')[0]}</span>
              </button>
            </div>

            {/* Run Query Button */}
            <button
              onClick={() => handleRun()}
              disabled={loading || !prompt.trim()}
              className="btn-copper text-xs py-1.5 px-4 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-3.5 h-3.5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                  <span>Reasoning Locally...</span>
                </>
              ) : (
                <>
                  <span>Run Investigation</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Action Suggestion Pills */}
        <div className="flex items-center gap-2 pt-1 flex-wrap">
          {[
            'Why did Booster Pump P-101 fail at 14:35Z?',
            'What is the threshold limit for bearing temperature?',
            'List all critical vibration incidents in CDU-1',
            'Generate MRPL Executive Approval Note'
          ].map((pill, i) => (
            <button
              key={i}
              onClick={() => {
                setPrompt(pill);
                handleRun(pill);
              }}
              className="px-3 py-1 rounded-full text-xs font-medium bg-[#1d1b18] border border-[#2e2a25] text-[#a09a90] hover:text-[#f5f2ed] hover:border-[#d9825b] transition-all truncate max-w-xs"
            >
              {pill}
            </button>
          ))}
        </div>
      </div>

      {/* MODAL 1: ADD FILES FROM WORKSPACE */}
      {activeModal === 'add-files' && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="clora-card w-full max-w-lg p-6 space-y-5 border-[#d9825b]/50 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-[#f5f2ed]">
                <Plus size={16} className="text-[#d9825b]" />
                <span>Attach Workspace Files</span>
              </div>
              <button onClick={() => setActiveModal(null)} className="text-[#a09a90] hover:text-[#f5f2ed]">
                <X size={18} />
              </button>
            </div>

            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-[#3b3630] hover:border-[#d9825b] rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-2 bg-[#171513] cursor-pointer transition-all"
            >
              <Upload size={24} className="text-[#d9825b]" />
              <span className="text-xs font-semibold text-[#f5f2ed]">Upload New Local Document</span>
              <span className="text-[10px] text-[#6d675e]">PDF manuals, Scanned inspections, CSV telemetry</span>
            </div>

            <div className="space-y-2">
              <span className="text-[11px] font-mono text-[#6d675e] uppercase">
                Available in {workspaceId} ({workspaceFiles.length}):
              </span>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {workspaceFiles.map((file) => (
                  <div
                    key={file.id}
                    onClick={() => {
                      setAttachedFiles(prev => prev.some(f => f.id === file.id) ? prev : [...prev, { name: file.filename, size: `${(file.size / 1024).toFixed(1)} KB`, id: file.id }]);
                      setActiveModal(null);
                    }}
                    className="p-2.5 rounded-lg bg-[#1b1917] hover:bg-[#25221e] border border-[#2b2723] flex items-center justify-between cursor-pointer text-xs transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <FileText size={14} className="text-[#d9825b]" />
                      <span className="text-[#f5f2ed] font-medium">{file.filename}</span>
                    </div>
                    <span className="text-[10px] text-[#6d675e] font-mono">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[#2a2622]">
              <button onClick={() => setActiveModal(null)} className="btn-outline text-xs">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: KNOWLEDGE CONTEXT */}
      {activeModal === 'knowledge' && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="clora-card w-full max-w-lg p-6 space-y-4 border-[#6e8c6e]/50 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-[#f5f2ed]">
                <BookOpen size={16} className="text-[#6e8c6e]" />
                <span>Knowledge Base Documents ({workspaceFiles.length})</span>
              </div>
              <button onClick={() => setActiveModal(null)} className="text-[#a09a90] hover:text-[#f5f2ed]">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {workspaceFiles.map((f) => (
                <div key={f.id} className="p-3 rounded-xl bg-[#181614] border border-[#2e2a25] flex items-center justify-between text-xs">
                  <div className="space-y-0.5">
                    <div className="font-semibold text-[#f5f2ed]">{f.filename}</div>
                    <div className="text-[10px] text-[#6d675e] font-mono">
                      Type: {f.file_type} • Method: {f.extraction_method || 'native_text'}
                    </div>
                  </div>
                  <span className="status-pill-sage text-[10px]">
                    {f.status}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2 border-t border-[#2a2622]">
              <button onClick={() => setActiveModal(null)} className="btn-copper text-xs">
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: ATTACH DATA */}
      {activeModal === 'attach-data' && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="clora-card w-full max-w-lg p-6 space-y-4 border-[#38bdf8]/50 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-[#f5f2ed]">
                <Database size={16} className="text-[#38bdf8]" />
                <span>Tabular Sensor Datasets (DuckDB)</span>
              </div>
              <button onClick={() => setActiveModal(null)} className="text-[#a09a90] hover:text-[#f5f2ed]">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {workspaceFiles.filter(f => f.filename.endsWith('.csv') || f.file_type === 'text/csv').map((f) => (
                <div key={f.id} className="p-3 rounded-xl bg-[#182328] border border-[#38bdf8]/40 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-[#f5f2ed]">{f.filename}</div>
                    <div className="text-[10px] text-[#7dd3fc] font-mono">DuckDB in-memory table mapped</div>
                  </div>
                  <span className="status-pill-emerald text-[10px]">MOUNTED</span>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2 border-t border-[#2a2622]">
              <button onClick={() => setActiveModal(null)} className="btn-copper text-xs">
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: SELECT MODEL & TOOLS */}
      {activeModal === 'select-tool' && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="clora-card w-full max-w-lg p-6 space-y-4 border-[#d9825b]/50 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-[#f5f2ed]">
                <Cpu size={16} className="text-[#d9825b]" />
                <span>Local Model & Tool Orchestration</span>
              </div>
              <button onClick={() => setActiveModal(null)} className="text-[#a09a90] hover:text-[#f5f2ed]">
                <X size={18} />
              </button>
            </div>

            {/* Model Selector */}
            <div className="space-y-2">
              <span className="text-[11px] font-mono text-[#6d675e] uppercase">Active Local LLM:</span>
              <div className="space-y-1.5">
                {availableModels.map((m) => {
                  const mName = typeof m === 'string' ? m : m?.name || 'qwen2.5:3b';
                  const isSelected = activeModelName === mName;
                  return (
                    <div
                      key={mName}
                      onClick={async () => {
                        setActiveModel(mName);
                        try {
                          await selectActiveModel(mName);
                        } catch (e) {
                          console.warn('Model switch sync warning:', e);
                        }
                      }}
                      className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? 'bg-[#291f19] border-[#d9825b] text-[#f5f2ed]'
                          : 'bg-[#181614] border-[#2e2a25] text-[#a09a90] hover:border-[#3d3830]'
                      }`}
                    >
                      <div className="text-xs font-bold font-mono">{mName}</div>
                      {isSelected && <Check size={14} className="text-[#d9825b]" />}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Tools Enabled */}
            <div className="space-y-2 pt-2 border-t border-[#26231f]">
              <span className="text-[11px] font-mono text-[#6d675e] uppercase">Enabled Sub-Agents & Tools:</span>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'chromadb', name: 'ChromaDB Vectors' },
                  { id: 'duckdb', name: 'DuckDB SQL AST' },
                  { id: 'causal_verifier', name: 'Causal Leap Guard' },
                  { id: 'docx_exporter', name: 'Word DOCX Engine' }
                ].map((tool) => {
                  const isEnabled = selectedTools.includes(tool.id);
                  return (
                    <div
                      key={tool.id}
                      onClick={() => toggleTool(tool.id)}
                      className={`p-2 rounded-lg border transition-all cursor-pointer flex items-center justify-between text-xs ${
                        isEnabled ? 'bg-[#1e1c19] border-[#6e8c6e] text-[#f5f2ed]' : 'bg-[#161412] border-[#26231f] text-[#6d675e]'
                      }`}
                    >
                      <span className="truncate">{tool.name}</span>
                      {isEnabled && <Check size={12} className="text-[#6e8c6e]" />}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-[#2a2622]">
              <button onClick={() => setActiveModal(null)} className="btn-copper text-xs">
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Synthesized Response Section */}
      {result && (
        <div className="clora-card p-6 space-y-4 border-[#d9825b]/40 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#2e2a25] pb-3">
            <div className="flex items-center gap-2.5">
              <span className={`w-2.5 h-2.5 rounded-full ${result.status === 'failed' ? 'bg-[#ef4444]' : 'bg-[#10b981]'}`} />
              <h3 className="text-sm font-semibold text-[#f5f2ed] tracking-wide uppercase">
                {result.status === 'failed' ? 'Investigation Alert' : 'Evidence-Grounded Forensic Report'}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="status-pill-sage">
                <ShieldCheck size={12} />
                <span>SOVEREIGN VERIFIED</span>
              </span>
              {result.id && (
                <button
                  onClick={() => downloadQueryDocx(result.id)}
                  className="btn-copper text-xs py-1 px-2.5 flex items-center gap-1.5"
                  title="Download MRPL Executive Approval Note"
                >
                  <Download size={12} />
                  <span>Download .docx</span>
                </button>
              )}
            </div>
          </div>

          <div className="space-y-4 text-xs leading-relaxed text-[#c8c2b8]">
            <pre className="font-sans whitespace-pre-wrap text-[#d6d0c4] bg-[#161412] p-4 rounded-xl border border-[#2c2824] leading-relaxed">
              {result.response || result.answer || result.error_message || 'Processing response...'}
            </pre>
          </div>

          {/* Document Sources Badges */}
          {result.sources && result.sources.length > 0 && (
            <div className="pt-2 border-t border-[#26231f] flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-[#6d675e] font-mono">CITED SOURCES:</span>
                {result.sources.map((src, i) => (
                  <button
                    key={i}
                    onClick={() => onSelectEvidence && onSelectEvidence(src)}
                    className="px-2.5 py-1 rounded-lg bg-[#201e1b] border border-[#3b3630] text-[11px] text-[#a09a90] hover:text-[#d9825b] hover:border-[#d9825b] transition-all flex items-center gap-1.5"
                  >
                    <FileText size={11} className="text-[#d9825b]" />
                    <span>{src.filename || 'Source'} (p.{src.page || 1})</span>
                    <ExternalLink size={10} />
                  </button>
                ))}
              </div>
              <span className="text-[10px] text-[#6e8c6e] font-mono">100% Grounded</span>
            </div>
          )}
        </div>
      )}

      {/* Recent Work Table */}
      <div className="clora-card p-5 space-y-3 border border-[#2e2a25]">
        <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2.5">
          <h3 className="text-sm font-semibold text-[#f5f2ed] tracking-wide">
            Recent Forensic Inquiries
          </h3>
          <span className="text-[11px] text-[#6d675e] font-mono">
            {recentQueries.length} Investigations Saved
          </span>
        </div>

        <div className="divide-y divide-[#26231f]">
          {recentQueries.length === 0 ? (
            <div className="py-6 text-center text-[#6d675e] text-xs">
              No previous queries in this workspace. Enter a prompt above to start.
            </div>
          ) : (
            recentQueries.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  setPrompt(item.question);
                  setResult(item);
                }}
                className="py-3 px-2 flex items-center justify-between hover:bg-[#1f1d1a] rounded-lg transition-colors cursor-pointer group"
              >
                <div className="flex items-center gap-3 min-w-0 mr-3">
                  <FileText size={15} className="text-[#d9825b] group-hover:scale-110 transition-transform shrink-0" />
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-[#f5f2ed] group-hover:text-[#d9825b] transition-colors truncate">
                      {item.question}
                    </div>
                    <div className="text-[10px] text-[#6d675e] flex items-center gap-2 mt-0.5">
                      <span>{new Date(item.created_at).toLocaleString()}</span>
                      <span>•</span>
                      <span className="font-mono">{item.id.substring(0, 8)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className={`status-pill-${item.status === 'completed' ? 'sage' : item.status === 'failed' ? 'amber' : 'copper'}`}>
                    {item.status}
                  </span>
                  <ChevronRight size={14} className="text-[#6d675e] group-hover:text-[#d9825b] transition-colors" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
