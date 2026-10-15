@description('Prefijo para los nombres de los recursos aprovisionados.')
param appNamePrefix string = 'legaltech'

@description('Perfil de infraestructura: Standard (costo eficiente) o Enterprise_HA (Alta disponibilidad multizona, auto-scaling y redundancia).')
@allowed([
  'Standard'
  'Enterprise_HA'
])
param environmentType string = 'Standard'

@description('Región geográfica de Azure donde se desplegarán los recursos.')
param location string = resourceGroup().location

@description('Nombre de usuario administrador para la base de datos PostgreSQL Flexible Server.')
param dbAdminLogin string = 'adminjuridico'

@description('Contraseña maestra para PostgreSQL (mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula y 1 número).')
@secure()
param dbAdminPassword string

@description('API Key maestra opcional para control de acceso (X-API-KEY). Si se deja vacía, se autogenerará una segura.')
@secure()
param appApiKey string = ''

@description('Correo de la cuenta designada como administradora inicial de la plataforma.')
param initialAdminEmail string = 'isc221977@itsatlixco.edu.mx'

var uniqueSuffix = uniqueString(resourceGroup().id)
var isEnterprise = environmentType == 'Enterprise_HA'

var storageAccountName = take('st${replace(appNamePrefix, '-', '')}${uniqueSuffix}', 24)
var pgServerName = 'pg-${appNamePrefix}-${uniqueSuffix}'
var openaiName = 'oai-${appNamePrefix}-${uniqueSuffix}'
var docIntelName = 'di-${appNamePrefix}-${uniqueSuffix}'
var searchServiceName = 'srch-${appNamePrefix}-${uniqueSuffix}'
var appServicePlanName = 'asp-${appNamePrefix}-${uniqueSuffix}'
var appServiceName = 'app-${appNamePrefix}-${uniqueSuffix}'

var storageSku = isEnterprise ? 'Standard_ZRS' : 'Standard_LRS'
var pgSkuName = isEnterprise ? 'Standard_D2ds_v5' : 'Standard_B1ms'
var pgTier = isEnterprise ? 'GeneralPurpose' : 'Burstable'
var pgHaMode = isEnterprise ? 'ZoneRedundant' : 'Disabled'
var appServiceSku = isEnterprise ? 'P1v3' : 'B1'
var openAiCapacity = isEnterprise ? 100 : 50

var resolvedApiKey = empty(appApiKey) ? 'lt_${uniqueString(resourceGroup().id, deployment().name, 'apikey')}' : appApiKey
var resolvedEncryptionKey = base64(concat(uniqueString(resourceGroup().id, 'k1'), uniqueString(resourceGroup().id, 'k2'), '123456'))

// 1. Storage Account para documentos jurídicos
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageSku
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }

  resource blobService 'blobServices' = {
    name: 'default'
    resource container 'containers' = {
      name: 'documentos'
      properties: {
        publicAccess: 'None'
      }
    }
  }
}

// 2. Base de Datos PostgreSQL Flexible Server
resource pgServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: pgServerName
  location: location
  sku: {
    name: pgSkuName
    tier: pgTier
  }
  properties: {
    administratorLogin: dbAdminLogin
    administratorLoginPassword: dbAdminPassword
    version: '16'
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    highAvailability: {
      mode: pgHaMode
    }
  }

  resource database 'databases' = {
    name: 'legaltech_db'
    properties: {
      charset: 'UTF8'
      collation: 'en_US.utf8'
    }
  }

  resource firewallAzure 'firewallRules' = {
    name: 'AllowAllWindowsAzureIps'
    properties: {
      startIpAddress: '0.0.0.0'
      endIpAddress: '0.0.0.0'
    }
  }
}

// 3. Azure OpenAI Service con modelos gpt-5-mini y text-embedding
resource openAi 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openaiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openaiName
    publicNetworkAccess: 'Enabled'
  }

  resource gptDeployment 'deployments' = {
    name: 'gpt-5-mini'
    sku: {
      name: 'GlobalStandard'
      capacity: openAiCapacity
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: 'gpt-5-mini'
        version: '2025-08-07'
      }
      versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    }
  }

  resource embeddingDeployment 'deployments' = {
    name: 'text-embedding-3-small'
    dependsOn: [
      gptDeployment
    ]
    sku: {
      name: 'GlobalStandard'
      capacity: 1
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: 'text-embedding-3-small'
        version: '1'
      }
      versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    }
  }
}

// 4. Azure AI Document Intelligence (OCR)
resource docIntel 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: docIntelName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: docIntelName
    publicNetworkAccess: 'Enabled'
  }
}

// 5. Azure AI Search
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
  }
}

// 6. Plan de App Service (Linux)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  properties: {
    reserved: true
  }
  sku: {
    name: appServiceSku
  }
}

// 7. App Service (API Backend FastAPI + SQLAdmin)
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      appCommandLine: 'gunicorn --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker main:app'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'POSTGRES_URL'
          value: 'postgresql+psycopg2://${dbAdminLogin}:${dbAdminPassword}@${pgServer.properties.fullyQualifiedDomainName}:5432/legaltech_db?sslmode=require'
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: openAi.properties.endpoint
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: openAi.listKeys().key1
        }
        {
          name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
          value: 'gpt-5-mini'
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: '2024-08-01-preview'
        }
        {
          name: 'AZURE_OPENAI_MAX_TOKENS'
          value: '1000'
        }
        {
          name: 'AZURE_OPENAI_REASONING_EFFORT'
          value: 'low'
        }
        {
          name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'
          value: docIntel.properties.endpoint
        }
        {
          name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY'
          value: docIntel.listKeys().key1
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'AZURE_STORAGE_CONTAINER_NAME'
          value: 'documentos'
        }
        {
          name: 'AZURE_STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: 'https://${searchServiceName}.search.windows.net'
        }
        {
          name: 'AZURE_SEARCH_KEY'
          value: searchService.listAdminKeys().primaryKey
        }
        {
          name: 'APP_API_KEY'
          value: resolvedApiKey
        }
        {
          name: 'APP_ENCRYPTION_KEY'
          value: resolvedEncryptionKey
        }
        {
          name: 'RATE_LIMIT_ENABLED'
          value: 'true'
        }
        {
          name: 'RATE_LIMIT_PER_MINUTE'
          value: '2400'
        }
        {
          name: 'MAX_REQUEST_BODY_BYTES'
          value: '10485760'
        }
        {
          name: 'INITIAL_ADMIN_EMAIL'
          value: initialAdminEmail
        }
        {
          name: 'ENABLE_DOCS'
          value: 'false'
        }
      ]
    }
  }
}

output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output appApiKey string = resolvedApiKey
output postgresServer string = pgServer.properties.fullyQualifiedDomainName
output openAiEndpoint string = openAi.properties.endpoint
output docIntelEndpoint string = docIntel.properties.endpoint
