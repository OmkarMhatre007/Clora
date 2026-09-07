"""
Golden Fixtures Builder for CLORA Sovereign Multimodal Demonstration.
SIH Flagship Scenario: Centrifugal Feed Pump P-101 Bearing Degradation & Trip.

Generates:
samples/
├── photographs/ (p101_bearing.jpg, nameplate.jpg, flange_corrosion.jpg, motor_stator.jpg)
├── telemetry/ (p101_vibration_telemetry.csv, m101_power_telemetry.csv)
├── sop/ (SOP-MRPL-P101-MNT.md, SOP-API-610-PUMP.md)
├── documents/ (P101_Equipment_Data_Sheet.pdf)
└── manifests/ (p101_flagship_manifest.json)
"""

import os
import io
import json
import hashlib
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont


def ensure_dirs():
    base = Path("samples")
    for d in ["photographs", "telemetry", "sop", "documents", "manifests"]:
        (base / d).mkdir(parents=True, exist_ok=True)


def build_telemetry():
    telem_csv = (
        "timestamp,equipment_id,measurement,value,unit,status\n"
        "2026-09-07T08:00:00Z,P-101,vibration_velocity_rms,3.12,mm/s,NORMAL\n"
        "2026-09-07T08:30:00Z,P-101,vibration_velocity_rms,4.45,mm/s,NORMAL\n"
        "2026-09-07T09:00:00Z,P-101,vibration_velocity_rms,6.80,mm/s,ALARM\n"
        "2026-09-07T09:15:00Z,P-101,vibration_velocity_rms,9.82,mm/s,TRIP\n"
        "2026-09-07T08:00:00Z,P-101,bearing_temp_c,62.4,C,NORMAL\n"
        "2026-09-07T08:30:00Z,P-101,bearing_temp_c,74.1,C,NORMAL\n"
        "2026-09-07T09:00:00Z,P-101,bearing_temp_c,88.5,C,ALARM\n"
        "2026-09-07T09:15:00Z,P-101,bearing_temp_c,104.2,C,TRIP\n"
    )
    p = Path("samples/telemetry/p101_vibration_telemetry.csv")
    with open(p, "w", encoding="utf-8") as f:
        f.write(telem_csv)
    return p


def build_sop():
    sop_content = """# STANDARD OPERATING PROCEDURE (SOP)
## DOCUMENT ID: SOP-MRPL-P101-MNT (REV 04)
### ASSET: SULZER API 610 BB2 CENTRIFUGAL PUMP (TAG: P-101)

#### SECTION 1: PURPOSE & SCOPE
This standard operating procedure establishes the mandatory mechanical maintenance protocol
for high-pressure feed pump P-101 in the CDU/VDU refinery units.

#### SECTION 2: GOVERNING STANDARDS & THRESHOLDS
Operating parameters are governed by ISO 10816-3 (Class II/III Machinery) and API 610 11th Edition.
- Normal Vibration Velocity RMS: < 4.5 mm/s
- Warning Vibration Velocity RMS: 4.5 mm/s to 7.1 mm/s
- Critical Trip Vibration Velocity RMS: >= 7.1 mm/s
- Maximum Bearing Housing Temperature: 80.0 °C (Warning), 95.0 °C (Trip)

#### SECTION 3: VISUAL INSPECTION FINDINGS
Raceway fatigue spalling, metallic flaking, or heat tint discoloration on roller elements
mandates immediate mechanical isolation if corroborated by vibration velocity >= 7.1 mm/s RMS.

#### SECTION 4: MANDATORY INTERVENTION PROTOCOL
Section 4.2: Mechanical Overhaul & Bearing Replacement
1. Perform controlled emergency operational shutdown of Pump P-101.
2. Disconnect drive coupling from Motor M-101 and install Lockout/Tagout (LOTO).
3. Drain lube oil reservoir and inspect magnetic drain plug for ferremagnetic wear debris.
4. Replace inboard angular contact bearing assembly with pre-certified OEM bearing.
5. Perform laser shaft alignment before re-coupling.
"""
    p = Path("samples/sop/SOP-MRPL-P101-MNT.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(sop_content)
    return p


def copy_or_generate_photos():
    src_fixtures = Path("samples/vision_fixtures")
    dest = Path("samples/photographs")
    photos = {}
    for jpg in ["p101_bearing.jpg", "nameplate.jpg", "flange_corrosion.jpg", "motor_stator.jpg"]:
        src_path = src_fixtures / jpg
        dest_path = dest / jpg
        if src_path.exists():
            shutil.copy2(src_path, dest_path)
            with open(dest_path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            photos[jpg] = {"path": str(dest_path), "sha256": h}
    return photos


def build_flagship_manifest(photos, telem_path, sop_path):
    with open(telem_path, "rb") as f:
        telem_h = hashlib.sha256(f.read()).hexdigest()
    with open(sop_path, "rb") as f:
        sop_h = hashlib.sha256(f.read()).hexdigest()

    manifest = {
        "scenario_id": "P101_FLAGSHIP_END_TO_END",
        "equipment_id": "P-101",
        "equipment_name": "Sulzer API 610 BB2 Centrifugal Feed Pump",
        "plant_unit": "MRPL Sulfur Recovery Unit (SRU-2)",
        "version": "1.0",
        "flagship_photo": {
            "filename": "p101_bearing.jpg",
            "sha256": photos.get("p101_bearing.jpg", {}).get("sha256"),
            "path": photos.get("p101_bearing.jpg", {}).get("path"),
            "defect_observed": "BEARING_FATIGUE_SPALLING",
        },
        "flagship_nameplate": {
            "filename": "nameplate.jpg",
            "sha256": photos.get("nameplate.jpg", {}).get("sha256"),
            "path": photos.get("nameplate.jpg", {}).get("path"),
            "design_limits": {"rated_power_kw": 315.0, "rated_speed_rpm": 1480, "max_pressure_bar": 25.0},
        },
        "telemetry_dataset": {
            "filename": "p101_vibration_telemetry.csv",
            "sha256": telem_h,
            "path": str(telem_path),
            "peak_vibration_rms": 9.82,
            "peak_bearing_temp_c": 104.2,
            "iso_limit_exceeded": True,
        },
        "sop_document": {
            "filename": "SOP-MRPL-P101-MNT.md",
            "sha256": sop_h,
            "path": str(sop_path),
            "governing_standard": "ISO 10816-3 (Class II/III)",
            "intervention_section": "Section 4.2 Mechanical Overhaul & Bearing Replacement",
        },
    }
    out = Path("samples/manifests/p101_flagship_manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return out


if __name__ == "__main__":
    ensure_dirs()
    t_path = build_telemetry()
    s_path = build_sop()
    p_dict = copy_or_generate_photos()
    m_path = build_flagship_manifest(p_dict, t_path, s_path)
    print(f"Generated Golden Flagship Fixtures with Manifest at: {m_path}")
