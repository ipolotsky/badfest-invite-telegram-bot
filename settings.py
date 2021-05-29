import os
import json
from utils import helper


class Settings:

    @staticmethod
    def max_invites():
        from persistence.firebase_persistence import FirebasePersistence
        settings = FirebasePersistence().settings.get()
        return helper.safe_list_get(settings, "max_invites", 5)

    @staticmethod
    def fb_creds():
        with open("FB_CREDS.json") as file:
            return json.load(file)

    @staticmethod
    def db_url():
        return os.environ["FB_DB_URL"]

    @staticmethod
    def bot_token():
        return os.environ["BAD_BAR_BOT_TOKEN"]

    @staticmethod
    def provider_token():
        return os.environ["BOT_PAYMENT_PROVIDER_TOKEN"]
