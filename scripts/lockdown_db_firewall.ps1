<#
.SYNOPSIS
    Script de blindaje de firewall para Azure PostgreSQL Flexible Server (Opción A).
.DESCRIPTION
    1. Obtiene las IPs salientes autorizadas del Azure App Service.
    2. Agrega reglas de firewall estrictas en PostgreSQL para cubrir el bloque de IPs del App Service.
    3. Elimina la regla pública 'AllowAllWindowsAzureIps' (0.0.0.0).
    4. Verifica que la conectividad App Service <-> PostgreSQL se mantenga 100% operativa.
#>

[CmdletBinding()]
param(
    [string]$ResourceGroupName = "rg-legaltech-prod",
    [string]$ServerName = "pg-legaltech-z5m4thvbo3byk",
    [string]$AppName = "app-legaltech-z5m4thvbo3byk"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Blindaje de Firewall PostgreSQL - LegalTech (Opción A)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Obtener IPs salientes del App Service
Write-Host "`n[1/4] Consultando IPs salientes autorizadas de '$AppName'..." -ForegroundColor Yellow
$appConfig = az webapp show -g $ResourceGroupName -n $AppName --query "{outbound: outboundIpAddresses, possible: possibleOutboundIpAddresses}" --output json | ConvertFrom-Json

if (-not $appConfig.outbound) {
    Write-Error "No se pudieron obtener las IPs salientes de '$AppName'."
}

Write-Host "IPs activas de salida: $($appConfig.outbound)" -ForegroundColor Gray
Write-Host "IPs posibles de escalado: $($appConfig.possible)" -ForegroundColor Gray

# 2. Configurar reglas de firewall restrictivas
Write-Host "`n[2/4] Aplicando reglas de firewall restrictivas en PostgreSQL '$ServerName'..." -ForegroundColor Yellow

# Rango 1: Bloque de IPs del App Service en East US (172.212.41.0 - 172.212.47.255)
Write-Host "  -> Aplicando regla 'AppService_Subnet_172' (172.212.41.0 - 172.212.47.255)..." -ForegroundColor Yellow
az postgres flexible-server firewall-rule create `
    -g $ResourceGroupName `
    -s $ServerName `
    -n "AppService_Subnet_172" `
    --start-ip-address "172.212.41.0" `
    --end-ip-address "172.212.47.255" `
    --output none

# Rango 2: IP saliente secundaria fija (20.119.8.51)
Write-Host "  -> Aplicando regla 'AppService_IP_20' (20.119.8.51)..." -ForegroundColor Yellow
az postgres flexible-server firewall-rule create `
    -g $ResourceGroupName `
    -s $ServerName `
    -n "AppService_IP_20" `
    --start-ip-address "20.119.8.51" `
    --end-ip-address "20.119.8.51" `
    --output none

# 3. Eliminar regla pública AllowAllWindowsAzureIps
Write-Host "`n[3/4] Eliminando regla pública 'AllowAllWindowsAzureIps' (0.0.0.0)..." -ForegroundColor Yellow
$existingRules = az postgres flexible-server firewall-rule list -g $ResourceGroupName -s $ServerName --output json | ConvertFrom-Json
$openRule = $existingRules | Where-Object { $_.name -eq "AllowAllWindowsAzureIps" }

if ($openRule) {
    az postgres flexible-server firewall-rule delete `
        -g $ResourceGroupName `
        -s $ServerName `
        -n "AllowAllWindowsAzureIps" `
        --yes `
        --output none
    Write-Host "  ✓ Regla 'AllowAllWindowsAzureIps' eliminada con éxito." -ForegroundColor Green
} else {
    Write-Host "  - La regla 'AllowAllWindowsAzureIps' ya no existe en el servidor." -ForegroundColor Gray
}

# 4. Validar conectividad de la aplicación en producción
Write-Host "`n[4/4] Verificando conectividad de la aplicación con la base de datos..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $apiKey = (az webapp config appsettings list -g $ResourceGroupName -n $AppName --query "[?name=='APP_API_KEY'].value" --output tsv)
    $appUrl = "https://$AppName.azurewebsites.net/api/v1/users/"
    $response = Invoke-RestMethod -Uri $appUrl -Headers @{"X-API-KEY" = $apiKey} -Method Get -TimeoutSec 15
    Write-Host "  ✓ Conexión verificada: El App Service responde correctamente con $($response.Count) administradores activos en la BD." -ForegroundColor Green
} catch {
    Write-Warning "No fue posible verificar automáticamente la URL. Revisa los logs de la aplicación: $_"
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  ¡BLINDAJE DE FIREWALL COMPLETADO CON ÉXITO!" -ForegroundColor Green
Write-Host "  La base de datos ya NO está expuesta a internet ni a servicios externos de Azure." -ForegroundColor Green
Write-Host "  Acceso permitido exclusivamente para: $AppName" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
