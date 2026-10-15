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

python @argsList
exit $LASTEXITCODE
