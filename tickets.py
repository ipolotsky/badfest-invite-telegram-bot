from telegram import TelegramError

from fire_persistence import FirebasePersistence
from utils import helper

store = FirebasePersistence()


class Ticket:
    PAID_TYPE = "paid"
    FREE_TYPE = "free"

    def __init__(self):
        self._id = None
        self._data = {}
        self.status = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _id: int):
        self._id = _id

    @property
    def paid(self):
        return helper.safe_list_get(self._data, "type", None) == self.PAID_TYPE

    @property
    def description(self):
        return helper.safe_list_get(self._data, "description")

    @description.setter
    def description(self, description: str):
        raise TelegramError("Description is being changed only via Firebase store")

    @property
    def price(self):
        return helper.safe_list_get(self._data, "price")

    @price.setter
    def price(self, price: int):
        raise TelegramError("Price is being changed only via Firebase store")

    @property
    def order(self):
        return helper.safe_list_get(self._data, "order")

    @order.setter
    def order(self, order: int):
        raise TelegramError("Order is being changed only via Firebase store")

    @property
    def type(self):
        return helper.safe_list_get(self._data, "type")

    @type.setter
    def type(self, _type: str):
        raise TelegramError("Type is being changed only via Firebase store")

    # Functions

    def load(self):
        if not self._id:
            raise TelegramError(f"Отсутстует id билета")

        _data = store.tickets.child(str(self._id)).get()
        if not _data:
            raise TelegramError(f"Нет данных по билету с id: {self._id}")

        self._data = _data

    def pretty_html(self, index: int = None):
        return "<b>{}{}</b>\n{}".format(str(index) + ". " if index else "", self.id, self.description)

    @staticmethod
    def get(_id: str):
        if not Ticket.exists(_id):
            raise TelegramError(f"Нет билета с id {_id}")
        ticket = Ticket()
        ticket.id = _id
        ticket.load()

        return ticket

    @staticmethod
    def exists(_id: str):
        return bool(store.tickets.child(_id).get())

    @staticmethod
    def create_new(_id: int):
        if Ticket.exists(str(_id)):
            raise TelegramError(f"Попытка создать билет id {_id}")

    @staticmethod
    def all(sort: str = "order", reverse=True):
        fb_tickets = store.tickets.order_by_child(sort).get() if sort else store.tickets.get()
        fb_tickets = reversed(fb_tickets) if reverse else fb_tickets

        fb_tickets = fb_tickets if fb_tickets else []
        return [Ticket.get(ticket) for ticket in fb_tickets]
        # return list(map(lambda fb_ticket: Ticket.get(fb_ticket), fb_tickets))

    @staticmethod
    def by_type(_type: str):
        return list(filter(lambda ticket: ticket.type == _type, Ticket.all()))
