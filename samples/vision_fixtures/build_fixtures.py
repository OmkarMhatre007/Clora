"""
Golden Vision Fixture Generator & Manifest Builder.
INDUSAI-X / CLORA Sovereign Multimodal Subsystem.
Creates cryptographically attested golden vision fixtures and writes manifest.json.
"""

import os
import json
import hashlib
from typing import Dict, List, Any
from PIL import Image, ImageDraw


def build_golden_vision_fixtures(fixture_dir: str = "samples/vision_fixtures") -> List[Dict[str, Any]]:
    os.makedirs(fixture_dir, exist_ok=True)
    manifest = []

    # 1. P-101 Bearing Spalling
    p101_file = "p101_bearing.jpg"
    p101_path = os.path.join(fixture_dir, p101_file)
    img1 = Image.new("RGB", (640, 480), color=(180, 185, 190))
    d1 = ImageDraw.Draw(img1)
    d1.ellipse([70, 40, 570, 440], outline=(70, 75, 80), width=18)
    d1.ellipse([160, 110, 480, 370], outline=(100, 105, 110), width=14)
    d1.rectangle([220, 140, 460, 320], fill=(60, 50, 40), outline=(210, 60, 30), width=3)
    d1.text((235, 155), "FATIGUE SPALLING ZONE", fill=(255, 200, 80))
    d1.text((235, 180), "Depth: ~1.2mm | Micro-cracks", fill=(240, 240, 240))
    d1.text((235, 205), "P-101 Inboard Cylindrical Roller", fill=(200, 200, 200))
    for x in range(120, 540, 65):
        d1.rectangle([x, 60, x + 40, 100], fill=(130, 135, 140), outline=(40, 40, 40), width=2)
    img1.save(p101_path, format="JPEG", quality=95)

    with open(p101_path, "rb") as f:
        h1 = hashlib.sha256(f.read()).hexdigest()

    manifest.append({
        "sha256": h1,
        "fixture_id": "P101_BEARING_SPALLING",
        "equipment_id": "P-101",
        "version": "1.0",
        "filename": p101_file,
        "description": "Inner ring raceway fatigue spalling on Pump P-101 inboard bearing",
        "mime_type": "image/jpeg"
    })

    # 2. Sulzer Pump Nameplate
    nameplate_file = "nameplate.jpg"
    nameplate_path = os.path.join(fixture_dir, nameplate_file)
    img2 = Image.new("RGB", (700, 500), color=(220, 220, 225))
    d2 = ImageDraw.Draw(img2)
    d2.rectangle([20, 20, 680, 480], fill=(235, 238, 242), outline=(30, 40, 60), width=6)
    d2.rectangle([35, 35, 665, 465], outline=(120, 130, 145), width=2)
    d2.text((50, 55), "SULZER PUMPS - API 610 11TH EDITION", fill=(10, 25, 60))
    d2.line([(50, 85), (650, 85)], fill=(30, 40, 60), width=3)
    d2.text((60, 105), "PUMP MODEL:   OH2-100-250", fill=(20, 20, 20))
    d2.text((380, 105), "SERIAL NO:    SZ-2024-8841", fill=(20, 20, 20))
    d2.text((60, 155), "RATED POWER:  315 kW", fill=(20, 20, 20))
    d2.text((380, 155), "RATED SPEED:  1480 RPM", fill=(20, 20, 20))
    d2.text((60, 205), "DESIGN FLOW:  240 m3/h", fill=(20, 20, 20))
    d2.text((380, 205), "MAX OP PRESS: 25.0 BAR", fill=(20, 20, 20))
    d2.text((60, 255), "HEAD:         118 METERS", fill=(20, 20, 20))
    d2.text((380, 255), "VOLTAGE:      415 V / 3 PH", fill=(20, 20, 20))
    d2.text((60, 305), "CASING MAT:   ASTM A216 WCB", fill=(20, 20, 20))
    d2.text((380, 305), "IMPELLER:     12% CR CS", fill=(20, 20, 20))
    img2.save(nameplate_path, format="JPEG", quality=95)

    with open(nameplate_path, "rb") as f:
        h2 = hashlib.sha256(f.read()).hexdigest()

    manifest.append({
        "sha256": h2,
        "fixture_id": "SULZER_PUMP_NAMEPLATE",
        "equipment_id": "P-101",
        "version": "1.0",
        "filename": nameplate_file,
        "description": "Sulzer API 610 BB2 Centrifugal Pump metallic rating plate with design limits",
        "mime_type": "image/jpeg"
    })

    # 3. Flange Pitting Corrosion
    flange_file = "flange_corrosion.jpg"
    flange_path = os.path.join(fixture_dir, flange_file)
    img3 = Image.new("RGB", (640, 480), color=(140, 130, 120))
    d3 = ImageDraw.Draw(img3)
    d3.ellipse([80, 60, 560, 420], outline=(50, 45, 40), width=16)
    d3.ellipse([180, 140, 460, 340], outline=(70, 65, 60), width=12)
    d3.rectangle([160, 170, 420, 360], fill=(85, 45, 30), outline=(180, 60, 20), width=2)
    d3.text((180, 190), "LOCALIZED PITTING CORROSION", fill=(255, 180, 60))
    d3.text((180, 215), "4-INCH ANSI 300# FLANGE NECK", fill=(240, 240, 240))
    img3.save(flange_path, format="JPEG", quality=95)

    with open(flange_path, "rb") as f:
        h3 = hashlib.sha256(f.read()).hexdigest()

    manifest.append({
        "sha256": h3,
        "fixture_id": "FLANGE_PITTING_CORROSION",
        "equipment_id": "E-101",
        "version": "1.0",
        "filename": flange_file,
        "description": "Localized pitting corrosion on 4-inch ANSI 300# Carbon Steel flange neck",
        "mime_type": "image/jpeg"
    })

    # 4. Motor Stator Scorch
    stator_file = "motor_stator.jpg"
    stator_path = os.path.join(fixture_dir, stator_file)
    img4 = Image.new("RGB", (640, 480), color=(80, 80, 90))
    d4 = ImageDraw.Draw(img4)
    d4.rectangle([130, 90, 510, 390], fill=(40, 30, 25), outline=(220, 90, 20), width=4)
    d4.text((160, 140), "MOTOR M-101 STATOR WINDING", fill=(255, 210, 70))
    d4.text((160, 170), "THERMAL VARNISH CARBONIZATION", fill=(230, 230, 230))
    img4.save(stator_path, format="JPEG", quality=95)

    with open(stator_path, "rb") as f:
        h4 = hashlib.sha256(f.read()).hexdigest()

    manifest.append({
        "sha256": h4,
        "fixture_id": "MOTOR_STATOR_SCORCH",
        "equipment_id": "M-101",
        "version": "1.0",
        "filename": stator_file,
        "description": "Thermal varnish carbonization and hot spot on 415V motor stator windings",
        "mime_type": "image/jpeg"
    })

    # Write manifest.json
    manifest_path = os.path.join(fixture_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)

    return manifest


if __name__ == "__main__":
    items = build_golden_vision_fixtures()
    print(f"Built {len(items)} golden fixtures with manifest.json:")
    for item in items:
        print(f"  [{item['fixture_id']}] SHA-256: {item['sha256']} ({item['filename']})")
