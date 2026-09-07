"""
Canonical Data Contracts & Schemas for Multimodal Industrial Photograph Inspection.
INDUSAI-X / CLORA Sovereign Multimodal Intelligence Subsystem.
Strictly enforces separation between visual observation, deterministic validation,
engineering policy, and evidence trust state.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    NORMAL = "NORMAL"
    UNKNOWN = "UNKNOWN"


class InspectionStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAILED = "FAILED"


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CORROBORATED = "CORROBORATED"
    UNVERIFIED = "UNVERIFIED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    REJECTED = "REJECTED"


class SemanticType(str, Enum):
    OBSERVATION = "OBSERVATION"        # Raw visual observation
    INFERENCE = "INFERENCE"            # Logical deduction
    HYPOTHESIS = "HYPOTHESIS"          # Probabilistic causal candidate (never fact)
    RECOMMENDATION = "RECOMMENDATION"  # Evidence-bound action from authorized SOP


class FieldStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    ILLEGIBLE = "ILLEGIBLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONFLICTING = "CONFLICTING"


class PhotoCategory(str, Enum):
    DEFECT_INSPECTION = "DEFECT_INSPECTION"
    NAMEPLATE_OCR = "NAMEPLATE_OCR"
    EQUIPMENT_SURVEY = "EQUIPMENT_SURVEY"
    THERMAL_IMAGE = "THERMAL_IMAGE"
    GAUGE_READING = "GAUGE_READING"
    UNKNOWN = "UNKNOWN"


class DefectClass(str, Enum):
    BEARING_FATIGUE_SPALLING = "BEARING_FATIGUE_SPALLING"
    PITTING_CORROSION = "PITTING_CORROSION"
    FLANGE_LEAKAGE = "FLANGE_LEAKAGE"
    CAVITATION_EROSION = "CAVITATION_EROSION"
    THERMAL_DISCOLORATION = "THERMAL_DISCOLORATION"
    MECHANICAL_WEAR = "MECHANICAL_WEAR"
    CLEAN_NORMAL = "CLEAN_NORMAL"
    UNKNOWN = "UNKNOWN"


class NormalizedRegion(BaseModel):
    """
    Normalized bounding region coordinates [0.0 to 1.0].
    Strictly validates 0 <= xmin < xmax <= 1 and 0 <= ymin < ymax <= 1.
    """
    ymin: float = Field(ge=0.0, le=1.0)
    xmin: float = Field(ge=0.0, le=1.0)
    ymax: float = Field(ge=0.0, le=1.0)
    xmax: float = Field(ge=0.0, le=1.0)
    label: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "NormalizedRegion":
        if self.xmin >= self.xmax:
            raise ValueError(f"xmin ({self.xmin}) must be strictly less than xmax ({self.xmax})")
        if self.ymin >= self.ymax:
            raise ValueError(f"ymin ({self.ymin}) must be strictly less than ymax ({self.ymax})")
        return self

    def to_list(self) -> List[float]:
        return [round(self.ymin, 4), round(self.xmin, 4), round(self.ymax, 4), round(self.xmax, 4)]

    def to_pixel_box(self, width: int, height: int) -> Dict[str, int]:
        return {
            "x": int(round(self.xmin * width)),
            "y": int(round(self.ymin * height)),
            "width": max(1, int(round((self.xmax - self.xmin) * width))),
            "height": max(1, int(round((self.ymax - self.ymin) * height))),
        }


class VisualConfidenceVector(BaseModel):
    """
    Multi-factor confidence vector decomposing vision into distinct dimensions.
    """
    visual_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    classification_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    localization_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ocr_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    image_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)


class DomainValidation(BaseModel):
    """
    Deterministic domain rule verification. Not a statistical probability.
    """
    equipment_identified: bool = False
    measurement_valid: bool = False
    unit_valid: bool = False
    range_valid: bool = False
    source_consistent: bool = False
    status: Literal["VALID", "PARTIAL", "INVALID", "UNKNOWN"] = "UNKNOWN"
    details: List[str] = Field(default_factory=list)


class VisualProvenance(BaseModel):
    """
    Strictly immutable execution provenance envelope for forensic auditability.
    """
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    artifact_version: str = "1.0.0"
    content_hash: str
    image_dimensions: Dict[str, int] = Field(default_factory=lambda: {"width": 0, "height": 0})
    mime_type: str = "image/png"
    preprocessing_hash: str = ""
    model_id: str = "local_vlm"
    model_version: str = "1.0"
    prompt_version: str = "v1.0_forensics"
    inspection_id: str = ""
    execution_id: str = ""


class NameplateField(BaseModel):
    """Individual extracted field from an equipment rating plate."""
    field_name: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_region: Optional[NormalizedRegion] = None
    status: FieldStatus = FieldStatus.NOT_FOUND


class NameplateData(BaseModel):
    """Structured manufacturer specification extracted from rating plate."""
    manufacturer: Optional[NameplateField] = None
    model_number: Optional[NameplateField] = None
    serial_number: Optional[NameplateField] = None
    rated_power_kw: Optional[NameplateField] = None
    rated_speed_rpm: Optional[NameplateField] = None
    design_flow_m3h: Optional[NameplateField] = None
    max_pressure_bar: Optional[NameplateField] = None
    voltage_v: Optional[NameplateField] = None
    raw_fields: Dict[str, NameplateField] = Field(default_factory=dict)


class RawInspectionProposal(BaseModel):
    """
    Model-independent observation proposal emitted by a VLM or test fixture.
    Proposals represent candidate observations before validation and policy checks.
    """
    provider_id: str
    proposed_category: PhotoCategory = PhotoCategory.UNKNOWN
    equipment_tag_candidate: Optional[str] = None
    observed_defect_class: DefectClass = DefectClass.UNKNOWN
    observed_regions: List[NormalizedRegion] = Field(default_factory=list)
    raw_findings: List[str] = Field(default_factory=list)
    proposed_hypothesis: Optional[str] = None
    hypothesis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    nameplate_proposal: Optional[Dict[str, Any]] = None
    raw_ocr_text: Optional[str] = None
    raw_model_response: Optional[Dict[str, Any]] = None
    confidence_vector: VisualConfidenceVector = Field(default_factory=VisualConfidenceVector)


class VisualFinding(BaseModel):
    """Categorized visual finding with strict semantic typing."""
    finding_id: str
    semantic_type: SemanticType = SemanticType.OBSERVATION
    description: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    region: Optional[NormalizedRegion] = None
    corroboration_source: Optional[str] = None


class RootCauseHypothesis(BaseModel):
    """Probabilistic root-cause candidate. Explicitly labeled as HYPOTHESIS, never FACT."""
    hypothesis: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    semantic_type: SemanticType = SemanticType.HYPOTHESIS
    status: str = "HYPOTHESIS"
    contributing_factors: List[str] = Field(default_factory=list)


class ValidatedInspectionProposal(BaseModel):
    """
    Type Hierarchy Level 2: Schema- and geometry-validated proposal.
    Guarantees all bounding regions, tags, and nameplate data satisfy coordinate & type contracts.
    """
    provider_id: str
    photo_category: PhotoCategory = PhotoCategory.UNKNOWN
    equipment_tag: str = "UNKNOWN"
    observed_defect_class: DefectClass = DefectClass.UNKNOWN
    valid_regions: List[NormalizedRegion] = Field(default_factory=list)
    findings: List[VisualFinding] = Field(default_factory=list)
    nameplate_data: Optional[NameplateData] = None
    candidate_hypothesis: Optional[RootCauseHypothesis] = None
    confidence_vector: VisualConfidenceVector = Field(default_factory=VisualConfidenceVector)


class EngineeringAssessment(BaseModel):
    """
    Type Hierarchy Level 3: Deterministic engineering policy & domain evaluation.
    Evaluates validated observations against standards (e.g. ISO 10816-3) and telemetry.
    """
    severity: SeverityLevel = SeverityLevel.UNKNOWN
    requires_immediate_action: bool = False
    requires_human_review: bool = False
    inspection_status: InspectionStatus = InspectionStatus.INCONCLUSIVE
    evidence_status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    evidence_bound_recommendation: Optional[str] = None
    domain_validation: DomainValidation = Field(default_factory=DomainValidation)


class PhotographInspectionResult(BaseModel):
    """
    Type Hierarchy Level 4: Canonical authoritative inspection contract uniting
    validated observation + deterministic engineering assessment + immutable provenance.
    """
    inspection_id: str
    photo_category: PhotoCategory
    equipment_tag: str = "UNKNOWN"
    defect_detected: bool = False
    defect_class: DefectClass = DefectClass.UNKNOWN
    severity: SeverityLevel = SeverityLevel.UNKNOWN
    requires_immediate_action: bool = False
    requires_human_review: bool = False
    inspection_status: InspectionStatus = InspectionStatus.INCONCLUSIVE
    evidence_status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    confidence_vector: VisualConfidenceVector = Field(default_factory=VisualConfidenceVector)
    domain_validation: DomainValidation = Field(default_factory=DomainValidation)
    provenance: VisualProvenance
    bounding_regions: List[NormalizedRegion] = Field(default_factory=list)
    findings: List[VisualFinding] = Field(default_factory=list)
    nameplate_data: Optional[NameplateData] = None
    root_cause_hypothesis: Optional[RootCauseHypothesis] = None
    evidence_bound_recommendation: Optional[str] = None
    summary: str = ""
    validated_proposal: Optional[ValidatedInspectionProposal] = None
    engineering_assessment: Optional[EngineeringAssessment] = None

    def to_evidence(self) -> Any:
        """
        Converts the canonical visual inspection result into an authoritative
        first-class Evidence object for LangGraph EvidencePack and verification.
        """
        from backend.rag.evidence import Evidence

        # Build grounded text content
        lines = [
            f"[Visual Inspection: {self.photo_category.value}] Asset: {self.equipment_tag}",
            f"Inspection Status: {self.inspection_status.value} | Evidence Trust: {self.evidence_status.value}",
            f"Severity Assessment: {self.severity.value} (Immediate Action: {self.requires_immediate_action}, Human Review: {self.requires_human_review})",
        ]

        if self.defect_detected and self.defect_class != DefectClass.CLEAN_NORMAL:
            lines.append(f"Visual Defect: {self.defect_class.value}")

        for f in self.findings:
            region_str = f" @ Region {f.region.to_list()}" if f.region else ""
            lines.append(f"• [{f.semantic_type.value}] {f.description}{region_str} (Conf: {f.confidence:.2f})")

        if self.nameplate_data:
            lines.append("Extracted Nameplate Specifications:")
            if self.nameplate_data.model_number and self.nameplate_data.model_number.value:
                lines.append(f"  - Model: {self.nameplate_data.model_number.value} (Conf: {self.nameplate_data.model_number.confidence:.2f})")
            if self.nameplate_data.serial_number and self.nameplate_data.serial_number.value:
                lines.append(f"  - Serial: {self.nameplate_data.serial_number.value}")
            if self.nameplate_data.rated_power_kw and self.nameplate_data.rated_power_kw.value:
                lines.append(f"  - Rated Power: {self.nameplate_data.rated_power_kw.value} {self.nameplate_data.rated_power_kw.unit or 'kW'}")
            if self.nameplate_data.rated_speed_rpm and self.nameplate_data.rated_speed_rpm.value:
                lines.append(f"  - Rated Speed: {self.nameplate_data.rated_speed_rpm.value} {self.nameplate_data.rated_speed_rpm.unit or 'RPM'}")
            if self.nameplate_data.design_flow_m3h and self.nameplate_data.design_flow_m3h.value:
                lines.append(f"  - Design Flow: {self.nameplate_data.design_flow_m3h.value} {self.nameplate_data.design_flow_m3h.unit or 'm³/h'}")
            if self.nameplate_data.max_pressure_bar and self.nameplate_data.max_pressure_bar.value:
                lines.append(f"  - Max Pressure: {self.nameplate_data.max_pressure_bar.value} {self.nameplate_data.max_pressure_bar.unit or 'bar'}")

        if self.root_cause_hypothesis:
            lines.append(f"Hypothesis [Probabilistic]: {self.root_cause_hypothesis.hypothesis} (Confidence: {self.root_cause_hypothesis.confidence:.2f})")

        if self.evidence_bound_recommendation:
            lines.append(f"Action [Bound to SOP]: {self.evidence_bound_recommendation}")

        overall_conf = max(
            0.1,
            min(
                1.0,
                (
                    self.confidence_vector.visual_confidence * 0.4
                    + self.confidence_vector.classification_confidence * 0.3
                    + self.confidence_vector.image_quality_score * 0.3
                )
            )
        )

        return Evidence(
            evidence_id=f"vis_ev_{self.inspection_id}",
            content="\n".join(lines),
            source_document=f"Photograph Artifact: {self.provenance.artifact_id}",
            page_number=1,
            chunk_id=f"vis_chunk_{self.inspection_id}",
            relevance_score=round(overall_conf, 4),
            equipment_id=self.equipment_tag,
            section="Visual Inspection & Defect Forensics",
            metadata={
                "inspection_id": self.inspection_id,
                "photo_category": self.photo_category.value,
                "defect_class": self.defect_class.value,
                "severity": self.severity.value,
                "inspection_status": self.inspection_status.value,
                "evidence_status": self.evidence_status.value,
                "requires_immediate_action": self.requires_immediate_action,
                "requires_human_review": self.requires_human_review,
                "bounding_regions": [r.to_list() for r in self.bounding_regions],
                "confidence_vector": self.confidence_vector.model_dump(),
                "domain_validation": self.domain_validation.model_dump(),
                "provenance": self.provenance.model_dump(),
                "sha256_content_hash": self.provenance.content_hash,
            },
        )
