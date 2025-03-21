""" Terragrunt files creator for Azure Subscriptions
This script automates the process of creating 'Terragrunt' directory structures and configuration files
for Azure subscriptions. It supports both interactive and silent modes.

This script accepts a JSON file as the input data source. The JSON file must contain the following fields:
- application_name: The name of the application.
- application_acronym: The acronym of the application.
- tenant_id: The ID of the relative AWS account associated with the subscription.
- infrastructure_environment: The environment of the infrastructure.
- application_environment: The environment of the application.
- create_optional_tags: A boolean value indicating whether to create optional tags.
- mandatory_tags: A dictionary containing the mandatory tags.
- optional_tags: A dictionary containing the optional tags if 'create_optional_tags' is set to 'true'.

The values of the JSON fields present in the JSON file input data source will be used to automatically populate the
'terragrunt' files to be created using the provided templates accordingly.

The script expects the following template files to be present in the 'scripts/templates' directory:
- subscription-inputs.json: Contains the input data for the subscription creation process.
- variables.hcl.tmpl: Contains the template for the 'variables.hcl' file.
- resources.hcl.tmpl: Contains the template for the 'resources.hcl' file.
- subscription.hcl.tmpl: Contains the template for the 'subscription.hcl' file.

This file can also be imported as a module and contains the following
functions:

    * create_file - Creates a new file at the specified path and writes the provided content to it.
    * load_json_file_as_dictionary - Loads a JSON file and parses its contents into a dictionary.
    * show_env_selection_menu - Displays a menu for selecting environments.
    * get_env_selection_menu_choice - Gets the user's choice from the menu.
    * environment_data_valid - Evaluates the validity of the provided environment.
    * get_environment_data - Retrieve environment-related data based on the provided mode and inputs.
    * application_name_valid - Validate the application name against predefined naming patterns for specific environments.
    * get_application_name - Determines the application name based on the provided options.
    * application_acronym_valid - Validates the format of the application acronym.
    * get_application_acronym - Get the acronym of the application based on user input or provided data.
    * tenant_id_valid - Validates the tenant ID based on the provided environment choice.
    * get_tenant_id - Retrieves the tenant ID based on either silent mode or user input.
    * vnet_app_ip_address_valid - Validate the given vnet_app_ip_address with a regex that matches CIDR notation.
    * get_vnet_app_ip_address - Retrieves the IP address of a Virtual Network (VNet) application.
    * mandatory_tag_valid - Validate whether the given mandatory tag is non-empty and correctly formatted.
    * get_mandatory_tags - Retrieves or constructs mandatory tags based on the provided inputs and operation mode.
    * create_optional_tags_choice_valid - Validates if the provided input for `optional_tags_choice` is a boolean.
    * get_create_optional_tags_choice - Determine whether to create optional tags based on interaction mode
    and provided inputs.
    * get_optional_tags - Retrieves or constructs optional tags based on the provided inputs and operation mode.
    * get_subscription_name - Determines the subscription name based on the given choice and application name,
    while taking into account the application's environment.
    * get_subscription_path - Generates the subscription path and subscription name based on given
    choice and application_name.
    * generate_resources_content - Generates resources content based on the provided inputs and a template file.
    * generate_subscription_content - Generates and returns the raw content of a subscription template from
    a pre-defined file path.
    * generate_variables_content - Generates the variables content by combining the mandatory and optional tags
    and substituting them into a predefined template.
    * create_subscription_files - Creates necessary subscription files and directories based on the provided parameters.
    * main - The main entry point for the script to create directory and file structures required for a new
    Azure subscription/application using Terragrunt.
"""

import argparse
import json
import os
import pathlib
import re

from enum import Enum
from string import Template


# Define the absolute path of the script's root directory
ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()
TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")
VARIABLES_TEMPLATE_ROOT_DIR = os.path.join(TEMPLATES_DIR, "landingzones")
RESOURCES_TEMPLATE_DIR = os.path.join(VARIABLES_TEMPLATE_ROOT_DIR, "resources")
SUBSCRIPTION_TEMPLATE_DIR = os.path.join(VARIABLES_TEMPLATE_ROOT_DIR, "subscription")

# Paths to various template files used in the script
SUBSCRIPTION_INPUTS_JSON_FILE_PATH = os.path.join(TEMPLATES_DIR, "subscription-inputs.json")
VARIABLES_TEMPLATE_FILE_PATH = os.path.join(VARIABLES_TEMPLATE_ROOT_DIR, "variables.hcl.tmpl")
RESOURCES_TEMPLATE_FILE_PATH = os.path.join(RESOURCES_TEMPLATE_DIR, "terragrunt.hcl.tmpl")
SUBSCRIPTION_TEMPLATE_FILE_PATH = os.path.join(SUBSCRIPTION_TEMPLATE_DIR, "terragrunt.hcl.tmpl")


# Define the path for the subscription directory inside the 'infra/landingzones' structure
SUBSCRIPTION_DIR = os.path.join(ROOT_DIR, "infra", "landingzones")


# Mapping of environment options to their respective infrastructure and application environments.
# Each key corresponds to a user-selectable option, and its value is a tuple containing
# the 'infrastructure_environment' and 'application_environment'.
ENVIRONMENT_MENU = {
    "1": ("dev", "infradev"),
    "2": ("prod", "dev"),
    "3": ("prod", "hom"),
    "4": ("prod", "prod")
}


# Dictionary to map the silent mode status for the script
SILENT_MODE = {
    0: False,
    1: True
}


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSONEncoder that modifies the default JSON string representation.

    The CustomJSONEncoder class extends the default JSONEncoder to produce a
    customized encoding of Python objects into JSON strings. This encoder
    replaces colons (":") with equal signs ("=") and removes commas from the
    resulting JSON string. This customized format can be useful for specific
    use cases where standard JSON formatting needs to be altered.

    Methods:
        encode: Overrides the default encoding behavior to apply the custom
        JSON formatting.

    """
    def encode(self, obj):
        """
        Encodes a given Python object into a JSON-formatted string with specific formatting changes.

        Customizes the default JSON encoding functionality by replacing colons
        with an equal sign and removing commas from the resulting JSON string.
        This ensures formatted strings are tailored for specific use cases
        that deviate from standard JSON formatting.

        :param obj: The Python object to encode into a JSON-formatted string.
        :return: A JSON-formatted string with colons replaced by equal signs
            and commas removed.
        :rtype: str
        """
        json_str = super().encode(obj)
        json_str = json_str.replace(":", " =")
        json_str = json_str.replace(",", "")

        return json_str


class SubscriptionError(Exception):
    """
    Represents a custom exception for subscription-related errors.

    This exception is used to handle errors specifically related
    to subscriptions. It provides a way to capture and convey detailed
    information regarding subscription issues through custom error messages.

    :ivar message: The error message describing the subscription issue.
    :type message: str
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}"


class ErrorMessages(Enum):
    """
    This class defines a collection of constant error messages in a structured way
    using an enumeration. These error messages are used to provide validation and
    consistent feedback for various configurations and inputs, such as JSON files,
    application environments, acronyms, AWS tenant IDs, IP ranges, among others.
    Each constant provides a descriptive and localized error message that includes
    instructions to correct invalid inputs. The use of this class ensures that error
    messages are standardized and centralized for reuse.

    :ivar ENVIRONMENT_JSON: Error message for an invalid combination of
        'infrastructure_environment' and 'application_environment'.
    :type ENVIRONMENT_JSON: str
    :ivar INFRASTRUCTURE_ENVIRONMENT_JSON: Error message for an invalid
        'infrastructure_environment' value.
    :type INFRASTRUCTURE_ENVIRONMENT_JSON: str
    :ivar APPLICATION_ENVIRONMENT_JSON: Error message for an invalid
        'application_environment' value.
    :type APPLICATION_ENVIRONMENT_JSON: str
    :ivar APPLICATION_NAME_INFRADEV_JSON: Error message for invalid
        application names in the 'infradev' environment when provided in JSON.
    :type APPLICATION_NAME_INFRADEV_JSON: str
    :ivar APPLICATION_NAME_INFRADEV: Error message for invalid application
        names in the 'infradev' environment.
    :type APPLICATION_NAME_INFRADEV: str
    :ivar APPLICATION_ACRONYM_JSON: Error message for an invalid application acronym
        provided in JSON.
    :type APPLICATION_ACRONYM_JSON: str
    :ivar APPLICATION_ACRONYM: Error message for an invalid application acronym.
    :type APPLICATION_ACRONYM: str
    :ivar TENANT_ID_JSON: Error message for an invalid AWS account ID specified
        in JSON.
    :type TENANT_ID_JSON: str
    :ivar TENANT_ID_INFRADEV_JSON: Error message for an invalid AWS account ID
        in the 'infradev' environment specified in JSON.
    :type TENANT_ID_INFRADEV_JSON: str
    :ivar TENANT_ID: Error message for an invalid AWS account ID in productive
        environments.
    :type TENANT_ID: str
    :ivar TENANT_ID_INFRADEV: Error message for an invalid AWS account ID in
        the 'infradev' environment.
    :type TENANT_ID_INFRADEV: str
    :ivar VNET_CIDR_JSON: Error message for an invalid IP address range in JSON.
    :type VNET_CIDR_JSON: str
    :ivar VNET_CIDR: Error message for an invalid IP address range.
    :type VNET_CIDR: str
    :ivar CREATE_OPTIONAL_TAGS_CHOICE_JSON: Error message for invalid
        field 'create_optional_tags' value in JSON.
    :type CREATE_OPTIONAL_TAGS_CHOICE_JSON: str
    :ivar MANDATORY_TAGS_EMPTY_JSON: Error message for empty values in the
        'mandatory_tags' JSON field.
    :type MANDATORY_TAGS_EMPTY_JSON: str
    :ivar MANDATORY_TAGS_EMPTY: Error message for empty values in mandatory tags.
    :type MANDATORY_TAGS_EMPTY: str
    :ivar MANDATORY_TAGS_ENVIRONMENT_JSON: Error message when the 'Environment' tag
        does not match the 'infrastructure_environment' field in JSON.
    :type MANDATORY_TAGS_ENVIRONMENT_JSON: str
    """
    FILE_EXISTS = "Arquivo já existe!"
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
    MANDATORY_TAGS_APPLICATION_NAME_JSON = ("A tag 'ApplicationName' precisa ter o mesmo valor do campo "
                                            "'application_name'.\n"
                                            "Corrija o arquivo de entrada de dados e tente novamente.")
    MANDATORY_TAGS_ENVIRONMENT_JSON = ("A tag 'Environment' precisa ter o mesmo valor do campo "
                                       "'infrastructure_environment'.\n"
                                       "Corrija o arquivo de entrada de dados e tente novamente.")


def create_file(file_path: str, file_content: str) -> None:
    """
    Creates a new file at the specified path and writes the provided content to it.

    The function attempts to create a new file using the specified `file_path`.
    It writes the given `file_content` into the newly created file. If the file
    already exists, the function will raise a `FileExistsError`. It ensures that
    the operations to create and write to the file are completed successfully
    before closing the file handle.

    :param file_path: The path at which the new file should be created.
    :param file_content: The content to write into the newly created file.
    :return: None
    """
    new_file = open(file_path, "x")
    new_file.write(file_content)
    new_file.close()


def load_json_file_as_dictionary(json_file: str) -> dict:
    """
    Loads a JSON file and parses its contents into a dictionary.

    This function takes the path of a JSON file, reads its contents, and
    parses it into a Python dictionary. It assumes that the provided file
    path is valid and points to a JSON-formatted file.

    :param json_file: Path to the JSON file to be loaded.
    :type json_file: str
    :return: A dictionary containing the parsed JSON data.
    :rtype: dict
    """
    with open(json_file, "r") as json_file:
        return json.load(json_file)


def show_env_selection_menu() -> None:
    """
    Displays a menu for selecting environments.

    This function prints out a list of available environments, formatted
    with their respective keys and descriptions provided in the global
    `ENVIRONMENT_MENU` dictionary.

    :raises KeyError: If `ENVIRONMENT_MENU` does not contain valid key-value
                      pairs or is not properly structured.

    :return: None
    """
    print("\nAmbientes:")
    for key, value in ENVIRONMENT_MENU.items():
        print(f"{key}. {value[1]}")


def get_env_selection_menu_choice() -> str:
    """
    Retrieves and validates the user's menu choice from the environment selection menu.

    The function displays an environment selection menu to the user, prompts for input,
    validates the input against the available menu options, and ensures the returned
    choice corresponds to a valid option in the menu. If the input is not a valid option,
    the user is prompted again until a valid selection is made.

    :return: The validated user's choice from the environment selection menu.
    :rtype: str
    """
    while True:
        show_env_selection_menu()
        choice = input("> ")

        if choice not in ENVIRONMENT_MENU.keys():
            print("Opção inválida. Por favor, escolha um dos itens da lista.")
        else:
            return choice


def environment_data_valid(environment: tuple[str, str]) -> bool:
    """
    Evaluates the validity of the provided environment tuple against defined
    environments in the system. The environment is checked against a predefined
    list of valid infrastructure and application environments. The function
    ensures the environment exists in the allowed list or raises an appropriate
    error indicating the invalidity of the provided environment.

    :param environment: A tuple containing the infrastructure and application environment.
                        The first element represents the infrastructure environment
                        and the second element represents the application environment.
    :type environment: tuple[str, str]
    :return: A boolean indicating whether the environment is valid or not.
    :rtype: bool
    :raises SubscriptionError: If the infrastructure environment is not present
                               in the allowed list.
    :raises SubscriptionError: If the application environment is not present in
                               the allowed list.
    :raises SubscriptionError: If the environment does not match any preconfigured
                               valid environments.
    """
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


def get_environment_data(silent_mode: bool, inputs_dict: dict) -> tuple[str, tuple[str, str]] | None:
    """
    Retrieve environment-related data based on the provided mode and inputs.

    This function determines the application's infrastructure and environment settings based
    on a silent or interactive mode. If the silent_mode is enabled, the function extracts
    environment data directly from the provided inputs. Otherwise, it retrieves the data
    using an interactive menu selection. The function ensures that the resulting environment
    values are validated before returning them.

    :param silent_mode: Determines whether the function operates in silent mode or interactive
        mode. A value of True enables silent mode.
    :type silent_mode: bool
    :param inputs_dict: A dictionary containing the pre-defined environment configuration when
        operating in silent mode. Keys are expected to include "infrastructure_environment" and
        "application_environment".
    :type inputs_dict: dict
    :return: If the environment is valid, returns a tuple consisting of the selected choice
        and another tuple containing the corresponding infrastructure and application environment
        names in lowercase. Returns None if the environment is invalid.
    :rtype: tuple[str, tuple[str, str]] | None
    """
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

    if environment_data_valid((infrastructure_environment, application_environment)):
        return choice, (infrastructure_environment.lower(), application_environment.lower())


def application_name_valid(choice: str, application_name: str, error_message: str) -> bool:
    """
    Validate the application name against predefined naming patterns for specific environments.

    This function checks whether the provided `application_name` string matches a specific
    naming convention when the `choice` corresponds to an "infradev" environment. If the
    naming convention is not met, a `SubscriptionError` is raised with the provided
    `error_message`. Otherwise, it returns a boolean indicating validity.

    :param choice: The environment menu choice that determines the validation rules to apply.
    :param application_name: The application name to validate against the naming convention.
    :param error_message: The error message to display if the validation fails.
    :return: A boolean indicating whether the application name is valid according
        to the specific validation rules.
    :rtype: bool
    :raises SubscriptionError: If the application name fails validation for the "infradev"
        environment.
    """
    if ENVIRONMENT_MENU.get(choice)[1] == "infradev":
        match_str = re.search("^Example(?:[1-9]|[1-9]\\d|[1-9]\\d{2})$", application_name.title())

        if match_str:
            return True
        else:
            raise SubscriptionError(error_message)
    else:
        return True


def get_application_name(silent_mode: bool, choice: str, inputs_dict: dict) -> str | None:
    """
    Determines the application name based on the provided options. If in silent mode, it retrieves the
    application name from a dictionary. Otherwise, it prompts the user to enter the name manually, validating
    it against the defined criteria.

    :param silent_mode: Whether the function operates in silent mode, fetching the application name without
        user interaction.
    :param choice: The selected choice that defines validation behavior for the application name.
    :param inputs_dict: Provides the application name in silent mode; a dictionary containing initialization
        parameters.
    :return: The validated application name as a string, or ``None`` if validation fails or in scenarios
        where no valid name can be determined.
    """
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
    """
    Validates the format of the application acronym to ensure it meets the specified
    pattern requirements. The acronym must strictly follow the pattern of two uppercase
    letters followed by a single digit (e.g., "AB1"). If the acronym does not match the
    expected pattern, a `SubscriptionError` is raised with the provided error message.

    :param application_acronym: The acronym to be validated.
    :param error_message: The error message to be raised in case the validation fails.
    :return: Returns True if the application acronym matches the predefined pattern.
    :rtype: bool
    :raises SubscriptionError: If the application acronym does not match the expected
        pattern.
    """
    match_str = re.search("^[A-Z]{2}[0-9]$", application_acronym)

    if match_str:
        return True
    else:
        raise SubscriptionError(error_message)


def get_application_acronym(silent_mode: bool, inputs_dict: dict) -> str | None:
    """
    Get the acronym of the application based on user input or provided data.

    This function retrieves the application acronym by either reading it
    from the `inputs_dict` in silent mode or prompting the user for input
    if not in silent mode. The acronym is validated using the
    `application_acronym_valid` method to ensure its correctness. In non-silent
    mode, the user is continuously prompted until a valid acronym is provided.

    :param silent_mode: Determines whether the function operates in silent mode
        (input taken from `inputs_dict`) or interactive mode
        (user input is required).
    :type silent_mode: bool
    :param inputs_dict: A dictionary containing various input parameters including
        the potential application acronym (key: "application_acronym"). Used when
        in silent mode.
    :type inputs_dict: dict
    :return: The validated application acronym as a string or `None` if a valid
        acronym is not obtained.
    :rtype: str | None
    """
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
    """
    Validates the tenant ID based on the provided environment choice. The validation
    criteria differ based on the type of environment being selected (e.g., "infradev"
    or another type). Raises a SubscriptionError if validation fails.

    :param choice: Represents the environment choice that determines the matching
                   criteria for the tenant ID.
    :type choice: str
    :param tenant_id: The tenant ID that needs to be validated. Its format is checked
                      based on the type of environment selected.
    :type tenant_id: str
    :param error_message_infradev: The error message raised if the tenant ID validation
                                   fails in the "infradev" environment.
    :type error_message_infradev: str
    :param error_message: The error message raised if the tenant ID validation fails
                          in any non-"infradev" environment.
    :type error_message: str
    :return: True if the tenant ID matches the expected format for the selected
             environment choice.
    :rtype: bool
    :raises SubscriptionError: Raised with the provided error message if the tenant
                               ID does not meet the expected criteria for the selected
                               environment.
    """
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
    """
    Retrieves the tenant ID based on either silent mode or user input, while validating it against the specified conditions.
    The function operates in two distinct modes: silent or interactive, determined by the `silent_mode`
    parameter. In silent mode, the tenant ID is extracted directly from the provided inputs' dictionary.
    In interactive mode, the function repeatedly prompts the user to enter a tenant ID until a valid one
    is provided or an error interrupts the process.

    :param silent_mode: Boolean indicating whether the function should operate in silent mode.
    :param choice: The selection used to validate the tenant ID based on specific conditions.
    :param inputs_dict: A dictionary containing input information, expected to contain a tenant ID key.
    :return: The valid tenant ID as a string if resolved successfully; otherwise, returns None.
    :rtype: str | None
    """
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


def vnet_app_ip_address_valid(vnet_app_ip_address: str, error_message: str) -> bool:
    """
    Validates whether the provided virtual network application IP address is in the correct CIDR notation format.

    The function compares the given vnet_app_ip_address with a regex that matches CIDR notation
    and returns `True` if the IP address is valid. If the validation fails, it raises a SubscriptionError
    with the provided error message.

    :param vnet_app_ip_address: The IP address of the application in the virtual network that needs to
        be validated. Must be a string in the CIDR notation.
    :param error_message: The error message to be included in the raised SubscriptionError if validation fails.
    :return: A boolean value, `True` if vnet_app_ip_address is valid.
    """
    cidr_regex = "(\\b([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\b\\.){3}(\\b([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\b)/\\b([1-2]?[0-9]|3[0-2])\\b"

    match_str = re.search(cidr_regex, vnet_app_ip_address)

    if match_str:
        return True
    else:
        raise SubscriptionError(error_message)


def get_vnet_app_ip_address(silent_mode: bool, inputs_dict: dict) -> str | None:
    """
    Retrieves the IP address of a Virtual Network (VNet) application either from the provided
    inputs dictionary or interactively requests the user input, depending on the silent mode.

    The function validates the VNet application IP address before returning it. If in silent mode,
    it fetches the IP address from the `inputs_dict`. Otherwise, it prompts the user to input
    an IP address in CIDR format, validates it, and then returns the input.

    :param silent_mode: Determines whether the function operates in silent mode. If True,
        retrieves the IP address from `inputs_dict` without user interaction.
    :type silent_mode: bool
    :param inputs_dict: A dictionary containing key-value mappings, potentially including
        the key "vnet_app_ip_address" with its corresponding IP address value.
    :type inputs_dict: dict
    :return: Returns the validated VNet application IP address. If silent mode is not enabled
        and the user does not provide valid input, it returns None.
    :rtype: str | None
    """
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
    """
    Validate whether the given mandatory tag is non-empty and correctly formatted.
    This function ensures that the mandatory tag string is not empty or composed
    solely of spaces. If the `mandatory_tag` is invalid, an exception is raised
    with the provided error message. Otherwise, the function returns a boolean
    value indicating the tag's validity.

    :param mandatory_tag: The mandatory tag string to verify. This must not be empty
        or composed only of whitespace.
    :type mandatory_tag: str
    :param error_message: The error message to include if the mandatory tag
        validation fails.
    :type error_message: str
    :return: A boolean value indicating the validity of the mandatory tag.
    :rtype: bool
    :raises SubscriptionError: If `mandatory_tag` is empty or contains only
        whitespace.
    """
    if mandatory_tag.strip() == "":
        raise SubscriptionError(error_message)
    else:
        return True


def get_mandatory_tags(silent_mode: bool, choice: str, inputs_dict: dict, application_name: str, application_acronym: str) -> str | None:
    """
    Retrieves or constructs mandatory tags based on the provided inputs and operation mode. If `silent_mode`
    is enabled, tags are fetched directly from the provided `inputs_dict`. Otherwise, the user is
    prompted interactively to enter the required tag values. The tags are returned in JSON format.

    :param silent_mode: A flag indicating whether the operation should run in silent mode without
        user interaction.
    :param choice: The selected environment choice, used to infer infrastructure-related tags.
    :param inputs_dict: A dictionary containing input data which includes mandatory tags when in silent mode.
    :param application_name: The name of the application, used as a mandatory tag.
    :param application_acronym: The acronym representing the application, used as a mandatory tag.
    :return: A JSON-formatted string containing the mandatory tags if successful, otherwise None.
    :rtype: str | None
    """
    if silent_mode:
        mandatory_tags = inputs_dict.get("mandatory_tags")
        infrastructure_environment = inputs_dict.get("infrastructure_environment")

        if mandatory_tags.get("ApplicationName").lower() != application_name.lower():
            raise SubscriptionError(ErrorMessages.MANDATORY_TAGS_APPLICATION_NAME_JSON.value)

        if mandatory_tags.get("Environment") != infrastructure_environment:
            raise SubscriptionError(ErrorMessages.MANDATORY_TAGS_ENVIRONMENT_JSON.value)

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


def create_optional_tags_choice_valid(optional_tags_choice: bool) -> bool:
    """
    Validates and confirms if the provided input for `optional_tags_choice` is a boolean.

    This function is used to ensure that only boolean values are accepted for the
    `optional_tags_choice` parameter. If the input is of type `bool`, the function
    returns True, indicating successful validation. Otherwise, an error is raised.

    :param optional_tags_choice: Represents the choice made for optional tags. Must
        strictly be a boolean value.
    :type optional_tags_choice: bool
    :raises SubscriptionError: Raised when the provided input is not of type `bool`.
    :return: True if the validation passes (i.e., the input is a boolean).
    :rtype: bool
    """
    if type(optional_tags_choice) == bool:
        return True
    else:
        raise SubscriptionError(ErrorMessages.CREATE_OPTIONAL_TAGS_CHOICE_JSON.value)


def get_create_optional_tags_choice(silent_mode: bool, inputs_dict: dict) -> bool | None:
    """
    Determine whether to create optional tags based on interaction mode and provided inputs.

    When the silent mode is enabled, the function attempts to determine the choice
    based on the value supplied in the `inputs_dict`. If the value is deemed valid,
    it is returned as the result.

    In non-silent mode, the function interacts with the user via the terminal, asking
    for input to make the choice interactively. It ensures the user's input is valid
    before returning the selection.

    :param silent_mode: Boolean flag indicating whether the function should operate silently.
    :param inputs_dict: Dictionary holding input values, including a possible pre-defined
        choice for creating optional tags.
    :return: The choice of whether to create optional tags. Returns a boolean value only
        if a valid choice is available, or None otherwise.
    """
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
    """
    Determines and retrieves optional metadata tags as a JSON string, based on user inputs in
    interactive or silent mode. In silent mode, the inputs are fetched directly from the
    inputs_dict dictionary, while in interactive mode, the user is prompted to provide input
    via the console. The function enforces certain default values for specific fields if
    they are left empty by the user.

    :param silent_mode: Indicates whether the method operates in silent mode. If True, the
        function fetches data from inputs_dict, otherwise it prompts the user for input.
    :type silent_mode: bool
    :param inputs_dict: A dictionary containing key-value pairs to be used in silent mode
        to generate the optional tags.
    :type inputs_dict: dict
    :return: A JSON string representation of the optional tags as a dictionary with
        interactive or predefined values populated.
    :rtype: str
    """
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
    """
    Determines the subscription name based on the given choice and application name,
    while taking into account the application's environment. For 'infradev', it processes
    the application name to extract and format numerical identifiers. For other environments,
    it constructs the subscription name by using the environment and application name.

    :param choice: The key used to retrieve the application environment info from
        `ENVIRONMENT_MENU` dictionary.
    :type choice: str
    :param application_name: The name of the application, which may include numeric
        identifiers for specific environments.
    :type application_name: str
    :return: The constructed subscription name based on the environment and application
        name.
    :rtype: str
    """
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


def get_subscription_path(choice: str, application_name: str) -> tuple[str, str]:
    """
    Generates the subscription path and subscription name based on given
    choice and application_name. It leverages predefined environment
    mappings and constructs the correct subscription path by combining
    directory paths and environment variables. This function returns both
    the subscription path and subscription name.

    :param choice: A string representing the environment choice. This is
        used to fetch the corresponding environment settings from the
        predefined environment menu.
    :param application_name: A string representing the application name.
        It is used to determine the subscription name.
    :return: A tuple containing:
        - The computed subscription path as a string
        - The generated subscription name as a string
    """
    subscription_name = get_subscription_name(choice, application_name)
    infrastructure_environment, application_environment = ENVIRONMENT_MENU.get(choice)
    subscription_path = os.path.join(SUBSCRIPTION_DIR,
                                     infrastructure_environment,
                                     application_environment,
                                     subscription_name)

    return subscription_path, subscription_name


def generate_resources_content(silent_mode: bool, choice: str, inputs_dict: dict) -> str:
    """
    Generates resources content based on the provided inputs and a template file. This function
    substitutes variables into a predefined template file and returns the resulting content as
    a string. It utilizes several input parameters to dynamically generate the required data
    for substitution into the template.

    :param silent_mode: Boolean flag that determines whether the operation should run in
        silent mode, avoiding interactive prompts.
    :type silent_mode: bool
    :param choice: A string representing the user's selection or choice affecting the
        data generation.
    :type choice: str
    :param inputs_dict: A dictionary containing input data that is used to generate
        the content for the template.
    :type inputs_dict: dict
    :return: A string representing the generated resource content after substituting
        values into the template.
    :rtype: str
    """
    tenant_id = get_tenant_id(silent_mode, choice, inputs_dict)
    vnet_ip_address_space = get_vnet_app_ip_address(silent_mode, inputs_dict)

    with open(RESOURCES_TEMPLATE_FILE_PATH, "r") as template_file:
        template_content = template_file.read()

    resources_template = Template(template_content)
    resources_template_str = resources_template.safe_substitute(
        tenant_id=tenant_id,
        vnet_ip_address_space=vnet_ip_address_space
    )

    return resources_template_str


def generate_subscription_content() -> str:
    """
    Generates and returns the raw content of a subscription template from
    a pre-defined file path. This function reads the template file, extracts
    its content, and returns it as a string. The template content is processed
    but not rendered with specific dynamic values.

    :return: String representation of the raw subscription template content
    :rtype: str
    """
    subscription_template_path = SUBSCRIPTION_TEMPLATE_FILE_PATH

    with open(subscription_template_path, "r") as template_file:
        template_content = template_file.read()

    subscription_template = Template(template_content)
    subscription_template_str = subscription_template.template

    return subscription_template_str


def generate_variables_content(silent_mode: bool, choice: str, application_name: str, application_acronym: str,
                               inputs_dict: dict) -> str:
    """
    Generates the variables content by combining the mandatory and optional tags
    and substituting them into a predefined template. The content is generated
    based on the provided parameters, allowing customization of the output.

    :param silent_mode: Indicates whether the operation is running in silent mode.
    :param choice: The type of operation or scenario being executed.
    :param application_name: The name of the application for which the variables are generated.
    :param application_acronym: The acronym corresponding to the given application.
    :param inputs_dict: A dictionary containing additional input options and their values.
    :return: A string representing the content generated from the variables' template.
    :rtype: str
    """
    mandatory_tags = get_mandatory_tags(silent_mode, choice, inputs_dict, application_name, application_acronym)
    optional_tags = get_optional_tags(silent_mode, inputs_dict)

    with open(VARIABLES_TEMPLATE_FILE_PATH, "r") as template_file:
        template_content = template_file.read()

    variables_template = Template(template_content)
    variables_template_str = variables_template.safe_substitute(
        application_acronym=application_acronym,
        tags_mandatory=mandatory_tags,
        tags_optional=optional_tags
    )

    return variables_template_str


def create_subscription_files(silent_mode: bool, choice: str, inputs_dict: dict) -> None:
    """
    Creates and writes subscription files for a specified application. It dynamically generates
    content for `variables.hcl`, `resources/terragrunt.hcl`, and `subscription/terragrunt.hcl` files
    based on the provided application name, acronym, and other input parameters. This function will
    ensure that directories for the files are created if they do not already exist, and writes
    content to these files accordingly.

    :param silent_mode: A boolean flag to run the function in silent mode, suppressing some outputs.
    :param choice: A string representing the user choice, typically used to determine specific paths.
    :param inputs_dict: A dictionary containing necessary data to generate application-specific
        configurations.
    :return: None. This function does not return any value but creates files with appropriate content.
    """
    application_name = get_application_name(silent_mode, choice, inputs_dict)
    application_acronym = get_application_acronym(silent_mode, inputs_dict)
    subscription_root_dir = get_subscription_path(choice, application_name)[0]
    subscription_variables_file_path = os.path.join(subscription_root_dir, "variables.hcl")
    subscription_resources_file_path = os.path.join(subscription_root_dir, "resources", "terragrunt.hcl")
    subscription_file_path = os.path.join(subscription_root_dir, "subscription", "terragrunt.hcl")

    subscription_files_path_list = [subscription_variables_file_path, subscription_resources_file_path, subscription_file_path]

    resources_content = generate_resources_content(silent_mode, choice, inputs_dict)
    subscription_content = generate_subscription_content()
    variables_content = generate_variables_content(silent_mode, choice, application_name, application_acronym, inputs_dict)

    for file in subscription_files_path_list:
        os.makedirs(os.path.dirname(file), exist_ok=False)

        print(f"Criando arquivo '{file}'...")
        with open(file, "x") as f:
            if "resources" in file:
                f.write(f"# file: '{os.path.relpath(file)}'\n"
                        f"# 'Resources' configuration file for application '{application_name}'\n"
                        f"\n{resources_content}")
                print(f"Arquivo '{file}' criado com sucesso!\n")
            elif "subscription" in file:
                f.write(f"# file: '{os.path.relpath(file)}'\n"
                        f"# 'Subscription' configuration file for application '{application_name}'\n"
                        f"\n{subscription_content}")
                print(f"Arquivo '{file}' criado com sucesso!\n")
            else:
                f.write(f"# file: '{os.path.relpath(file)}'\n"
                        f"# 'Variables' file for application '{application_name}'\n"
                        f"\n{variables_content}")
                print(f"Arquivo '{file}' criado com sucesso!\n")


def main() -> None:
    """
    The main entry point for the script to create directory and file structures required for a new
    Azure subscription/application using Terragrunt. The script supports both interactive and silent
    modes to accommodate user preference or automation needs.

    Interactive mode enables users to provide input manually during execution, while silent mode
    requires a JSON file containing necessary data.

    Command-line arguments are parsed, and appropriate functions are invoked based on the mode selected.

    Arguments:
        - -i, --interactive: Enables interactive mode to create a subscription manually.
        - -s, --silent: Enables silent mode for subscription creation. Requires a JSON file.
        - -j, --json: Provides the path to the JSON file used in silent mode for data input.

    :return: None
    """
    parser = argparse.ArgumentParser(
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
        json_file_as_dict = load_json_file_as_dictionary(args.json)
        choice = get_environment_data(True, json_file_as_dict)[0]

        print("Executando o script no modo silencioso...")
        create_subscription_files(True, choice, json_file_as_dict)

    else:
        json_file_as_dict = {}
        choice = get_environment_data(False, json_file_as_dict)[0]

        print("Executando o script no modo interativo...")
        create_subscription_files(False, choice, json_file_as_dict)


if __name__ == "__main__":
    main()
