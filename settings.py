from fire_persistence import FirebasePersistence
from utils import helper

store = FirebasePersistence()


class Settings:

    @staticmethod
    def max_invites():
        settings = store.settings.get()
        return helper.safe_list_get(settings, "max_invites", 5)
