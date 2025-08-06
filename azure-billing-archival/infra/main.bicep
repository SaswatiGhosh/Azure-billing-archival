param location string = resourceGroup().location
param projectName string = 'billingarchival'
param cosmosDbName string = '${projectName}-cosmos'
param blobStorageName string = toLower('${projectName}storage')
param functionPlanName string = '${projectName}-plan'
param appInsightsName string = '${projectName}-ai'
param blobContainerName string = 'billing-archive'
param cosmosDbDatabaseName string = 'billing'
param cosmosDbContainerName string = 'records'
param cosmosPartitionKeyPath string = '/partitionKey'

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: blobStorageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: storage
  name: 'default/${blobContainerName}'
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosDbName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDb
  name: cosmosDbDatabaseName
  properties: {
    resource: {
      id: cosmosDbDatabaseName
    }
    options: {}
  }
}

resource cosmosContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDatabase
  name: cosmosDbContainerName
  properties: {
    resource: {
      id: cosmosDbContainerName
      partitionKey: {
        paths: [ cosmosPartitionKeyPath ]
        kind: 'Hash'
      }
    }
    options: {}
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource functionPlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: functionPlanName
  location: location
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
}

var functionApps = [
  'archival-function'
  'retrieval-function'
  'integrity-check-function'
]

resource functionAppsRes 'Microsoft.Web/sites@2022-03-01' = [for name in functionApps: {
  name: '${projectName}-${name}'
  location: location
  kind: 'functionapp'
  properties: {
    serverFarmId: functionPlan.id
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storage.listKeys().keys[0].value
        }
        {
          name: 'BLOB_CONN_STR'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'BLOB_CONTAINER_NAME'
          value: blobContainerName
        }
        {
          name: 'COSMOS_URL'
          value: cosmosDb.properties.documentEndpoint
        }
        {
          name: 'COSMOS_KEY'
          value: listKeys(cosmosDb.id, '2023-04-15').primaryMasterKey
        }
        {
          name: 'COSMOS_DB_NAME'
          value: cosmosDbDatabaseName
        }
        {
          name: 'COSMOS_CONTAINER_NAME'
          value: cosmosDbContainerName
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
      ]
    }
  }
}]
