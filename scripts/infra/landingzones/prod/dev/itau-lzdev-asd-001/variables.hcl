# file: 'infra\landingzones\prod\dev\itau-lzdev-asd-001\variables.hcl'
# Subscription variables file for application 'Asd'

application_acronym = AS2
tags_mandatory = {'ApplicationName': 'Asd', 'CostCenter': 'as', 'DataClassification': 'Interna', 'Environment': 'prod', 'OwnerName': 'asd', 'Sigla': 'AS2', 'Squad': 'asd'}
tags_optional = {
    "ApproverName" = "asd"
    "CreatedWith" = "DevOps"
    "RequesterName" = "asd"
    "NotificationEmail" = "asd"
    "ProductOwnerEmail" = ""
    "AccountType" = "App"
}