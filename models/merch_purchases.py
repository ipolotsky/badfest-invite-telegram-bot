from emoji import emojize
from firebase_admin.db import Reference
from telegram import TelegramError

from models.base_purchases import BasePurchase
from models.merchs import Merch
from persistence.firebase_persistence import FirebasePersistence
from utils import helper

store = FirebasePersistence()


class MerchPurchase(BasePurchase):

    @classmethod
    def ref(cls) -> Reference:
        return store.merch_purchases

    @property
    def merch_name(self):
        return helper.safe_list_get(self._data, "merch_name", None)

    @merch_name.setter
    def merch_name(self, merch_name: str):
        raise TelegramError("Direct setter for merch name is denied")

    @property
    def merch_base_price(self):
        return helper.safe_list_get(self._data, "merch_base_price", None)

    @merch_base_price.setter
    def merch_base_price(self, merch_base_price: str):
        raise TelegramError("Direct setter for merch_base_price is denied")

    @property
    def merch_description(self):
        return helper.safe_list_get(self._data, "merch_description", None)

    @merch_description.setter
    def merch_description(self, ticket_description: str):
        raise TelegramError("Direct setter for merch_description name is denied")

    @property
    def user_id(self):
        return helper.safe_list_get(self._data, "user_id", None)

    @user_id.setter
    def user_id(self, user_id: int):
        self._data["user_id"] = user_id

    # Functions

    def set_merch_info(self, merch: Merch):
        self._data["merch_name"] = merch.id
        self._data["merch_base_price"] = merch.price
        self._data["merch_description"] = merch.description

    def pretty_html(self, index: int = None):
        return emojize(":fire:", use_aliases=True) + f"Мерч '{self.merch_name}' на BadFest 2022 твой!\n" \
               f"Стоимость: {self.total_amount / 100}р.\n" \
               f"Дата покупки: {self.created} (UTC)"

    def admin_pretty_html(self, index: int = None):
        return (f"{str(index)}." if index else "") + emojize(":fire:", use_aliases=True) + \
               f"'{self.merch_name}' для <a href='tg://user?id={self.user_id}'>{self.customer_name}</a>\n" \
               f"Тел: {self.phone_number} / email: {self.email} cтоимость: {self.total_amount / 100}р.\n" \
               f"Дата покупки: {self.created} (UTC)"


    @staticmethod
    def by_user_id(user_id: int):
        return list(filter(lambda purchase: purchase.user_id == user_id, MerchPurchase.all()))
