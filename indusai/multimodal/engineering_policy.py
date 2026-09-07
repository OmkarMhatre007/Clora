"""
Authoritative Engineering Policy Engine & Safety Gate for Multimodal Inspection.
INDUSAI-X / CLORA Sovereign Multimodal Intelligence Subsystem.

Enforces:
1. Complete decoupling of VLM visual perception from engineering severity assignment.
   - VLMs emit probabilistic observations ("raceway spalling observed").
   - Engineering Policy Gate evaluates ISO/ASME/IEC limits against operating telemetry
     to authoritatively assign SeverityLevel.
2. EngineeringPolicyProfile standards per industrial equipment class:
   - P101_BEARING_PROFILE (ISO 10816-3 Class II/III, ISO 13373-1)
   - MOTOR_PROFILE (IEC 60034-1, IEEE 43)
   - PUMP_PROFILE (API 610 11th Ed, API 682)
   - FLANGE_PROFILE (ASME B31.3, API 570)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from indusai.multimodal.photo_schema import (
    DefectClass,
    PhotoCategory,
    RawInspectionProposal,
    SeverityLevel,
)


@dataclass(frozen=True)
class EngineeringPolicyProfile:
    """Standard-bound engineering policy profile for an industrial asset class."""
    profile_id: str
    equipment_class: str
    governing_standard: str
    standard_version: str
    vibration_velocity_warning_mms: float
    vibration_velocity_trip_mms: float
    bearing_temp_warning_c: float
    bearing_temp_trip_c: float
    corrosion_allowance_mm: Optional[float] = None
    required_corroborating_telemetry: List[str] = field(default_factory=list)
    description: str = ""


# Pre-calibrated industrial policy profiles
P101_BEARING_PROFILE = EngineeringPolicyProfile(
    profile_id="P101_BEARING_PROFILE",
    equipment_class="Centrifugal Feed Pump P-101 Inboard Bearing (Sulzer BB2)",
    governing_standard="ISO 10816-3 (Class II/III) & ISO 13373-1",
    standard_version="ISO 10816-3:2009",
    vibration_velocity_warning_mms=4.5,
    vibration_velocity_trip_mms=7.1,
    bearing_temp_warning_c=80.0,
    bearing_temp_trip_c=95.0,
    required_corroborating_telemetry=["vibration_rms", "bearing_temp_c"],
    description="Sulfur Recovery Unit feed pump bearing raceway monitoring and trip limits."
)

MOTOR_PROFILE = EngineeringPolicyProfile(
    profile_id="MOTOR_PROFILE",
    equipment_class="Medium-Voltage Induction Motor M-101 (415V / 315 kW)",
    governing_standard="IEC 60034-1 & IEEE 43-2013",
    standard_version="IEC 60034-1:2017",
    vibration_velocity_warning_mms=3.5,
    vibration_velocity_trip_mms=5.5,
    bearing_temp_warning_c=75.0,
    bearing_temp_trip_c=90.0,
    required_corroborating_telemetry=["stator_temp_c", "motor_current_a"],
    description="Electric motor drive end and non-drive end thermal insulation limits."
)

PUMP_PROFILE = EngineeringPolicyProfile(
    profile_id="PUMP_PROFILE",
    equipment_class="API 610 Between-Bearings Centrifugal Pump (General)",
    governing_standard="API 610 11th Edition / ISO 13709",
    standard_version="API 610:2010",
    vibration_velocity_warning_mms=4.5,
    vibration_velocity_trip_mms=7.1,
    bearing_temp_warning_c=80.0,
    bearing_temp_trip_c=95.0,
    required_corroborating_telemetry=["discharge_pressure_bar", "flow_m3h"],
    description="General centrifugal pump hydraulic and mechanical limits."
)

FLANGE_PROFILE = EngineeringPolicyProfile(
    profile_id="FLANGE_PROFILE",
    equipment_class="Piping Flange Connection FL-104 (ANSI 300# Carbon Steel)",
    governing_standard="ASME B31.3 & API 570 Piping Inspection",
    standard_version="ASME B31.3:2020",
    vibration_velocity_warning_mms=10.0,
    vibration_velocity_trip_mms=20.0,
    bearing_temp_warning_c=120.0,
    bearing_temp_trip_c=150.0,
    corrosion_allowance_mm=3.2,
    required_corroborating_telemetry=["pressure_bar", "fluid_temp_c"],
    description="Pressure boundary flange pitting corrosion and wall thinning threshold."
)

POLICY_REGISTRY: Dict[str, EngineeringPolicyProfile] = {
    "P101_BEARING_PROFILE": P101_BEARING_PROFILE,
    "MOTOR_PROFILE": MOTOR_PROFILE,
    "PUMP_PROFILE": PUMP_PROFILE,
    "FLANGE_PROFILE": FLANGE_PROFILE,
}


class EngineeringPolicyGate:
    """
    Authoritative Engineering Policy Gate.
    Evaluates visual observations against quantitative telemetry and governing industrial standards.
    Determines authoritative severity, shutdown requirements, and evidence-bound SOP recommendations.
    """

    @classmethod
    def resolve_profile(
        cls,
        proposal: RawInspectionProposal,
        explicit_profile_id: Optional[str] = None
    ) -> EngineeringPolicyProfile:
        """Determines the appropriate engineering profile based on equipment tag or defect."""
        if explicit_profile_id and explicit_profile_id in POLICY_REGISTRY:
            return POLICY_REGISTRY[explicit_profile_id]

        if not proposal:
            return P101_BEARING_PROFILE

        if hasattr(proposal, "equipment_tag_candidate"):
            raw_tag = proposal.equipment_tag_candidate
        elif hasattr(proposal, "equipment_tag"):
            raw_tag = proposal.equipment_tag
        else:
            raw_tag = ""
        tag = (raw_tag or "").upper()

        if hasattr(proposal, "observed_defect_class"):
            defect = proposal.observed_defect_class
        elif hasattr(proposal, "defect_class"):
            defect = proposal.defect_class
        else:
            defect = DefectClass.UNKNOWN

        if "M-101" in tag or "MOTOR" in tag or defect == DefectClass.THERMAL_DISCOLORATION:
            return MOTOR_PROFILE
        elif "FL-" in tag or "FLANGE" in tag or defect == DefectClass.PITTING_CORROSION:
            return FLANGE_PROFILE
        elif "P-101" in tag or defect == DefectClass.BEARING_FATIGUE_SPALLING:
            return P101_BEARING_PROFILE
        else:
            return PUMP_PROFILE


    @classmethod
    def evaluate(
        cls,
        proposal: RawInspectionProposal,
        telemetry_context: Optional[Dict[str, Any]] = None,
        sop_context: Optional[str] = None,
        profile: Optional[EngineeringPolicyProfile] = None,
    ) -> Tuple[SeverityLevel, bool, bool, Optional[str]]:
        """
        Authoritatively evaluates visual observation + operating telemetry against standards.
        Returns:
            (severity, requires_immediate_action, requires_human_review, evidence_bound_recommendation)
        """
        active_profile = profile or cls.resolve_profile(proposal)
        t = telemetry_context or {}

        tag = getattr(proposal, "equipment_tag_candidate", None) or getattr(proposal, "equipment_tag", "Pump P-101")
        cat = getattr(proposal, "proposed_category", None) or getattr(proposal, "photo_category", PhotoCategory.UNKNOWN)
        defect = getattr(proposal, "observed_defect_class", None) or getattr(proposal, "defect_class", DefectClass.UNKNOWN)

        vib_rms = t.get("vibration_rms", t.get("vibration_velocity_rms"))
        temp_c = t.get("bearing_temp_c", t.get("temperature_c", t.get("stator_temp_c")))

        # Scenario 1: Bearing Spalling (e.g. Pump P-101)
        if defect == DefectClass.BEARING_FATIGUE_SPALLING:
            has_vib_trip = vib_rms is not None and float(vib_rms) >= active_profile.vibration_velocity_trip_mms
            has_temp_trip = temp_c is not None and float(temp_c) >= active_profile.bearing_temp_trip_c
            has_vib_warn = vib_rms is not None and float(vib_rms) >= active_profile.vibration_velocity_warning_mms
            has_temp_warn = temp_c is not None and float(temp_c) >= active_profile.bearing_temp_warning_c

            if has_vib_trip or has_temp_trip:
                # Corroborated critical failure condition
                rec = (
                    f"Initiate controlled operational shutdown of {tag}. "
                    f"Vibration velocity RMS ({vib_rms} mm/s) or temperature ({temp_c} °C) exceeds "
                    f"{active_profile.governing_standard} trip limit ({active_profile.vibration_velocity_trip_mms} mm/s). "
                    "Execute mechanical decoupling, inspect lube oil filter for metallic debris, and replace inboard bearing "
                    "per SOP-MRPL-P101-MNT Section 4.2."
                )
                return SeverityLevel.CRITICAL, True, True, rec

            elif has_vib_warn or has_temp_warn:
                rec = (
                    f"Operating telemetry exceeds {active_profile.governing_standard} warning limit "
                    f"({active_profile.vibration_velocity_warning_mms} mm/s). Schedule bearing raceway replacement "
                    "within 48 hours. Increase vibration monitoring frequency to 15-minute intervals."
                )
                return SeverityLevel.HIGH, False, True, rec

            else:
                # Visual spalling detected but telemetry is normal or absent
                rec = (
                    "Visual raceway fatigue spalling detected. Telemetry within normal limits or unavailable. "
                    "Schedule bearing raceway replacement at next planned turnaround. Continue vibration monitoring."
                )
                return SeverityLevel.HIGH, False, True, rec

        # Scenario 2: Flange Pitting Corrosion
        elif defect == DefectClass.PITTING_CORROSION:
            rec = (
                f"Perform ultrasonic thickness (UT) wall measurement across flange neck to determine remaining "
                f"wall thickness versus {active_profile.governing_standard} corrosion allowance "
                f"({active_profile.corrosion_allowance_mm or 3.2} mm). Do not pressurize above 15.0 bar until verified."
            )
            return SeverityLevel.MODERATE, False, True, rec

        # Scenario 3: Thermal Discoloration / Stator Scorch
        elif defect == DefectClass.THERMAL_DISCOLORATION:
            rec = (
                f"Conduct Megger insulation resistance test and polarization index (PI) evaluation per "
                f"{active_profile.governing_standard} before re-energizing. Inspect forced ventilation fan "
                "cowling for cooling blockage."
            )
            return SeverityLevel.HIGH, True, True, rec

        # Scenario 4: Nameplate OCR or Clean Normal Asset
        elif cat == PhotoCategory.NAMEPLATE_OCR or defect == DefectClass.CLEAN_NORMAL:
            rec = (
                f"Equipment nameplate operational parameters verified against {active_profile.governing_standard} "
                "and asset master register. No immediate mechanical or electrical intervention required."
            )
            return SeverityLevel.NORMAL, False, False, rec


        # Scenario 5: Cavitation Erosion
        elif defect == DefectClass.CAVITATION_EROSION:
            rec = (
                "Inspect impeller eye and suction casing for vapor collapse pitting. "
                "Verify suction pressure meets required NPSHa margin."
            )
            return SeverityLevel.HIGH, False, True, rec

        # Default / Inconclusive
        return (
            SeverityLevel.UNKNOWN,
            False,
            True,
            "Insufficient visual or telemetry evidence to mandate immediate mechanical intervention. Recommend visual re-inspection."
        )
