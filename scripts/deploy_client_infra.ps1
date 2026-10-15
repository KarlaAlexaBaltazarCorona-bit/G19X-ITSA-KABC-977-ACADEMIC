<#
.SYNOPSIS
    Script de despliegue Click-to-Go para la entrega de infraestructura en Azure del cliente.
.DESCRIPTION
    Aprovisiona automáticamente todos los recursos de Azure (PostgreSQL, App Service, OpenAI,
    Document Intelligence, Blob Storage y AI Search) y enlaza las variables de entorno sin talacha manual.
.EXAMPLE
    .\scripts\deploy_client_infra.ps1 -ResourceGroupName "rg-plurione-prod" -Location "eastus" -EnvironmentType "Enterprise_HA"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false, HelpMessage = "Nombre del Resource Group a crear o usar")]
    [string]$ResourceGroupName = "",

    [Parameter(Mandatory = $false, HelpMessage = "Región de Azure (ej. eastus, mexicocentral)")]
    [string]$Location = "eastus",

    [Parameter(Mandatory = $false, HelpMessage = "Perfil de despliegue: Standard o Enterprise_HA")]
    [ValidateSet("Standard", "Enterprise_HA")]
    [string]$EnvironmentType = "Standard",

    [Parameter(Mandatory = $false, HelpMessage = "Contraseña maestra para PostgreSQL")]
    [string]$DbPassword = ""
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  PluriOne LegalTech - Despliegue Click-to-Go en Azure" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verificar sesión de Azure CLI
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Iniciando sesión en Azure..." -ForegroundColor Yellow
    az login --output none
    $account = az account show | ConvertFrom-Json
}
Write-Host "Suscripción activa: $($account.name) ($($account.id))" -ForegroundColor Green

# 2. Solicitar datos si no se pasaron como parámetros
if ([string]::IsNullOrWhiteSpace($ResourceGroupName)) {
    $ResourceGroupName = Read-Host "Ingresa el nombre del Resource Group (ej. rg-legaltech-prod)"
}
if ([string]::IsNullOrWhiteSpace($DbPassword)) {
    $securePass = Read-Host "Ingresa una contraseña segura para PostgreSQL (mínimo 8 caracteres, al menos 1 mayúscula y 1 número)" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    $DbPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# 3. Crear Resource Group si no existe
Write-Host "`nCreando o verificando Resource Group '$ResourceGroupName' en '$Location'..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location --output table

# 4. Desplegar plantilla ARM / Bicep
Write-Host "`nAprovisionando infraestructura llave en mano (Perfil: $EnvironmentType)..." -ForegroundColor Yellow
Write-Host "Esto tomará aproximadamente 3 a 5 minutos. Relájate mientras Azure hace todo el trabajo..." -ForegroundColor Gray

$templatePath = Join-Path $PSScriptRoot "..\infra\azuredeploy.json"
if (-not (Test-Path $templatePath)) {
    $templatePath = Join-Path $PSScriptRoot "..\infra\main.bicep"
}

$deployOutput = az deployment group create `
    --resource-group $ResourceGroupName `
    --template-file $templatePath `
    --parameters `
        environmentType=$EnvironmentType `
        dbAdminPassword=$DbPassword `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==========================================================" -ForegroundColor Green
    Write-Host "  ¡DESPLIEGUE COMPLETADO CON ÉXITO!" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green

    $outputs = $deployOutput.properties.outputs
    Write-Host "URL de la Aplicación:    $($outputs.appServiceUrl.value)" -ForegroundColor Cyan
    Write-Host "Servidor PostgreSQL:     $($outputs.postgresServer.value)" -ForegroundColor White
    Write-Host "Azure OpenAI Endpoint:   $($outputs.openAiEndpoint.value)" -ForegroundColor White
    Write-Host "Doc Intelligence:        $($outputs.docIntelEndpoint.value)" -ForegroundColor White
    Write-Host "API Key Generada:        $($outputs.appApiKey.value)" -ForegroundColor Yellow
    Write-Host "`nTodos los servicios quedaron interconectados automáticamente." -ForegroundColor Green
} else {
    Write-Host "`nSe presentó un error durante el despliegue. Revisa los logs de Azure Resource Manager." -ForegroundColor Red
}
