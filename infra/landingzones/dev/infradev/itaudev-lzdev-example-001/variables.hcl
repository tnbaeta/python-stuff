# file: 'C:\Users\tiagobaeta\Documents\PythonProjects\python-stuff\infra\landingzones\dev\infradev\itaudev-lzdev-example-001\variables.hcl'
# Subscription variables file for application 'Example1'

application_acronym = JT5
mandatory_tags = {
    "ApplicationName" = "example1"
    "CostCenter" = "12345-678"
    "DataClassification" = "Interna"
    "Environment" = "dev"
    "OwnerName" = "Tiago Baeta"
    "Sigla" = "jt5"
    "Squad" = "Redmond"
}
optional_tags = {
    "ApproverName" = "Tiago Baeta"
    "CreatedWith" = "DevOps"
    "RequesterName" = "Tiago Baeta"
    "NotificationEmail" = "tiagobaeta@microsoft.com"
    "ProductOwnerEmail" = "tiagobaeta@microsoft.com"
    "AccountType" = "App"
    "Escopo" = "Camada Zero"
}