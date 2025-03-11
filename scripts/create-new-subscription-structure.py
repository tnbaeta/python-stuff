import json

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

