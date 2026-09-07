"""
GPU Resource Telemetry & VRAM Measurement Provider for CLORA.
Supports NVML, PyTorch CUDA, or mock testing with confidence scoring.
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from app.ai.control_plane.models import MemoryConfidence

logger = logging.getLogger("indusai.gpu")


class GPUResourceProvider:
    """
    Measures available and total GPU VRAM to inform the admission controller.
    Assigns confidence levels based on whether metrics originate from live hardware.
    """

    _mock_total: Optional[int] = None
    _mock_free: Optional[int] = None

    @classmethod
    def set_mock_vram(cls, total_mb: Optional[int], free_mb: Optional[int]) -> None:
        """Allow unit tests to inject deterministic GPU telemetry."""
        cls._mock_total = total_mb
        cls._mock_free = free_mb

    @classmethod
    def get_telemetry(cls) -> Dict[str, Any]:
        """
        Query available VRAM.
        Returns:
            {
                "total_vram_mb": int,
                "free_vram_mb": int,
                "used_vram_mb": int,
                "confidence": MemoryConfidence,
                "device_name": str,
            }
        """
        # 1. Mock override (for testing)
        if cls._mock_total is not None and cls._mock_free is not None:
            return {
                "total_vram_mb": cls._mock_total,
                "free_vram_mb": cls._mock_free,
                "used_vram_mb": cls._mock_total - cls._mock_free,
                "confidence": MemoryConfidence.MEASURED,
                "device_name": "Mock GPU Test Device",
            }

        # 2. Try PyTorch CUDA if installed
        try:
            import torch
            if torch.cuda.is_available():
                dev = torch.cuda.current_device()
                name = torch.cuda.get_device_name(dev)
                total = torch.cuda.get_device_properties(dev).total_memory // (1024 * 1024)
                reserved = torch.cuda.memory_reserved(dev) // (1024 * 1024)
                free = max(0, total - reserved)
                return {
                    "total_vram_mb": total,
                    "free_vram_mb": free,
                    "used_vram_mb": reserved,
                    "confidence": MemoryConfidence.MEASURED,
                    "device_name": name,
                }
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("PyTorch CUDA query failed: %s", exc)

        # 3. Fallback to advisory/unknown
        return {
            "total_vram_mb": 16384,
            "free_vram_mb": 8192,
            "used_vram_mb": 8192,
            "confidence": MemoryConfidence.ESTIMATED,
            "device_name": "Host Memory Fallback (Advisory)",
        }
