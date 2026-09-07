"""
Field-Level RBAC Filtering for CLORA Deliverables.
Enforces that user role comes strictly from authenticated context,
filtering sensitive fields (financial amounts, approval blocks) before rendering.
"""
from __future__ import annotations

from typing import Dict, Any, List, Set

from app.ai.rbac import UserRole, RBACManager


ROLE_FIELD_ALLOWLIST: Dict[UserRole, Set[str]] = {
    UserRole.GUEST: {"investigation_id", "created_at", "status"},
    UserRole.FIELD_TECHNICIAN: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "evidence_support_score",
    },
    UserRole.OPERATOR: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "evidence_support_score",
    },
    UserRole.MAINTENANCE_ENGINEER: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "root_cause",
        "claims_matrix", "evidence_support_score", "recommended_action",
    },
    UserRole.LEAD_PROCESS_ENGINEER: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "root_cause",
        "claims_matrix", "evidence_support_score", "recommended_action",
        "financial_estimate",
    },
    UserRole.OPERATIONS_SUPERVISOR: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "root_cause",
        "claims_matrix", "evidence_support_score", "recommended_action",
        "financial_estimate", "signoff_block",
    },
    UserRole.PLANT_DIRECTOR: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "root_cause",
        "claims_matrix", "evidence_support_score", "recommended_action",
        "financial_estimate", "signoff_block", "audit_chain", "budget_sanction",
    },
    UserRole.CHIEF_SANCTION_OFFICER: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "root_cause",
        "claims_matrix", "evidence_support_score", "recommended_action",
        "financial_estimate", "signoff_block", "audit_chain", "budget_sanction",
    },
    UserRole.ADMIN: {
        "investigation_id", "trace_id", "created_at", "equipment_tag",
        "telemetry", "thresholds", "inspection_steps", "root_cause",
        "claims_matrix", "evidence_support_score", "recommended_action",
        "financial_estimate", "signoff_block", "audit_chain", "budget_sanction",
    },
}


class DeliverableRBACFilter:
    """Filters manifest content based on the authenticated requester role."""

    @classmethod
    def filter_manifest_for_role(cls, manifest: Dict[str, Any], role_str: str) -> Dict[str, Any]:
        role = RBACManager.resolve_role(role_str)
        allowed_fields = ROLE_FIELD_ALLOWLIST.get(role, ROLE_FIELD_ALLOWLIST[UserRole.GUEST])

        filtered = dict(manifest)
        # Ensure role is explicitly bound from context, not manifest
        filtered["requester_role"] = role.value

        # Mask financial sanction if not authorized
        if "financial_estimate" not in allowed_fields:
            sanction = dict(filtered.get("sanction_proposal", {}))
            sanction["financial_estimate_inr"] = "[RESTRICTED - AUTHORIZED ROLES ONLY]"
            filtered["sanction_proposal"] = sanction

        # Mask sign-off block if not authorized
        if "signoff_block" not in allowed_fields:
            filtered["human_approval_allowed"] = False
        else:
            filtered["human_approval_allowed"] = True

        # Mask audit chain head if not authorized
        if "audit_chain" not in allowed_fields:
            filtered["audit_chain_head"] = "[RESTRICTED - AUDITOR / DIRECTOR ONLY]"

        return filtered
