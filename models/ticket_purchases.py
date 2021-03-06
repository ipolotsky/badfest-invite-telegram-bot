import collections
import re
import uuid
import csv
from datetime import datetime

from firebase_admin.db import Reference
from telegram import TelegramError

from models.base_purchases import BasePurchase
from persistence.firebase_persistence import FirebasePersistence
from models.tickets import Ticket
from models.users import User
from utils import helper
from PIL import Image, ImageDraw, ImageFont
import pyqrcode

store = FirebasePersistence()


class TicketPurchase(BasePurchase):

    @classmethod
    def ref(cls) -> Reference:
        return store.purchases

    @property
    def ticket_name(self):
        return helper.safe_list_get(self._data, "ticket_name", None)

    @ticket_name.setter
    def ticket_name(self, ticket_name: str):
        raise TelegramError("Direct setter for ticket name is denied")

    @property
    def ticket_base_price(self):
        return helper.safe_list_get(self._data, "ticket_base_price", None)

    @ticket_base_price.setter
    def ticket_base_price(self, ticket_base_price: str):
        raise TelegramError("Direct setter for ticket_base_price is denied")

    @property
    def ticket_description(self):
        return helper.safe_list_get(self._data, "ticket_description", None)

    @ticket_description.setter
    def ticket_description(self, ticket_description: str):
        raise TelegramError("Direct setter for ticket_description is denied")

    @property
    def user(self):
        _id = helper.safe_list_get(self._data, "user", None)
        return User.get(_id) if _id else None

    @user.setter
    def user(self, user: User):
        self._data["user"] = user.id
        self._data["user_name"] = user.real_name
        self._data["user_username"] = user.username

    @property
    def issuer(self):
        _id = helper.safe_list_get(self._data, "issuer", None)
        return User.get(_id) if _id else None

    @issuer.setter
    def issuer(self, issuer: User):
        self._data["issuer"] = issuer.id
        self._data["issuer_name"] = issuer.real_name
        self._data["issuer_username"] = issuer.username

    # activated
    @property
    def activated(self):
        timestamp = helper.safe_list_get(self._data, "activated")
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime(
                '%Y-%m-%d %H:%M:%S') + " UTC"

    @activated.setter
    def activated(self, activated: float):
        self._data["activated"] = activated

    # Functions

    def set_ticket_info(self, ticket: Ticket):
        self._data["ticket_name"] = ticket.id
        self._data["ticket_base_price"] = ticket.price
        self._data["ticket_description"] = ticket.description

    def pretty_html(self, index: int = None):
        return f"?????????? '{self.ticket_name}' ???? BadFest 2022!\n" \
               f"??????????????????: {self.total_amount / 100}??.\n" \
               f"???????? ??????????????: {self.created} (UTC)"

    def pretty_detailed_html(self):
        return f"???????????????? ????????????: {helper.safe_list_get(self._data, 'user_name')}\n"\
               f"?????? ??????????: {helper.safe_list_get(self._data, 'ticket_name')}\n"\
               f"???? ?????? ????????????: {helper.safe_list_get(self._data, 'ticket_description')}\n" \
               f"??????????????????????: {self.activated if self.activated else '??????'}"


    def create_image(self):
        # generate qr
        big_code = pyqrcode.create(self.id)
        big_code.png('tmp_code.png', scale=20, module_color=[0, 0, 0, 128], background=(255, 255, 255))

        qr = Image.open("tmp_code.png")
        ticket_width = qr.width + 60

        # get qr img
        qr_img = Image.new('RGB', (ticket_width, ticket_width), color=(255, 218, 0))
        qr_img.paste(qr, (30, 30))

        # get text img
        text_img = Image.new('RGB', (ticket_width, 420), color=(255, 218, 0))
        d = ImageDraw.Draw(text_img)
        master_font = ImageFont.FreeTypeFont('fonts/HelveticaBlack.ttf', 60, encoding="utf-8")
        d.text((50, 50), "BadFest 2022 / 2-3 ????????", fill=(0, 0, 0), font=master_font)
        slave_font = ImageFont.FreeTypeFont('fonts/arial.ttf', 40, encoding="utf-8")
        d.text((60, 130), '??????: ' + self.user.real_name, fill=(0, 0, 0), font=slave_font)
        d.text((60, 180), '??????: ' + self.ticket_name, fill=(0, 0, 0), font=slave_font)
        d.text((60, 230), '??????????????????: ' + str(self.total_amount / 100) + ' ????????????', fill=(0, 0, 0), font=slave_font)
        d.text((60, 280), '????????: ' + self.created + ' (UTC)', fill=(0, 0, 0), font=slave_font)

        # get ticket size
        ticket_height = qr_img.height + text_img.height

        # concatenate text and qr
        purchase = Image.new('RGB', (ticket_width, ticket_height))
        purchase.paste(text_img, (0, 0))
        purchase.paste(qr_img, (0, text_img.height))

        purchase.save(f'images/{self.id}.png')

    @staticmethod
    def create_new_gift(issuer: User):
        _id = str(uuid.uuid4())
        purchase = TicketPurchase.create_new(_id)
        purchase.issuer = issuer

        free_tickets = Ticket.by_type(Ticket.FREE_TYPE)
        if not free_tickets or len(free_tickets) == 0:
            raise TelegramError("?????? ???????????????????? ?????????? ??????????????")

        ticket = free_tickets[0]
        purchase.currency = "RUB"
        purchase.total_amount = ticket.price * 100
        purchase.set_ticket_info(ticket)
        purchase.save()

        return purchase

    @staticmethod
    def by_user(user: User):
        return list(filter(lambda purchase: purchase._data["user"] and purchase._data["user"] == user.id, TicketPurchase.all()))

    @staticmethod
    def statistics():
        purchase_list = TicketPurchase.all()
        groups = collections.defaultdict(dict)
        groups["???????? ????????????"] = {'count': 0, 'items': []}
        groups["????????"] = {'count': 0, 'items': []}
        groups["????????"] = {'count': 0, 'items': []}
        groups["??????????"] = {'count': 0, 'items': []}
        groups["??????, ??????????????!"] = {'count': 0, 'items': []}
        taxes = 0
        total = 0
        for obj in purchase_list:
            total = total + obj.total_amount
            if obj.ticket_name == "???????? ????????????":
                if re.search('????????', obj.ticket_description, re.IGNORECASE):
                    groups["????????"]['items'].append(obj)
                    groups["????????"]['count'] = groups["????????"]['count'] + obj.total_amount
                    continue

                if re.search('????????', obj.ticket_description, re.IGNORECASE):
                    groups["????????"]['items'].append(obj)
                    groups["????????"]['count'] = groups["????????"]['count'] + obj.total_amount
                    continue

                if re.search('??????????', obj.ticket_description, re.IGNORECASE):
                    groups["??????????"]['items'].append(obj)
                    groups["??????????"]['count'] = groups["??????????"]['count'] + obj.total_amount
                    continue

            taxes = taxes + obj.total_amount
            groups[obj.ticket_name]['items'].append(obj)
            groups[obj.ticket_name]['count'] = groups[obj.ticket_name]['count'] + obj.total_amount

        result = ""
        for group in groups:
            result += str(group).capitalize() + ": " + str(len(groups[group]['items'])) + " / " + str(groups[group]['count'] / 100) + "??. \n\n"

        result += f"??????????: {str(total / 100)}??\n"
        result += f"?????????? ????????: {str(round(taxes / 100 * 0.905, 2))} ({str(taxes / 100)})\n"
        result += f"?????????? ??????????: {str((total - taxes) / 100)}??\n"
        return result

    @staticmethod
    def statistics_csv():
        # csv header
        fieldnames = ['customer_name', 'email', 'ticket_name', 'ticket_base_price',
                      'total_amount', 'phone_number',
                      'user', 'user_name', 'user_username',
                      'ticket_description', 'id', 'created',
                      'provider_payment_charge_id', 'telegram_payment_charge_id', 'currency',
                      'issuer_username', 'issuer_name', 'issuer', 'activated']

        # csv data
        rows = [purchase._data for purchase in TicketPurchase.all()]

        with open('purchases.csv', 'w', encoding='UTF8', newline='\n') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)