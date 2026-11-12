<#
.SYNOPSIS
    Script rápido para ejecutar la auditoría integral de ciberseguridad y OWASP en Windows.
.EXAMPLE
    .\audit.ps1
    .\audit.ps1 -SkipTests
    .\audit.ps1 -Fix
#>
param(
    [switch]$SkipTests,
    [switch]$Fix
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

$argsList = @("scripts/security_audit.py")
if ($SkipTests) { $argsList += "--skip-tests" }
if ($Fix) { $argsList += "--fix" }

$pyCmd = @("python")
$check = & python --version 2>&1
if ($LASTEXITCODE -ne 0 -or "$check" -like "*was not found*") {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        $pyCmd = @("py", "-3.11")
    }
}

if ($pyCmd.Length -gt 1) {
    & $pyCmd[0] $pyCmd[1] @argsList
} else {
    & $pyCmd[0] @argsList
}
exit $LASTEXITCODE
