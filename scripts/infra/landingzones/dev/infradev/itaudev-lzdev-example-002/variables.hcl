# file: 'infra\landingzones\dev\infradev\itaudev-lzdev-example-002\variables.hcl'
# Subscription variables file for application 'Example2'

application_acronym = JT3
tags_mandatory = {
    "ApplicationName" = "Example2"
    "CostCenter" = "123"
    "DataClassification" = "Interna"
    "Environment" = "dev"
    "OwnerName" = "Baeta"
    "Sigla" = "JT3"
    "Squad" = "Redmond"
}
tags_optional = {}