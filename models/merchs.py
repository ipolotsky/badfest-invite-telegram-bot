from firebase_admin.db import Reference
from models.base_goods import BaseProduct
from persistence.firebase_persistence import FirebasePersistence

store = FirebasePersistence()


class Merch(BaseProduct):

    ACTIVE_TYPE = "active"
    ARCHIVE_TYPE = "archive"

    @classmethod
    def ref(cls) -> Reference:
        return store.merch

    @staticmethod
    def by_type(_type: str):
        return list(filter(lambda merch: merch.type == _type, Merch.all()))
