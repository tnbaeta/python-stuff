import json
import os
import re
from enum import Enum
from string import Template
from argparse import ArgumentParser


ENVIRONMENT_MENU = {
    "1": ("dev", "infradev"),
    "2": ("prod", "dev"),
    "3": ("prod", "hom"),
    "4": ("prod", "prod")
}
SILENT_MODE = {
    0: False,
    1: True
}
INPUTS_JSON_FILE = "templates/user-inputs.json"


class CustomJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        json_str = super().encode(obj)
        json_str = json_str.replace(":", " =")
        json_str = json_str.replace(",", "")

        return json_str


class SubscriptionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}"


class ErrorMessages(Enum):
    ENVIRONMENT_JSON = ("Combinação das entradas 'infrastructure_environment' e 'application_environment' inválida.\n"
                        "Valores válidos: 'dev e infradev', 'prod e dev', 'prod e hom' ou 'prod e prod'.\n"
                        "Corrija o arquivo de entrada de dados e tente novamente.")
    INFRASTRUCTURE_ENVIRONMENT_JSON = ("Entrada 'infrastructure_environment' inválida.\n"
                                       "Valores válidos: 'dev' ou 'prod'.\n"
                                       "Corrija o arquivo de entrada de dados e tente novamente.")
    APPLICATION_ENVIRONMENT_JSON = ("Entrada 'application_environment' inválida.\n"
                                   "Valores válidos: 'infradev', 'dev', 'hom' ou 'prod'.\n"
                                   "Corrija o arquivo de entrada de dados e tente novamente.")
    APPLICATION_NAME_INFRADEV_JSON = ("Nome de aplicação inválido para o ambiente de 'infradev'.\n"
                                      "O nome da aplicação para o ambiente de 'infradev' deve seguir o padrão "
                                      "'example' + 'número (1-999)'.\n"
                                      "Exemplos: 'example1', 'example23', 'example456'...\n"
                                      "Corrija o arquivo de entrada de dados e tente novamente.")
    APPLICATION_NAME_INFRADEV = ("Nome de aplicação inválido para o ambiente de 'infradev'.\n"
                                 "O nome da aplicação para o ambiente de 'infradev' deve seguir o padrão 'example' + "
                                 "'número (1-999)'.\n"
                                 "Exemplos: 'example1', 'example23', 'example456'...\n")
    APPLICATION_ACRONYM_JSON = ("A sigla da aplicação é inválida.\n"
                                "A sigla da aplicação deve seguir o padrão 'letra + letra [A-Z] + dígito (0-9)'.\n"
                                "Exemplos: 'AB1', 'CD2', 'DE3'...\n"
                                "Corrija o arquivo de entrada de dados e tente novamente.")
    APPLICATION_ACRONYM = ("A sigla da aplicação é inválida.\n"
                           "A sigla da aplicação deve seguir o padrão 'letra + letra [A-Z] + dígito (0-9)'.\n"
                           "Exemplos: 'AB1', 'CD2', 'DE3'...\n")
    TENANT_ID_JSON = ("ID de conta AWS inválido. Um ID de conta AWS válido para ambientes produtivos deve conter 12 "
                      "dígitos.\n"
                      "Exemplos: '123456789012', '111111111111', '222222222222', etc.\n"
                      "Corrija o arquivo de entrada de dados e tente novamente.")
    TENANT_ID_INFRADEV_JSON = ("ID de conta AWS inválido. Um ID de conta AWS válido para o ambiente de 'infradev' "
                               "deve conter o prefixo 'new' seguido de 9 dígitos.\n"
                               "Exemplos: 'new123456789', 'new111111111', 'new222222222', etc.\n"
                               "Corrija o arquivo de entrada de dados e tente novamente.")
    TENANT_ID = ("ID de conta AWS inválido. Um ID de conta AWS válido para ambientes produtivos deve conter 12 "
                 "dígitos.\n"
                 "Exemplos: '123456789012', '111111111111', '222222222222', etc.")
    TENANT_ID_INFRADEV = ("ID de conta AWS inválido. Um ID de conta AWS válido para o ambiente de 'infradev' deve "
                          "conter o prefixo 'new' seguido de 9 dígitos.\n"
                          "Exemplos: 'new123456789', 'new111111111', 'new222222222', etc.")
    VNET_CIDR_JSON = ("O range de endereço IP  é inválido.\n"
                      "Um range de endereço IP válido deve ser no formato CIDR e estar dentro do intervalo "
                      "'0.0.0.0/0-255.255.255.255/32'."
                      "Corrija o arquivo de entrada de dados e tente novamente.")
    VNET_CIDR = ("O range de endereço IP  é inválido.\n"
                 "Um range de endereço IP válido deve ser no formato CIDR e estar dentro do intervalo "
                 "'0.0.0.0/0-255.255.255.255/32'.")
    CREATE_OPTIONAL_TAGS_CHOICE_JSON = ("O valor do campo 'create_optional_tags' deve ser do tipo 'booleano' e definido"
                                        " como 'true' ou 'false'.\n"
                                        "Corrija o arquivo de entrada de dados e tente novamente.")
    MANDATORY_TAGS_EMPTY_JSON = ("Os valores das 'tags' no campo 'mandatory_tags' não podem ser vazios.\n"
                                 "Corrija o arquivo de entrada de dados e tente novamente.")
    MANDATORY_TAGS_EMPTY = ("O valor de uma 'tag' obrigatória não pode ser vazio.\n"
                            "Defina um valor para a tag.")
    MANDATORY_TAGS_ENVIRONMENT_JSON = ("A tag 'Environment' precisa ter o mesmo valor do campo "
                                       "'infrastructure_environment'.\n"
                                       "Corrija o arquivo de entrada de dados e tente novamente.")


def create_file(file_path: str, file_content: str) -> None:
    new_file = open(file_path, "x")
    new_file.write(file_content)
    new_file.close()


def load_json_file_as_dictionary(json_file=INPUTS_JSON_FILE) -> dict:
    with open(json_file, "r") as json_file:
        return json.load(json_file)


def show_env_selection_menu() -> None:
    print("\nAmbientes:")
    for key, value in ENVIRONMENT_MENU.items():
        print(f"{key}. {value[1]}")


def get_env_selection_menu_choice() -> str:
    while True:
        show_env_selection_menu()
        choice = input("> ")

        if choice not in ENVIRONMENT_MENU.keys():
            print("Opção inválida. Por favor, escolha um dos itens da lista.")
        else:
            return choice


def environment_valid(environment: tuple[str, str]) -> bool:
    environment_list = ENVIRONMENT_MENU.values()
    infrastructure_environment_list = []
    application_environment_list = []

    for v in environment_list:
        infrastructure_environment_list.append(v[0])
        application_environment_list.append(v[1])

    if environment in environment_list:
        return True
    else:
        if environment[0] not in infrastructure_environment_list:
            raise SubscriptionError(f"{ErrorMessages.INFRASTRUCTURE_ENVIRONMENT_JSON.value}\n")
        if environment[1] not in application_environment_list:
            raise SubscriptionError(f"{ErrorMessages.APPLICATION_ENVIRONMENT_JSON.value}\n")

        raise SubscriptionError(f"{ErrorMessages.ENVIRONMENT_JSON.value}\n")


def get_environment(silent_mode: bool, inputs_dict: dict) -> tuple[str, tuple[str, str]] | None:
    choice = None
    if silent_mode:
        infrastructure_environment = inputs_dict.get("infrastructure_environment").lower()
        application_environment = inputs_dict.get("application_environment").lower()

        for k, v in ENVIRONMENT_MENU.items():
            if v == (infrastructure_environment, application_environment):
                choice = k
                break
            else:
                choice = None

    else:
        choice = get_env_selection_menu_choice()
        infrastructure_environment = ENVIRONMENT_MENU.get(choice)[0]
        application_environment = ENVIRONMENT_MENU.get(choice)[1]

    if environment_valid((infrastructure_environment, application_environment)):
        return choice, (infrastructure_environment.lower(), application_environment.lower())


def application_name_valid(choice, application_name, error_message: str) -> bool:
    if ENVIRONMENT_MENU.get(choice)[1] == "infradev":
        match_str = re.search("^Example(?:[1-9]|[1-9]\\d|[1-9]\\d{2})$", application_name.title())

        if match_str:
            return True
        else:
            raise SubscriptionError(error_message)
    else:
        return True


def get_application_name(silent_mode: bool, choice: str, inputs_dict: dict) -> str | None:
    if silent_mode:
        application_name = inputs_dict.get("application_name").title()

        if application_name_valid(choice, application_name, ErrorMessages.APPLICATION_NAME_INFRADEV_JSON.value):
            return application_name

    else:
        while True:
                print("\nDigite o nome da aplicação:")
                application_name = input("> ").title()

                try:
                    if application_name_valid(choice, application_name, ErrorMessages.APPLICATION_NAME_INFRADEV.value):
                        return application_name

                except SubscriptionError as err:
                    print(err)


def application_acronym_valid(application_acronym: str, error_message: str) -> bool:
    match_str = re.search("^[A-Z]{2}[0-9]$", application_acronym)

    if match_str:
        return True
    else:
        raise SubscriptionError(error_message)


def get_application_acronym(silent_mode: bool, inputs_dict: dict) -> str | None:
    if silent_mode:
        application_acronym = inputs_dict.get("application_acronym").upper()

        if application_acronym_valid(application_acronym, ErrorMessages.APPLICATION_ACRONYM_JSON.value):
            return application_acronym

    else:
        while True:
            print("\nDigite a sigla da aplicação:")
            application_acronym = input("> ").upper()

            try:
                if application_acronym_valid(application_acronym, ErrorMessages.APPLICATION_ACRONYM.value):
                    return application_acronym
            except SubscriptionError as err:
                print(err)


def tenant_id_valid(choice: str, tenant_id: str, error_message_infradev: str, error_message: str) -> bool:
    if ENVIRONMENT_MENU.get(choice)[1] == "infradev":
        match_str = re.search("^new\\d{9}$", tenant_id)
    else:
        match_str = re.search("^\\d{12}$", tenant_id)

    if match_str:
        return True
    else:
        if ENVIRONMENT_MENU.get(choice)[1] == "infradev":
            raise SubscriptionError(error_message_infradev)
        else:
            raise SubscriptionError(error_message)


def get_tenant_id(silent_mode: bool, choice: str, inputs_dict: dict) -> str | None:
    if silent_mode:
        tenant_id = inputs_dict.get("tenant_id")

        if tenant_id_valid(choice,
                           tenant_id,
                           ErrorMessages.TENANT_ID_INFRADEV_JSON.value,
                           ErrorMessages.TENANT_ID_JSON.value):
            return tenant_id
    else:
        while True:
            print("\nDigite o ID de conta AWS relacionado:")
            tenant_id = input("> ")

            try:
                if tenant_id_valid(choice,
                                   tenant_id,
                                   ErrorMessages.TENANT_ID_INFRADEV.value,
                                   ErrorMessages.TENANT_ID.value):
                    return tenant_id
            except SubscriptionError as err:
                print(err)


def vnet_app_ip_address_valid(vnet_app_ip_address, error_message: str):
    cidr_regex = ("^((1|(2))?(?(3)[0-5][0-5]|[0-9][0-9])\\.|[0-9]\\.){3}((1|(2))?(?(3)[0-5][0-5]|[0-9][0-9])|["
                  "0-9])/([0-9]|[1-2][0-9]|3[0-2])$")

    match_str = re.search(cidr_regex, vnet_app_ip_address)

    if match_str:
        return vnet_app_ip_address
    else:
        raise SubscriptionError(error_message)


def get_vnet_app_ip_address(silent_mode: bool, inputs_dict: dict) -> str | None:
    if silent_mode:
        vnet_app_ip_address = inputs_dict.get("vnet_app_ip_address")

        if vnet_app_ip_address_valid(vnet_app_ip_address, ErrorMessages.VNET_CIDR_JSON.value):
            return vnet_app_ip_address
    else:

        while True:
            print("\nDigite um range de endereço IP da rede virtual (VNet) no formato CIDR:")
            vnet_ip_address_space = input("> ")

            try:
                if vnet_app_ip_address_valid(vnet_ip_address_space, ErrorMessages.VNET_CIDR.value):
                    return vnet_ip_address_space
            except SubscriptionError as err:
                print(err)


def mandatory_tag_valid(mandatory_tag: str, error_message: str) -> bool:
    if mandatory_tag.strip() == "":
        raise SubscriptionError(error_message)
    else:
        return True


def get_mandatory_tags(silent_mode: bool, choice, inputs_dict: dict, application_name: str, application_acronym: str) -> str | None:
    if silent_mode:
        mandatory_tags = inputs_dict.get("mandatory_tags")

        for k, v in mandatory_tags.items():
            if mandatory_tag_valid(v, ErrorMessages.MANDATORY_TAGS_EMPTY_JSON.value):
                return json.dumps(mandatory_tags, indent=4, cls=CustomJSONEncoder)

    else:
        infrastructure_environment, _ = ENVIRONMENT_MENU.get(choice)

        print("\nTags obrigatórias:")
        while True:
            cost_center = input("CostCenter: ")
            try:
                if mandatory_tag_valid(cost_center, ErrorMessages.MANDATORY_TAGS_EMPTY.value):
                    break
            except SubscriptionError as err:
                print(err)
        while True:
            data_classification = input("DataClassification [Interna]: ")
            try:
                if mandatory_tag_valid(data_classification, ErrorMessages.MANDATORY_TAGS_EMPTY.value):
                    break
            except SubscriptionError:
                print("Definindo valor default...")
                data_classification = "Interna"
                break
        while True:
            owner_name = input("OwnerName: ")
            try:
                if mandatory_tag_valid(owner_name, ErrorMessages.MANDATORY_TAGS_EMPTY.value):
                    break
            except SubscriptionError as err:
                print(err)
        while True:
            squad = input("Squad: ")
            try:
                if mandatory_tag_valid(squad, ErrorMessages.MANDATORY_TAGS_EMPTY.value):
                    break
            except SubscriptionError as err:
                print(err)

        mandatory_tags = {
            "ApplicationName": application_name,
            "CostCenter": cost_center,
            "DataClassification": data_classification,
            "Environment": infrastructure_environment,
            "OwnerName": owner_name,
            "Sigla": application_acronym,
            "Squad": squad
        }

        return json.dumps(mandatory_tags, indent=4, cls=CustomJSONEncoder)


def create_optional_tags_choice_valid(optional_tags_choice: str) -> bool:
    if type(optional_tags_choice) == bool:
        return True
    else:
        raise SubscriptionError(ErrorMessages.CREATE_OPTIONAL_TAGS_CHOICE_JSON.value)


def get_create_optional_tags_choice(silent_mode: bool, inputs_dict: dict) -> bool | None:
    if silent_mode:
        optional_tags_choice = inputs_dict.get("create_optional_tags")

        if create_optional_tags_choice_valid(optional_tags_choice):
            return optional_tags_choice

    else:
        while True:
            try:
                print("\nDeseja criar tags opcionais? ")
                choice = int(input("1. Sim\n"
                                   "2. Não\n"
                                   "> "))
                match choice:
                    case 1:
                        return True
                    case 2:
                        return False
                    case _:
                        print("Opção inválida. Escolha entre a opções '1' ou '2'.")
            except ValueError:
                print("Opção inválida. Escolha entre a opções '1' ou '2'.")


def get_optional_tags(silent_mode: bool, inputs_dict: dict) -> str:
    optional_tags_choice = get_create_optional_tags_choice(silent_mode, inputs_dict)
    if silent_mode:
        if optional_tags_choice:
            optional_tags = inputs_dict.get("optional_tags")
        else:
            optional_tags = {}

    else:
        if optional_tags_choice:
            print("\nTags opcionais:")
            optional_tags = {
                "ApproverName": input("ApproverName: "),
                "CreatedWith": input("CreatedWith [DevOps]: "),
                "RequesterName": input("RequesterName: "),
                "NotificationEmail": input("NotificationEmail: "),
                "ProductOwnerEmail": input("ProductOwnerEmail: "),
                "AccountType": input("AccountType [App]: "),
            }
            if optional_tags.get("CreatedWith") == "":
                optional_tags["CreatedWith"] = "DevOps"

            if optional_tags.get("AccountType") == "":
                optional_tags["AccountType"] = "App"
        else:
            optional_tags = {}

    return json.dumps(optional_tags, indent=4, cls=CustomJSONEncoder)


def get_subscription_name(choice: str, application_name: str) -> str:
    _, application_environment = ENVIRONMENT_MENU.get(choice)

    if application_environment == "infradev":
        application_number = re.findall("\\d+", application_name)[0]
        final_application_name = application_name.replace(application_number, "").lower()

        if len(application_number) == 1:
            final_application_number = f"00{application_number}"
        elif len(application_number) == 2:
            final_application_number = f"0{application_number}"
        else:
            final_application_number = application_number

        subscription_name = f"itaudev-lzdev-{final_application_name}-{final_application_number}"
        return subscription_name

    else:
        subscription_name = f"itau-lz{application_environment}-{application_name.lower()}-001"
        return subscription_name


def get_subscription_path(choice: str, application_name) -> tuple[str, str]:
    subscription_name = get_subscription_name(choice, application_name)
    infrastructure_environment, application_environment = ENVIRONMENT_MENU.get(choice)
    subscription_path = os.path.join("infra",
                                     "landingzones",
                                     infrastructure_environment,
                                     application_environment,
                                     subscription_name)

    return subscription_path, subscription_name


def generate_resources_content(silent_mode: bool, choice: str, inputs_dict: dict) -> str:
    tenant_id = get_tenant_id(silent_mode, choice, inputs_dict)
    vnet_ip_address_space = get_vnet_app_ip_address(silent_mode, inputs_dict)

    resources_template_path = os.path.join("templates",
                                           "landingzones",
                                           "resources",
                                           "terragrunt.hcl.tmpl")

    with open(resources_template_path, "r") as template_file:
        template_content = template_file.read()

    resources_template = Template(template_content)
    resources_template_str = resources_template.safe_substitute(
        tenant_id=tenant_id,
        vnet_ip_address_space=vnet_ip_address_space
    )

    return resources_template_str


def generate_subscription_content() -> str:
    subscription_template_path = os.path.join("templates",
                                              "landingzones",
                                              "subscription",
                                              "terragrunt.hcl.tmpl")

    with open(subscription_template_path, "r") as template_file:
        template_content = template_file.read()

    subscription_template = Template(template_content)
    subscription_template_str = subscription_template.template

    return subscription_template_str


def generate_variables_content(silent_mode: bool, choice: str, application_name: str, application_acronym: str, inputs_dict: dict) -> str:
    tags_mandatory = get_mandatory_tags(silent_mode, choice, inputs_dict, application_name, application_acronym)
    tags_optional = get_optional_tags(silent_mode, inputs_dict)

    variables_template_path = os.path.join("templates",
                                           "landingzones",
                                           "variables.hcl.tmpl")

    with open(variables_template_path, "r") as template_file:
        template_content = template_file.read()

    variables_template = Template(template_content)
    variables_template_str = variables_template.safe_substitute(
        application_acronym = application_acronym,
        tags_mandatory=tags_mandatory,
        tags_optional=tags_optional
    )

    return variables_template_str


def create_subscription_files(silent_mode: bool, choice: str, inputs_dict: dict) -> None:
    application_name = get_application_name(silent_mode, choice, inputs_dict)
    application_acronym = get_application_acronym(silent_mode, inputs_dict)
    subscription_root_dir = get_subscription_path(choice, application_name)[0]
    subscription_resources_dir_path = os.path.join(subscription_root_dir, "resources")
    subscription_dir_path = os.path.join(subscription_root_dir, "subscription")

    subscription_dir_path_list = [subscription_root_dir, subscription_resources_dir_path, subscription_dir_path]

    resources_content = generate_resources_content(silent_mode, choice, inputs_dict)
    subscription_content = generate_subscription_content()
    variables_content = generate_variables_content(silent_mode, choice, application_name, application_acronym, inputs_dict)

    current_dir = os.getcwd()
    for d in subscription_dir_path_list:
        print(f"Criando diretório '{d}'...")
        if not os.path.isdir(d):
            os.makedirs(d)
            print(f"Diretório '{d}' criado com sucesso!\n")
        else:
            print(f"O diretório '{d}' já existe!\n")

        if "resources" in d:
            os.chdir(subscription_resources_dir_path)
            resources_file = "terragrunt.hcl"
            try:
                print("Criando arquivo 'terragrunt.hcl'...")
                with open(resources_file, "x") as f:
                    f.write(f"# file: '{os.path.join(subscription_resources_dir_path, resources_file)}'\n"
                            f"# Resources creation configuration file for application '{application_name}'\n"
                            f"\n{resources_content}")
                print(f"Arquivo '{os.path.join(d, resources_file)}' criado com sucesso!\n")
            except FileExistsError:
                print(f"O arquivo '{os.path.join(d, resources_file)}' já existe!\n")
            os.chdir(current_dir)

        elif "subscription" in d:
            os.chdir(subscription_dir_path)
            subscription_file = "terragrunt.hcl"
            try:
                print("Criando arquivo 'terragrunt.hcl'...")
                with open(subscription_file, "x") as f:
                    f.write(f"# file: '{os.path.join(subscription_dir_path, subscription_file)}'\n"
                            f"# Subscription creation configuration file for application '{application_name}'\n"
                            f"\n{subscription_content}")
                print(f"Arquivo '{os.path.join(d, subscription_file)}' criado com sucesso!\n")
            except FileExistsError:
                print(f"O arquivo '{os.path.join(d, subscription_file)}' já existe!\n")
            os.chdir(current_dir)

        else:
            os.chdir(subscription_root_dir)
            variables_file = "variables.hcl"
            try:
                print("Criando arquivo 'variables.hcl'...")
                with open(variables_file, "x") as f:
                    f.write(f"# file: '{os.path.join(subscription_root_dir, variables_file)}'\n"
                            f"# Subscription variables file for application '{application_name}'\n"
                            f"\n{variables_content}")
                print(f"Arquivo '{os.path.join(d, variables_file)}' criado com sucesso!\n")
            except FileExistsError:
                print(f"O arquivo '{os.path.join(d, variables_file)}' já existe!\n")
            os.chdir(current_dir)


def main():
    parser = ArgumentParser(
        prog="create-subscription-files",
        description="Cria a estrutura de diretórios e arquivos necessários para a criação de uma "
                    "nova subscrição/aplicação Azure via Terragrunt.",
        usage="%(prog)s [-h] (-i | -s) [-s -j JSON]",
    )
    args_group = parser.add_mutually_exclusive_group(required=True)

    args_group.add_argument("-i", "--interactive", action="store_true", help="Cria uma subscrição de modo interativo")
    args_group.add_argument("-s", "--silent", action="store_true", help="Cria a subscrição de modo silencioso. Um "
                                                                        "arquivo JSON deve ser passado com a opção '-j'")
    parser.add_argument("-j", "--json", help="Caminho para o arquivo JSON com as entradas de dados")

    args = parser.parse_args()

    if args.silent:
        json_file_as_dict = load_json_file_as_dictionary(args.json_file)
        choice = get_environment(True, json_file_as_dict)[0]

        print("Executando o script no modo silencioso...")
        create_subscription_files(True, choice, json_file_as_dict)

    else:
        json_file_as_dict = {}
        choice = get_environment(False, json_file_as_dict)[0]

        print("Executando o script no modo interativo...")
        create_subscription_files(False, choice, json_file_as_dict)


if __name__ == "__main__":
    main()