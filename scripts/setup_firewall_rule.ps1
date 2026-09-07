# Idempotent Windows Firewall rule creation for CLORA Outbound Deny
# Run with Administrator privileges

$ruleName = "CLORA_DENY_OUTBOUND"
Write-Host "Checking for Windows Firewall rule: $ruleName..."

$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
    try {
        New-NetFirewallRule -DisplayName $ruleName `
            -Direction Outbound `
            -Action Block `
            -Profile Any `
            -Description "Enforces outbound network air-gap block for CLORA/INDUSAI-X sovereign demonstrations" `
            | Out-Null
        Write-Host "[OK] Successfully created outbound deny rule: $ruleName" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed creating firewall rule (Administrator privileges required): $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Firewall rule '$ruleName' already exists." -ForegroundColor Green
}
