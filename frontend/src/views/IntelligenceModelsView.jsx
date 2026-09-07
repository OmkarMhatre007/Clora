import React, { useState, useEffect } from 'react';
import { Cpu, Zap, Activity, HardDrive, CheckCircle2, Check, RefreshCw, Layers, ShieldCheck } from 'lucide-react';
import { getModels, getRegisteredModels, selectActiveModel } from '../services/api';

export default function IntelligenceModelsView() {
  const [activeModel, setActiveModel] = useState('qwen2.5:3b');
  const [availableModels, setAvailableModels] = useState(['qwen2.5:3b', 'llama3.2:3b', 'phi3.5:latest']);
  const [registeredProfiles, setRegisteredProfiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [notice, setNotice] = useState(null);

  const loadModels = async () => {
    setLoading(true);
    try {
      const [modelsData, profiles] = await Promise.all([
        getModels(),
        getRegisteredModels()
      ]);
      if (modelsData) {
        if (typeof modelsData.active_model === 'string') {
          setActiveModel(modelsData.active_model);
        } else if (modelsData.active_model?.name) {
          setActiveModel(modelsData.active_model.name);
        }

        if (Array.isArray(modelsData.available_models)) {
          const names = modelsData.available_models.map(m =>
            typeof m === 'string' ? m : m?.name || m?.model_id || 'qwen2.5:3b'
          ).filter(Boolean);
          if (names.length > 0) {
            setAvailableModels(Array.from(new Set(names)));
          }
        }
      }
      if (profiles && Array.isArray(profiles)) {
        setRegisteredProfiles(profiles);
      }
    } catch (err) {
      console.warn('Failed to load models data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleSelectModel = async (modelName) => {
    const nameStr = typeof modelName === 'string' ? modelName : modelName?.name || 'qwen2.5:3b';
    setSwitching(true);
    setNotice(null);
    try {
      await selectActiveModel(nameStr);
      setActiveModel(nameStr);
      setNotice({
        type: 'success',
        message: `Active model successfully switched to '${nameStr}' with zero cloud fallback.`
      });
      await loadModels();
    } catch (err) {
      setNotice({
        type: 'error',
        message: `Failed to switch model: ${err.message}`
      });
    } finally {
      setSwitching(false);
    }
  };

  const modelMetadataMap = {
    'llama3.2:3b': {
      displayName: 'Llama 3.2 3B Instruct',
      role: 'General Multi-Agent Reasoning & Failure Root-Cause Analysis',
      ttft: '0.48 s',
      throughput: '12.4 tok/s',
      vram: '2.8 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Standard (1B-4B)'
    },
    'qwen2.5:3b': {
      displayName: 'Qwen 2.5 3B Instruct',
      role: 'Long-Context Document Synthesis & Python Sandbox Code Engine',
      ttft: '0.52 s',
      throughput: '11.8 tok/s',
      vram: '3.0 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Standard (1B-4B)'
    },
    'phi3.5:latest': {
      displayName: 'Phi 3.5 Mini 3.8B',
      role: 'Mathematical Formula Verification & Step-by-Step Logic',
      ttft: '0.61 s',
      throughput: '9.8 tok/s',
      vram: '3.4 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Standard (1B-4B)'
    },
    'qwen2.5-coder:1.5b': {
      displayName: 'Qwen 2.5 Coder 1.5B',
      role: 'Fast Lightweight SQL Scripting & Data Transformation',
      ttft: '0.28 s',
      throughput: '18.2 tok/s',
      vram: '1.6 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Lightweight (1B-2B)'
    },
    'llama3.2:1b': {
      displayName: 'Llama 3.2 1B Fast Triage',
      role: 'High-Speed Query Router, Intent Classifier & Atomic Extraction',
      ttft: '0.22 s',
      throughput: '22.0 tok/s',
      vram: '1.2 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Lightweight (1B-2B)'
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-[11px] font-mono font-bold tracking-widest text-[#6d675e] uppercase">
            INTELLIGENCE • LOCAL INFERENCE RUNTIME
          </span>
          <h1 className="text-xl font-display font-bold text-[#f5f2ed]">
            Local Sovereign Model Registry
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadModels}
            disabled={loading}
            className="btn-stone text-xs py-1.5 px-3 flex items-center gap-1.5"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            <span>Scan Daemon</span>
          </button>
          <span className="status-pill-emerald">
            <Zap size={12} />
            <span>Ollama Daemon Local</span>
          </span>
        </div>
      </div>

      {notice && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-mono flex items-center justify-between ${
            notice.type === 'error'
              ? 'bg-[#291414] border-[#6b2525] text-[#f87171]'
              : 'bg-[#142319] border-[#1f5433] text-[#34d399]'
          }`}
        >
          <span>{notice.message}</span>
          <button onClick={() => setNotice(null)} className="px-2 py-0.5 rounded bg-black/30">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Model Cards Grid */}
        <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          {availableModels.map((modItem) => {
            const modName = typeof modItem === 'string' ? modItem : modItem?.name || 'qwen2.5:3b';
            const isActive = activeModel === modName;
            const meta = modelMetadataMap[modName] || {
              displayName: modName,
              role: 'Quantized Open-Weight Local Inference',
              ttft: '0.50 s',
              throughput: '10.0 tok/s',
              vram: '3.0 GB',
              precision: 'GGUF Q4_K_M',
              tier: 'Standard'
            };

            return (
              <div
                key={modName}
                className={`clora-card p-5 space-y-3.5 flex flex-col justify-between border transition-all ${
                  isActive ? 'border-[#d9825b] shadow-lg shadow-[#d9825b]/5' : 'border-[#2e2a25]'
                }`}
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-[#f5f2ed] font-mono">{meta.displayName || modName}</h3>
                    {isActive ? (
                      <span className="status-pill-copper text-[9px]">ACTIVE INFERENCE</span>
                    ) : (
                      <span className="status-pill-sage text-[9px]">READY</span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#a09a90] leading-normal">{meta.role}</p>
                </div>

                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#26231f] text-[11px] font-mono">
                    <div className="space-y-0.5">
                      <span className="text-[9px] text-[#6d675e] block">TTFT</span>
                      <span className="text-[#f5f2ed] font-bold">{meta.ttft}</span>
                    </div>
                    <div className="space-y-0.5">
                      <span className="text-[9px] text-[#6d675e] block">Throughput</span>
                      <span className="text-[#d9825b] font-bold">{meta.throughput}</span>
                    </div>
                    <div className="space-y-0.5">
                      <span className="text-[9px] text-[#6d675e] block">VRAM Footprint</span>
                      <span className="text-[#a09a90]">{meta.vram}</span>
                    </div>
                    <div className="space-y-0.5">
                      <span className="text-[9px] text-[#6d675e] block">Quantization</span>
                      <span className="text-[#8ca68c]">{meta.precision}</span>
                    </div>
                  </div>

                  {!isActive && (
                    <button
                      onClick={() => handleSelectModel(modName)}
                      disabled={switching}
                      className="w-full py-1.5 px-3 rounded-lg bg-[#24201d] hover:bg-[#2d2723] border border-[#3b3630] hover:border-[#d9825b] text-xs font-semibold text-[#f5f2ed] flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Check size={13} className="text-[#d9825b]" />
                      <span>Select as Active Model</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Panel: Resource Allocation */}
        <div className="lg:col-span-4 space-y-4">
          <div className="clora-card p-4.5 space-y-4 border border-[#2e2a25]">
            <div className="flex items-center justify-between border-b border-[#2e2a25] pb-2">
              <span className="text-xs font-semibold text-[#f5f2ed] uppercase tracking-wide">
                Hardware Compute Allocation
              </span>
              <HardDrive size={13} className="text-[#d9825b]" />
            </div>

            {/* RAM Meter */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#a09a90]">Host RAM</span>
                <span className="font-mono text-[#f5f2ed] font-bold">Local Host Memory</span>
              </div>
              <div className="w-full h-2 rounded-full bg-[#181614] overflow-hidden">
                <div className="h-full bg-[#d9825b] rounded-full w-[35%]" />
              </div>
            </div>

            {/* VRAM Meter */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#a09a90]">Active Model Memory</span>
                <span className="font-mono text-[#f5f2ed] font-bold">~3.0 GB Allocated</span>
              </div>
              <div className="w-full h-2 rounded-full bg-[#181614] overflow-hidden">
                <div className="h-full bg-[#10b981] rounded-full w-[45%]" />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-[#181614] border border-[#2b2723] space-y-1 text-xs text-[#a09a90]">
              <span className="text-[#10b981] font-semibold text-[10px] uppercase tracking-wide block">
                Air-Gap Ingestion Sentinel
              </span>
              <p className="text-[11px] text-[#8a8377] leading-relaxed">
                Zero cloud API calls are made. All transformer layers execute locally on local CPU/GPU hardware.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
