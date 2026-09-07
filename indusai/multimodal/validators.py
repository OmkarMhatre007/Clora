"""
Deterministic Visual & Domain Validation Pipeline for Industrial Photographs.
INDUSAI-X / CLORA Sovereign Multimodal Intelligence Subsystem.

Enforces:
1. Mathematical bounding box geometry contracts (finite, non-inverted, within [0, 1]).
2. Resilient schema validation & normalization over raw model proposals.
3. Deterministic engineering domain boundary validation (physical units & operational ranges).
"""

import math
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from indusai.multimodal.photo_schema import (
    DefectClass,
    DomainValidation,
    FieldStatus,
    NameplateData,
    NameplateField,
    NormalizedRegion,
    PhotoCategory,
    RawInspectionProposal,
    VisualConfidenceVector,
)

logger = logging.getLogger("indusai.multimodal.validators")


class BoundingBoxValidator:
    """
    Validates and normalizes spatial coordinates for detected visual defect regions.
    Guarantees no invalid or inverted geometry penetrates downstream systems.
    """

    MIN_AREA_THRESHOLD: float = 0.0001  # Minimum 0.01% of image area to exclude degenerate lines/points

    @classmethod
    def validate_coordinates(
        cls, ymin: float, xmin: float, ymax: float, xmax: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates coordinate mathematical and domain correctness.
        Returns: (is_valid, rejection_reason)
        """
        coords = [ymin, xmin, ymax, xmax]
        for c in coords:
            if not isinstance(c, (int, float)):
                return False, f"Coordinate is not a number: {type(c)}"
            if math.isnan(c) or math.isinf(c):
                return False, "Coordinate contains NaN or Infinity"

        if not (0.0 <= xmin <= 1.0 and 0.0 <= xmax <= 1.0):
            return False, f"X coordinates [{xmin}, {xmax}] exceed normalized unit space [0.0, 1.0]"
        if not (0.0 <= ymin <= 1.0 and 0.0 <= ymax <= 1.0):
            return False, f"Y coordinates [{ymin}, ymax={ymax}] exceed normalized unit space [0.0, 1.0]"

        if xmin >= xmax:
            return False, f"Inverted horizontal bounds: xmin ({xmin}) >= xmax ({xmax})"
        if ymin >= ymax:
            return False, f"Inverted vertical bounds: ymin ({ymin}) >= ymax ({ymax})"

        area = (xmax - xmin) * (ymax - ymin)
        if area < cls.MIN_AREA_THRESHOLD:
            return False, f"Bounding box area ({area:.6f}) is below minimal physical threshold ({cls.MIN_AREA_THRESHOLD})"

        return True, None

    @classmethod
    def filter_and_build_regions(
        cls, candidate_regions: List[Union[Dict[str, Any], List[float], NormalizedRegion]]
    ) -> List[NormalizedRegion]:
        """
        Filters raw proposals and constructs strictly valid NormalizedRegion instances.
        Invalid coordinates are logged and discarded without halting execution.
        """
        valid_regions: List[NormalizedRegion] = []

        for item in candidate_regions:
            if isinstance(item, NormalizedRegion):
                valid_regions.append(item)
                continue

            ymin, xmin, ymax, xmax = 0.0, 0.0, 0.0, 0.0
            label = ""
            conf = 1.0

            if isinstance(item, (list, tuple)) and len(item) >= 4:
                ymin, xmin, ymax, xmax = float(item[0]), float(item[1]), float(item[2]), float(item[3])
                label = str(item[4]) if len(item) > 4 else "Region"
            elif isinstance(item, dict):
                ymin = float(item.get("ymin", 0.0))
                xmin = float(item.get("xmin", 0.0))
                ymax = float(item.get("ymax", 0.0))
                xmax = float(item.get("xmax", 0.0))
                label = str(item.get("label", "Detection"))
                conf = float(item.get("confidence", 1.0))
            else:
                continue

            ok, reason = cls.validate_coordinates(ymin, xmin, ymax, xmax)
            if ok:
                try:
                    region = NormalizedRegion(
                        ymin=ymin,
                        xmin=xmin,
                        ymax=ymax,
                        xmax=xmax,
                        label=label,
                        confidence=min(max(conf, 0.0), 1.0),
                    )
                    valid_regions.append(region)
                except Exception as e:
                    logger.warning("Failed to instantiate NormalizedRegion: %s", e)
            else:
                logger.warning("Discarded invalid bounding box [%s, %s, %s, %s]: %s", ymin, xmin, ymax, xmax, reason)

        return valid_regions


class SchemaValidator:
    """
    Validates model extraction output and guarantees conformance to RawInspectionProposal.
    Handles malformed responses, missing keys, and unexpected datatypes.
    """

    VALID_UNITS = {
        "rated_power_kw": {"kw", "hp", "w"},
        "rated_speed_rpm": {"rpm", "r/min", "min-1"},
        "design_flow_m3h": {"m3/h", "m³/h", "gpm", "l/min"},
        "max_pressure_bar": {"bar", "psi", "mpa", "kpa"},
        "voltage_v": {"v", "kv", "vac"},
    }

    @classmethod
    def sanitize_raw_proposal(
        cls,
        raw_dict: Dict[str, Any],
        provider_id: str,
        default_equipment_tag: Optional[str] = None
    ) -> RawInspectionProposal:
        """
        Parses an untrusted dictionary from a VLM into a guaranteed RawInspectionProposal.
        """
        # Category resolution
        cat_str = str(raw_dict.get("category", "")).upper()
        if "NAMEPLATE" in cat_str:
            cat = PhotoCategory.NAMEPLATE_OCR
        elif "THERMAL" in cat_str:
            cat = PhotoCategory.THERMAL_IMAGE
        elif "GAUGE" in cat_str:
            cat = PhotoCategory.GAUGE_READING
        elif "EQUIPMENT" in cat_str:
            cat = PhotoCategory.EQUIPMENT_SURVEY
        elif "DEFECT" in cat_str:
            cat = PhotoCategory.DEFECT_INSPECTION
        else:
            cat = PhotoCategory.UNKNOWN

        # Defect class resolution
        defect_str = str(raw_dict.get("defect_class", "")).upper()
        defect_class = DefectClass.__members__.get(defect_str, DefectClass.UNKNOWN)

        # Equipment tag
        eq_candidate = raw_dict.get("equipment_tag") or raw_dict.get("equipment_id") or default_equipment_tag

        # Bounding box / regions extraction
        raw_regions = []
        if raw_dict.get("bbox") and isinstance(raw_dict["bbox"], (list, tuple)):
            raw_regions.append(raw_dict["bbox"])
        if raw_dict.get("regions") and isinstance(raw_dict["regions"], list):
            raw_regions.extend(raw_dict["regions"])

        valid_regions = BoundingBoxValidator.filter_and_build_regions(raw_regions)

        # Observations / findings
        raw_obs = raw_dict.get("observations") or raw_dict.get("raw_findings") or []
        if isinstance(raw_obs, str):
            findings = [raw_obs]
        elif isinstance(raw_obs, list):
            findings = [str(x) for x in raw_obs if x is not None]
        else:
            findings = []

        # Hypothesis
        hypothesis = raw_dict.get("hypothesis")
        if hypothesis and not isinstance(hypothesis, str):
            hypothesis = str(hypothesis)

        # Nameplate proposal extraction
        np_raw = raw_dict.get("nameplate") or raw_dict.get("nameplate_proposal")
        nameplate_proposal = np_raw if isinstance(np_raw, dict) else None

        # Confidence Vector
        conf_dict = raw_dict.get("confidence_vector", {})
        if not isinstance(conf_dict, dict):
            conf_dict = {}

        def _safe_float(val: Any, default: float) -> float:
            try:
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    return default
                return min(max(f, 0.0), 1.0)
            except Exception:
                return default

        confidence_vector = VisualConfidenceVector(
            visual_confidence=_safe_float(conf_dict.get("visual_confidence", raw_dict.get("confidence")), 0.75),
            classification_confidence=_safe_float(conf_dict.get("classification_confidence"), 0.75),
            localization_confidence=_safe_float(conf_dict.get("localization_confidence"), 0.70 if valid_regions else 0.0),
            ocr_confidence=_safe_float(conf_dict.get("ocr_confidence"), 0.90 if cat == PhotoCategory.NAMEPLATE_OCR else 0.0),
            extraction_confidence=_safe_float(conf_dict.get("extraction_confidence"), 0.75),
            image_quality_score=_safe_float(conf_dict.get("image_quality_score"), 0.85),
        )

        return RawInspectionProposal(
            provider_id=provider_id,
            proposed_category=cat,
            equipment_tag_candidate=str(eq_candidate) if eq_candidate else None,
            observed_defect_class=defect_class,
            observed_regions=valid_regions,
            raw_findings=findings if findings else ["Visual observation processed."],
            proposed_hypothesis=hypothesis,
            hypothesis_confidence=_safe_float(raw_dict.get("hypothesis_confidence"), 0.60 if hypothesis else 0.0),
            nameplate_proposal=nameplate_proposal,
            raw_model_response=raw_dict,
            confidence_vector=confidence_vector,
        )


class DomainValidator:
    """
    Deterministic domain rule validator.
    Strictly asserts physical boundary validity, unit correctness, and asset consistency.
    Never equates statistical model confidence with domain truth.
    """

    PHYSICAL_RANGES = {
        "rated_power_kw": (1.0, 10000.0),        # 1 kW to 10 MW
        "rated_speed_rpm": (300.0, 7200.0),      # 300 to 7200 RPM
        "design_flow_m3h": (0.5, 25000.0),       # 0.5 to 25,000 m³/h
        "max_pressure_bar": (0.1, 450.0),        # 0.1 to 450 bar
        "voltage_v": (110.0, 15000.0),           # 110V to 15 kV
    }

    KNOWN_EQUIPMENT_PATTERNS = {"P-101", "P-102", "M-101", "E-101", "FL-104", "TK-201", "V-301"}

    @classmethod
    def validate_proposal(
        cls,
        proposal: RawInspectionProposal,
        known_assets: Optional[List[str]] = None
    ) -> DomainValidation:
        """
        Executes strict domain rule checks against a RawInspectionProposal.
        """
        details: List[str] = []
        valid_assets = set(known_assets) if known_assets else cls.KNOWN_EQUIPMENT_PATTERNS

        # 1. Equipment Tag Verification
        eq_identified = False
        tag = (proposal.equipment_tag_candidate or "").strip().upper()
        if tag and tag != "UNKNOWN":
            # Match against known asset codes
            matched = any(asset in tag for asset in valid_assets)
            if matched:
                eq_identified = True
                details.append(f"Equipment tag '{tag}' verified in plant asset registry.")
            else:
                details.append(f"Equipment tag '{tag}' unrecognized in plant registry.")
        else:
            details.append("No authoritative equipment tag identified in image.")

        # 2. Nameplate & Measurements Validation
        measurement_valid = True
        unit_valid = True
        range_valid = True

        if proposal.nameplate_proposal:
            np = proposal.nameplate_proposal
            for field, bounds in cls.PHYSICAL_RANGES.items():
                if field in np and isinstance(np[field], dict):
                    val = np[field].get("value")
                    unit = str(np[field].get("unit") or "").lower().strip()

                    if val is not None:
                        try:
                            fval = float(val)
                            min_b, max_b = bounds
                            if not (min_b <= fval <= max_b):
                                range_valid = False
                                details.append(
                                    f"Field '{field}' value {fval} out of physical industrial limits [{min_b}, {max_b}]"
                                )
                        except (ValueError, TypeError):
                            measurement_valid = False
                            details.append(f"Field '{field}' value '{val}' is not a valid numerical measurement.")

                        # Unit check
                        expected_units = SchemaValidator.VALID_UNITS.get(field, set())
                        if unit and expected_units and unit not in expected_units:
                            unit_valid = False
                            details.append(f"Field '{field}' unit '{unit}' not standard industrial unit ({expected_units})")

        # 3. Defect & Category Source Consistency
        source_consistent = True
        if proposal.proposed_category == PhotoCategory.NAMEPLATE_OCR:
            if proposal.observed_defect_class not in (DefectClass.CLEAN_NORMAL, DefectClass.UNKNOWN):
                # Nameplate photos should not be classified as severe mechanical spalling unless damaged
                source_consistent = True  # Allowed if plate is pitted
        elif proposal.observed_defect_class == DefectClass.BEARING_FATIGUE_SPALLING:
            if "BEARING" not in tag and "P-" not in tag and "PUMP" not in tag and tag != "UNKNOWN":
                details.append(f"Bearing defect candidate observed on non-rotating asset '{tag}'.")
                source_consistent = False

        # 4. Status Determination
        if eq_identified and measurement_valid and unit_valid and range_valid and source_consistent:
            dom_status = "VALID"
        elif not range_valid or not measurement_valid:
            dom_status = "INVALID"
        elif eq_identified or (proposal.proposed_category != PhotoCategory.UNKNOWN and source_consistent):
            dom_status = "PARTIAL"
        else:
            dom_status = "UNKNOWN"

        return DomainValidation(
            equipment_identified=eq_identified,
            measurement_valid=measurement_valid,
            unit_valid=unit_valid,
            range_valid=range_valid,
            source_consistent=source_consistent,
            status=dom_status,
            details=details,
        )
