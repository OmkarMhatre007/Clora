#!/usr/bin/env bash
# Idempotent Linux iptables rule creation for CLORA Outbound Deny
# Run with sudo / root privileges

RULE_COMMENT="CLORA_DENY_OUTBOUND"

if sudo iptables -C OUTPUT -m comment --comment "$RULE_COMMENT" -j DROP 2>/dev/null; then
    echo "[OK] iptables rule '$RULE_COMMENT' already exists."
else
    if sudo iptables -A OUTPUT -m comment --comment "$RULE_COMMENT" -j DROP; then
        echo "[OK] Successfully created iptables outbound deny rule: $RULE_COMMENT"
    else
        echo "[ERROR] Failed creating iptables rule (sudo required)."
        exit 1
    fi
fi
