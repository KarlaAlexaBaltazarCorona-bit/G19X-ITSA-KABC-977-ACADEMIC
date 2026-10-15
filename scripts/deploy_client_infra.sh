#!/usr/bin/env bash
# ==============================================================================
# PluriOne LegalTech - Despliegue Click-to-Go en Azure (Bash / Cloud Shell)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo "  PluriOne LegalTech - Despliegue Click-to-Go en Azure"
echo "=========================================================="

# 1. Verificar sesión en Azure CLI
if ! az account show > /dev/null 2>&1; then
    echo "Iniciando sesión en Azure..."
    az login --output none
fi

SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Suscripción activa: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"

# 2. Parámetros interactivos o por variables de entorno
RG_NAME="${1:-}"
LOCATION="${2:-eastus}"
ENV_TYPE="${3:-Standard}"
DB_PASSWORD="${4:-}"

if [ -z "$RG_NAME" ]; then
    read -rp "Ingresa el nombre del Resource Group (ej. rg-legaltech-prod): " RG_NAME
fi

if [ -z "$DB_PASSWORD" ]; then
    read -rsp "Ingresa contraseña segura para PostgreSQL (mínimo 8 caracteres, al menos 1 mayúscula y 1 número): " DB_PASSWORD
    echo ""
fi

# 3. Crear Resource Group
echo "Creando o verificando Resource Group '$RG_NAME' en '$LOCATION'..."
az group create --name "$RG_NAME" --location "$LOCATION" --output table

# 4. Desplegar plantilla ARM / Bicep
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_PATH="$SCRIPT_DIR/../infra/azuredeploy.json"

if [ ! -f "$TEMPLATE_PATH" ]; then
    TEMPLATE_PATH="$SCRIPT_DIR/../infra/main.bicep"
fi

echo "Aprovisionando infraestructura llave en mano (Perfil: $ENV_TYPE)..."
echo "Esto tomará aproximadamente 3 a 5 minutos. Azure está configurando y enlazando los 8 servicios..."

DEPLOY_OUTPUT=$(az deployment group create \
    --resource-group "$RG_NAME" \
    --template-file "$TEMPLATE_PATH" \
    --parameters \
        environmentType="$ENV_TYPE" \
        dbAdminPassword="$DB_PASSWORD" \
    --output json)

echo "=========================================================="
echo "  ¡DESPLIEGUE COMPLETADO CON ÉXITO!"
echo "=========================================================="

APP_URL=$(echo "$DEPLOY_OUTPUT" | jq -r '.properties.outputs.appServiceUrl.value // empty')
API_KEY=$(echo "$DEPLOY_OUTPUT" | jq -r '.properties.outputs.appApiKey.value // empty')
PG_SERVER=$(echo "$DEPLOY_OUTPUT" | jq -r '.properties.outputs.postgresServer.value // empty')
OAI_ENDPOINT=$(echo "$DEPLOY_OUTPUT" | jq -r '.properties.outputs.openAiEndpoint.value // empty')

echo "URL de la Aplicación:    $APP_URL"
echo "Servidor PostgreSQL:     $PG_SERVER"
echo "Azure OpenAI Endpoint:   $OAI_ENDPOINT"
echo "API Key Generada:        $API_KEY"
echo ""
echo "Todos los servicios quedaron interconectados automáticamente sin configuración manual."
