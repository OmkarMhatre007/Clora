"""
RBAC Gateway, Refinery Role Mapping & Tool Authorization Policy Enforcer for CLORA.
Defaults unauthenticated sessions to NONE/GUEST and maps granular ModelPermissions
onto the 5-role refinery hierarchy.
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("indusai.rbac")


class UserRole(str, Enum):
    NONE = "NONE"
    GUEST = "GUEST"
    # Refinery Role Mappings
    FIELD_TECHNICIAN = "FIELD_TECHNICIAN"
    OPERATOR = "OPERATOR"  # Alias for FIELD_TECHNICIAN
    MAINTENANCE_ENGINEER = "MAINTENANCE_ENGINEER"
    LEAD_PROCESS_ENGINEER = "LEAD_PROCESS_ENGINEER"
    ENGINEER = "ENGINEER"  # Base engineering role
    OPERATIONS_SUPERVISOR = "OPERATIONS_SUPERVISOR"
    PLANT_DIRECTOR = "PLANT_DIRECTOR"
    CHIEF_SANCTION_OFFICER = "CHIEF_SANCTION_OFFICER"  # Alias for PLANT_DIRECTOR
    ADMIN = "ADMIN"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ModelPermission(str, Enum):
    VIEW = "model.view"
    DISCOVER = "model.discover"
    SWITCH = "model.switch"
    UNLOAD = "model.unload"
    REGISTER = "model.register"
    APPROVE = "model.approve"
    REVOKE = "model.revoke"
    PROVIDER_MANAGE = "provider.manage"


# Matrix of role permissions per document authorization tier
ROLE_DOCUMENT_PERMISSIONS: Dict[UserRole, List[str]] = {
    UserRole.NONE: [],
    UserRole.GUEST: ["public_notices"],
    UserRole.FIELD_TECHNICIAN: ["public_notices", "equipment_sop", "telemetry_logs"],
    UserRole.OPERATOR: ["public_notices", "equipment_sop", "telemetry_logs"],
    UserRole.MAINTENANCE_ENGINEER: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings"],
    UserRole.LEAD_PROCESS_ENGINEER: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings", "process_flow"],
    UserRole.ENGINEER: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings"],
    UserRole.OPERATIONS_SUPERVISOR: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings", "process_flow", "incident_reports"],
    UserRole.PLANT_DIRECTOR: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings", "budget_sanctions", "audit_trails", "system_config"],
    UserRole.CHIEF_SANCTION_OFFICER: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings", "budget_sanctions", "audit_trails"],
    UserRole.ADMIN: ["public_notices", "equipment_sop", "telemetry_logs", "maintenance_history", "engineering_drawings", "budget_sanctions", "audit_trails", "system_config"],
}

# Granular Model Management Permissions mapped to Refinery Roles
ROLE_MODEL_PERMISSIONS: Dict[UserRole, Set[ModelPermission]] = {
    UserRole.NONE: set(),
    UserRole.GUEST: {ModelPermission.VIEW},
    UserRole.FIELD_TECHNICIAN: {ModelPermission.VIEW},
    UserRole.OPERATOR: {ModelPermission.VIEW},
    UserRole.MAINTENANCE_ENGINEER: {
        ModelPermission.VIEW,
        ModelPermission.DISCOVER,
        ModelPermission.SWITCH,
    },
    UserRole.LEAD_PROCESS_ENGINEER: {
        ModelPermission.VIEW,
        ModelPermission.DISCOVER,
        ModelPermission.SWITCH,
    },
    UserRole.ENGINEER: {
        ModelPermission.VIEW,
        ModelPermission.DISCOVER,
        ModelPermission.SWITCH,
    },
    UserRole.OPERATIONS_SUPERVISOR: {
        ModelPermission.VIEW,
        ModelPermission.DISCOVER,
        ModelPermission.SWITCH,
        ModelPermission.UNLOAD,
        ModelPermission.REGISTER,
    },
    UserRole.PLANT_DIRECTOR: {
        ModelPermission.VIEW,
        ModelPermission.DISCOVER,
        ModelPermission.SWITCH,
        ModelPermission.UNLOAD,
        ModelPermission.REGISTER,
        ModelPermission.APPROVE,
        ModelPermission.REVOKE,
        ModelPermission.PROVIDER_MANAGE,
    },
    UserRole.CHIEF_SANCTION_OFFICER: {
        ModelPermission.VIEW,
        ModelPermission.DISCOVER,
        ModelPermission.SWITCH,
        ModelPermission.UNLOAD,
        ModelPermission.REGISTER,
        ModelPermission.APPROVE,
        ModelPermission.REVOKE,
        ModelPermission.PROVIDER_MANAGE,
    },
    UserRole.ADMIN: set(ModelPermission),
}

# Tool Risk & Approval Policy Matrix
TOOL_RISK_POLICY: Dict[str, Dict[str, Any]] = {
    "search_equipment_history": {
        "risk": RiskTier.LOW,
        "required_roles": [UserRole.OPERATOR, UserRole.FIELD_TECHNICIAN, UserRole.ENGINEER, UserRole.MAINTENANCE_ENGINEER, UserRole.LEAD_PROCESS_ENGINEER, UserRole.OPERATIONS_SUPERVISOR, UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": False,
    },
    "retrieve_sop": {
        "risk": RiskTier.LOW,
        "required_roles": [UserRole.OPERATOR, UserRole.FIELD_TECHNICIAN, UserRole.ENGINEER, UserRole.MAINTENANCE_ENGINEER, UserRole.LEAD_PROCESS_ENGINEER, UserRole.OPERATIONS_SUPERVISOR, UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": False,
    },
    "analyze_telemetry": {
        "risk": RiskTier.LOW,
        "required_roles": [UserRole.OPERATOR, UserRole.FIELD_TECHNICIAN, UserRole.ENGINEER, UserRole.MAINTENANCE_ENGINEER, UserRole.LEAD_PROCESS_ENGINEER, UserRole.OPERATIONS_SUPERVISOR, UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": False,
    },
    "check_threshold_breach": {
        "risk": RiskTier.MEDIUM,
        "required_roles": [UserRole.ENGINEER, UserRole.MAINTENANCE_ENGINEER, UserRole.LEAD_PROCESS_ENGINEER, UserRole.OPERATIONS_SUPERVISOR, UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": False,
    },
    "generate_audit_report": {
        "risk": RiskTier.MEDIUM,
        "required_roles": [UserRole.ENGINEER, UserRole.MAINTENANCE_ENGINEER, UserRole.LEAD_PROCESS_ENGINEER, UserRole.OPERATIONS_SUPERVISOR, UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": False,
    },
    "recommend_maintenance_action": {
        "risk": RiskTier.HIGH,
        "required_roles": [UserRole.ENGINEER, UserRole.MAINTENANCE_ENGINEER, UserRole.LEAD_PROCESS_ENGINEER, UserRole.OPERATIONS_SUPERVISOR, UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": True,
    },
    "execute_operational_action": {
        "risk": RiskTier.CRITICAL,
        "required_roles": [UserRole.CHIEF_SANCTION_OFFICER, UserRole.PLANT_DIRECTOR, UserRole.ADMIN],
        "human_approval": True,
    },
}


class RBACAuthorizationError(PermissionError):
    """Raised when an unauthorized role attempts document, tool, or model control plane access."""
    pass


class RBACManager:
    """Manages role resolution and pre-retrieval document access control."""

    @staticmethod
    def resolve_role(role_str: Optional[str]) -> UserRole:
        """Resolve a role string to UserRole. Defaults strictly to GUEST."""
        if not role_str:
            return UserRole.GUEST
        clean = role_str.upper().strip()
        try:
            return UserRole(clean)
        except ValueError:
            logger.warning("Unrecognized role '%s', defaulting to GUEST", role_str)
            return UserRole.GUEST

    @classmethod
    def filter_authorized_categories(cls, role: UserRole) -> List[str]:
        """Return authorized document categories for pre-retrieval filtering."""
        return ROLE_DOCUMENT_PERMISSIONS.get(role, [])

    @classmethod
    def is_document_authorized(cls, role: UserRole, category: str) -> bool:
        """Check if a specific document category is authorized for role."""
        allowed = cls.filter_authorized_categories(role)
        return category.lower() in [c.lower() for c in allowed]

    @classmethod
    def check_model_permission(cls, role: UserRole, permission: ModelPermission) -> bool:
        """Check if role holds a specific model control plane permission."""
        perms = ROLE_MODEL_PERMISSIONS.get(role, set())
        return permission in perms

    @classmethod
    def require_model_permission(cls, role: UserRole, permission: ModelPermission) -> None:
        """Enforce model permission; raise RBACAuthorizationError if missing."""
        if not cls.check_model_permission(role, permission):
            raise RBACAuthorizationError(
                f"Role '{role.value}' does not possess required permission '{permission.value}'."
            )


class ToolAuthorizationGateway:
    """Policy-Gated Gateway enforcing tool permissions, parameter validation, and human approval boundaries."""

    @classmethod
    def authorize_tool(cls, tool_name: str, role: UserRole, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate role permissions, risk tier, parameter structure, and human approval requirement."""
        if tool_name not in TOOL_RISK_POLICY:
            raise RBACAuthorizationError(f"Tool '{tool_name}' is not registered in security policy.")

        policy = TOOL_RISK_POLICY[tool_name]
        allowed_roles = policy["required_roles"]

        if role not in allowed_roles:
            raise RBACAuthorizationError(
                f"Role '{role.value}' is not authorized to invoke tool '{tool_name}'. Allowed: {[r.value for r in allowed_roles]}"
            )

        if not isinstance(parameters, dict):
            raise ValueError(f"Invalid parameters for tool '{tool_name}': must be a key-value dict.")

        return {
            "authorized": True,
            "tool": tool_name,
            "risk_tier": policy["risk"].value,
            "requires_human_approval": policy["human_approval"],
            "role": role.value,
        }
