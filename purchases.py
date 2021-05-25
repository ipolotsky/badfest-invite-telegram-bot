from datetime import datetime

from telegram import TelegramError

from fire_persistence import FirebasePersistence
from tickets import Ticket
from users import User
from utils import helper

store = FirebasePersistence()


class Purchase:

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
    def ticket(self):
        _id = helper.safe_list_get(self._data, "ticket", None)
        return Ticket.get(_id) if _id else None

    @ticket.setter
    def ticket(self, ticket: Ticket):
        self._data["ticket"] = ticket.id
        self._data["ticket_name"] = ticket.id

    @property
    def user(self):
        _id = helper.safe_list_get(self._data, "user", None)
        return User.get(_id) if _id else None

    @user.setter
    def user(self, user: User):
        self._data["user"] = user.id
        self._data["user_name"] = user.real_name
        self._data["user_username"] = user.username

    # Currency
    @property
    def currency(self):
        return helper.safe_list_get(self._data, "currency", None)

    @currency.setter
    def currency(self, currency: str):
        self._data["currency"] = currency

    # Total_amount
    @property
    def total_amount(self):
        return helper.safe_list_get(self._data, "total_amount", None)

    @total_amount.setter
    def total_amount(self, total_amount: int):
        self._data["total_amount"] = total_amount

    # Total_amount
    @property
    def ticket_name(self):
        return helper.safe_list_get(self._data, "ticket_name", None)

    @ticket_name.setter
    def ticket_name(self, ticket_name: str):
        raise TelegramError("Setter for ticket_name is denied")

    # Phone_number
    @property
    def phone_number(self):
        return helper.safe_list_get(self._data, "phone_number", None)

    @phone_number.setter
    def phone_number(self, phone_number: str):
        self._data["phone_number"] = phone_number

    # email
    @property
    def email(self):
        return helper.safe_list_get(self._data, "email", None)

    @email.setter
    def email(self, email: str):
        self._data["email"] = email

    # telegram_payment_charge_id
    @property
    def telegram_payment_charge_id(self):
        return helper.safe_list_get(self._data, "telegram_payment_charge_id", None)

    @telegram_payment_charge_id.setter
    def telegram_payment_charge_id(self, telegram_payment_charge_id: str):
        self._data["telegram_payment_charge_id"] = telegram_payment_charge_id

    # provider_payment_charge_id
    @property
    def provider_payment_charge_id(self):
        return helper.safe_list_get(self._data, "provider_payment_charge_id", None)

    @provider_payment_charge_id.setter
    def provider_payment_charge_id(self, provider_payment_charge_id: str):
        self._data["provider_payment_charge_id"] = provider_payment_charge_id

    # provider_payment_charge_id
    @property
    def provider_payment_charge_id(self):
        return helper.safe_list_get(self._data, "provider_payment_charge_id", None)

    @provider_payment_charge_id.setter
    def provider_payment_charge_id(self, provider_payment_charge_id: str):
        self._data["provider_payment_charge_id"] = provider_payment_charge_id

    # created
    @property
    def created(self):
        timestamp = helper.safe_list_get(self._data, "created")
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime(
                '%Y-%m-%d %H:%M:%S')

    @created.setter
    def created(self, created: float):
        self._data["created"] = created

    def save(self):
        store.purchases.child(self._id).update(self._data)

    def tech_data(self):
        return self._data

    # Functions

    def load(self):
        if not self._id:
            raise TelegramError(f"Отсутстует id")

        _data = store.purchases.child(str(self._id)).get()
        if not _data:
            raise TelegramError(f"Нет данных по покупке с id: {self._id}")

        self._data = _data

    def pretty_html(self, index: int = None):
        return f"Твой билет '{self.ticket_name}' на BadFest 2021!\n" \
               f"Стоимость: {self.total_amount / 100}р.\n" \
               f"Дата покупки: {self.created}"

    @staticmethod
    def get(_id: str):
        if not Purchase.exists(_id):
            raise TelegramError(f"Нет покупки с id {_id}")
        purchase = Purchase()
        purchase.id = _id
        purchase.load()

        return purchase

    @staticmethod
    def exists(_id: str):
        return bool(store.purchases.child(_id).get())

    @staticmethod
    def create_new(_id: str):
        if Purchase.exists(_id):
            raise TelegramError(f"Попытка создать покупку с существующем id {_id}")

        store.purchases.child(_id).update({
            'id': _id,
            'created': datetime.now().timestamp()
        })

        purchase = Purchase()
        purchase.id = _id
        purchase._data = store.purchases.child(_id).get()
        return purchase

    @staticmethod
    def all(sort: str = "created", reverse=True):
        fb_purchases = store.purchases.order_by_child(sort).get() if sort else store.purchases.get()
        fb_purchases = reversed(fb_purchases) if reverse else fb_purchases
        return list(map(lambda fb_purchase: Purchase.get(fb_purchase), fb_purchases))

    @staticmethod
    def by_user(user: User):
        return list(filter(lambda purchase: purchase.user.id == user.id, Purchase.all()))

