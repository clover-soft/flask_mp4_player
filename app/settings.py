import json
from typing import Any


class Settings:
    config_dict = {}
    crm_user_cache = {}

    @staticmethod
    def load_config():
        with open('.settings.json') as file:
            Settings.config_dict = json.load(file)

    @staticmethod
    def get_config_param(key):
        if key in Settings.config_dict.keys():
            return Settings.config_dict[key]
        return None
    