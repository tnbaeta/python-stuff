import json
import re

ENV_MENU = {
    "1": ("dev", "infradev"),
    "2": ("prod", "dev"),
    "3": ("prod", "hom"),
    "4": ("prod", "prod")
}


class CustomJSONEncoder(json.JSONEncoder):
    """
    CustomJSONEncoder modifies JSON encoded strings by replacing specific
    characters.

    This encoder customizes the default behavior of `json.JSONEncoder` by
    replacing colons with equal signs and removing commas in the resultant
    JSON string. It is particularly useful in contexts where this specific
    modification of JSON format is required for compatibility or readability.

    :ivar item_separator: Separator used between items.
    :type item_separator: str
    :ivar key_separator: Separator between names and values.
    :type key_separator: str
    """

    def encode(self, obj):
        json_str = super().encode(obj)
        json_str = json_str.replace(":", " =")
        json_str = json_str.replace(",", "")

        return json_str


def show_env_selection_menu() -> None:
    """
    Displays a selection menu for available environments.

    This function prints out a menu of environmental options. Each environment is
    numbered and associated with a description. It iterates through the global
    ``ENV_MENU`` dictionary to fetch the available environments and their respective
    descriptions for user display. The purpose of this function is to provide a simple
    interface for the user to identify and select an environment.

    :return: None
    """
    print("\nAmbientes:")
    for key, value in ENV_MENU.items():
        print(f"{key}. {value[1]}")


def get_env_selection_menu_choice() -> str:
    """
    Get the user's choice from the environment selection menu.

    This function continuously displays the environment selection menu
    and prompts the user for input until a valid choice is made. The
    `ENV_MENU.keys()` is used as the set of valid options. If an invalid
    option is entered, an error message is printed, and the menu is
    displayed again. Once a valid input is received, the corresponding
    choice is returned.

    :return: The valid choice selected from the environment selection menu
    :rtype: str
    """
    while True:
        show_env_selection_menu()
        choice = input("> ")

        if choice not in ENV_MENU.keys():
            print("Opção inválida. Por favor, escolha um dos itens da lista.")
        else:
            return choice


def get_application_name(choice) -> str:
    """
    Fetches the application name based on user input and verifies its format depending on the provided environment context.

    :param choice: The key used to determine the application environment from the ENV_MENU mapping
    :type choice: str
    :return: Validated application name input by the user that satisfies the required format for the environment
    :rtype: str
    """
    _, application_environment = ENV_MENU.get(choice)

    while True:
        application_name = input("\nDigite o nome da aplicação: ").lower()

        if application_environment == "infradev":
            match_str = re.search("^example(?:[1-9]|[1-9]\\d|[1-9]\\d{2})$", application_name)

            if match_str:
                return application_name
            else:
                print(f"O nome de aplicação '{application_name}' é inválido par ao ambiente de '{application_environment}'.\n"
                      f"Em '{application_environment}' a aplicação deve seguir o padrão 'example' + 'número (0-999)'.\n"
                      f"Exemplos: 'example1', 'example23', 'example456'.")
        else:
            return application_name


def get_subscription_name() -> str:
    pass


if __name__ == "__main__":
    c = get_env_selection_menu_choice()
    app = get_application_name(c)
