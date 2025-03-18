# file: 'infra\landingzones\dev\infradev\itaudev-lzdev-example-001\variables.hcl'
# Subscription variables file for application 'Example1'

application_acronym = JT4
tags_mandatory = {'ApplicationName': 'Example1', 'CostCenter': '123', 'DataClassification': 'Interna', 'Environment': 'dev', 'OwnerName': 'Baeta', 'Sigla': 'JT4', 'Squad': 'Redmond'}
tags_optional = {
    "ApproverName" = "Baeta"
    "CreatedWith" = "DevOps"
    "RequesterName" = "Baeta"
    "NotificationEmail" = "as"
    "ProductOwnerEmail" = ""
    "AccountType" = "App"
}