from firebase_admin.db import Reference
from telegram import TelegramError

from models.base_products import BaseProduct
from persistence.firebase_persistence import FirebasePersistence
from utils import helper

store = FirebasePersistence()


class Ticket(BaseProduct):

    PAID_TYPE = "paid"
    FREE_TYPE = "free"

    @classmethod
    def ref(cls) -> Reference:
        return store.tickets

    # Functions

    @staticmethod
    def by_type(_type: str):
        return list(filter(lambda ticket: ticket.type == _type, Ticket.all()))
