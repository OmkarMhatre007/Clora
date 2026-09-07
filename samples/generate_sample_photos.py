"""
Synthetic Industrial Photograph Generator for Test & Demo Environments.
INDUSAI-X / CLORA Sovereign Multimodal Intelligence Subsystem.

Generates reproducible, high-contrast sample images:
1. samples/photos/P101_Bearing_Spalling.png
2. samples/photos/Sulzer_Pump_Nameplate.png
3. samples/photos/Flange_Pitting_Corrosion.png
4. samples/photos/Motor_Stator_Scorch.png

Also provides a registry mapping dictionary of SHA-256 hashes to scenario keys.
"""

import os
import io
import hashlib
from typing import Dict, Tuple
from PIL import Image, ImageDraw, ImageFont


def generate_sample_photos(output_dir: str = "samples/photos") -> Dict[str, str]:
    """Generates synthetic test photographs and returns dict of {sha256_hash: scenario_key}."""
    os.makedirs(output_dir, exist_ok=True)
    hash_registry = {}

    # 1. Tier B Killer Scenario: P-101 Bearing Spalling
    p101_path = os.path.join(output_dir, "P101_Bearing_Spalling.png")
    img1 = Image.new("RGB", (640, 480), color=(180, 185, 190))
    d1 = ImageDraw.Draw(img1)
    # Bearing outer ring and inner raceway
    d1.ellipse([70, 40, 570, 440], outline=(70, 75, 80), width=18)
    d1.ellipse([160, 110, 480, 370], outline=(100, 105, 110), width=14)
    # Spalling defect zone (inner raceway)
    d1.rectangle([220, 140, 460, 320], fill=(60, 50, 40), outline=(210, 60, 30), width=3)
    d1.text((235, 155), "FATIGUE SPALLING ZONE", fill=(255, 200, 80))
    d1.text((235, 180), "Depth: ~1.2mm | Micro-cracks", fill=(240, 240, 240))
    d1.text((235, 205), "P-101 Inboard Cylindrical Roller", fill=(200, 200, 200))
    # Rollers
    for x in range(120, 540, 65):
        d1.rectangle([x, 60, x + 40, 100], fill=(130, 135, 140), outline=(40, 40, 40), width=2)
    img1.save(p101_path, format="PNG")

    with open(p101_path, "rb") as f:
        h1 = hashlib.sha256(f.read()).hexdigest()
    hash_registry[h1] = "P101_BEARING_SPALLING"

    # 2. Tier A Strongest Scenario: Sulzer BB2 Pump Nameplate
    sulzer_path = os.path.join(output_dir, "Sulzer_Pump_Nameplate.png")
    img2 = Image.new("RGB", (700, 500), color=(220, 220, 225))
    d2 = ImageDraw.Draw(img2)
    # Metallic plate border
    d2.rectangle([20, 20, 680, 480], fill=(235, 238, 242), outline=(30, 40, 60), width=6)
    d2.rectangle([35, 35, 665, 465], outline=(120, 130, 145), width=2)
    # Text headers & specs
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
    img2.save(sulzer_path, format="PNG")

    with open(sulzer_path, "rb") as f:
        h2 = hashlib.sha256(f.read()).hexdigest()
    hash_registry[h2] = "SULZER_PUMP_NAMEPLATE"

    # 3. Tier C Scenario: Flange Pitting Corrosion
    flange_path = os.path.join(output_dir, "Flange_Pitting_Corrosion.png")
    img3 = Image.new("RGB", (640, 480), color=(140, 130, 120))
    d3 = ImageDraw.Draw(img3)
    d3.ellipse([80, 60, 560, 420], outline=(50, 45, 40), width=16)
    d3.ellipse([180, 140, 460, 340], outline=(70, 65, 60), width=12)
    # Corrosion pits
    d3.rectangle([160, 170, 420, 360], fill=(85, 45, 30), outline=(180, 60, 20), width=2)
    d3.text((180, 190), "LOCALIZED PITTING CORROSION", fill=(255, 180, 60))
    d3.text((180, 215), "4-INCH ANSI 300# FLANGE NECK", fill=(240, 240, 240))
    img3.save(flange_path, format="PNG")

    with open(flange_path, "rb") as f:
        h3 = hashlib.sha256(f.read()).hexdigest()
    hash_registry[h3] = "FLANGE_PITTING_CORROSION"

    # 4. Tier D Scenario: Motor Stator Scorch
    stator_path = os.path.join(output_dir, "Motor_Stator_Scorch.png")
    img4 = Image.new("RGB", (640, 480), color=(80, 80, 90))
    d4 = ImageDraw.Draw(img4)
    d4.rectangle([130, 90, 510, 390], fill=(40, 30, 25), outline=(220, 90, 20), width=4)
    d4.text((160, 140), "MOTOR M-101 STATOR WINDING", fill=(255, 210, 70))
    d4.text((160, 170), "THERMAL VARNISH CARBONIZATION", fill=(230, 230, 230))
    img4.save(stator_path, format="PNG")

    with open(stator_path, "rb") as f:
        h4 = hashlib.sha256(f.read()).hexdigest()
    hash_registry[h4] = "MOTOR_STATOR_SCORCH"

    # Update CalibratedTestProvider FIXTURE_REGISTRY directly
    from indusai.multimodal.photo_inspector import CalibratedTestProvider
    CalibratedTestProvider.FIXTURE_REGISTRY.update(hash_registry)

    return hash_registry


if __name__ == "__main__":
    regs = generate_sample_photos()
    print(f"Generated {len(regs)} synthetic sample photographs.")
    for h, scen in regs.items():
        print(f"  SHA-256: {h[:16]}... -> Scenario: {scen}")
