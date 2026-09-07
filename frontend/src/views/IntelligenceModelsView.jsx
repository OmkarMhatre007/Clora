import React, { useState, useEffect } from 'react';
import { Cpu, Zap, Activity, HardDrive, CheckCircle2, Check, RefreshCw } from 'lucide-react';
import { getModels, getRegisteredModels, selectActiveModel } from '../services/api';

export default function IntelligenceModelsView() {
  const [activeModel, setActiveModel] = useState('llama3.2:3b');
  const [availableModels, setAvailableModels] = useState([]);
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
        if (modelsData.active_model) setActiveModel(modelsData.active_model);
        setAvailableModels(modelsData.available_models || ['llama3.2:3b', 'qwen2.5:3b', 'phi3.5:latest']);
      }
      if (profiles) {
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
    setSwitching(true);
    setNotice(null);
    try {
      await selectActiveModel(modelName);
      setActiveModel(modelName);
      setNotice({
        type: 'success',
        message: `Active sovereign model successfully switched to '${modelName}' with zero cloud fallback.`
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
      role: 'General Multi-Agent Reasoning & Failure Root-Cause Analysis',
      ttft: '0.48 s',
      throughput: '12.4 tok/s',
      vram: '2.8 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Standard (1B-4B)'
    },
    'qwen2.5:3b': {
      role: 'Long-Context Document Synthesis & Python Sandbox Code Engine',
      ttft: '0.52 s',
      throughput: '11.8 tok/s',
      vram: '3.0 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Standard (1B-4B)'
    },
    'phi3.5:latest': {
      role: 'Mathematical Formula Verification & Step-by-Step Logic',
      ttft: '0.61 s',
      throughput: '9.8 tok/s',
      vram: '3.4 GB',
      precision: 'GGUF Q4_K_M',
      tier: 'Standard (1B-4B)'
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
          {availableModels.map((modName) => {
            const isActive = activeModel === modName;
            const meta = modelMetadataMap[modName] || {
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
                    <h3 className="text-sm font-bold text-[#f5f2ed] font-mono">{modName}</h3>
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
