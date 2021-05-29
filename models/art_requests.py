import random
import string
from datetime import datetime
from telegram import TelegramError
from persistence.firebase_persistence import FirebasePersistence
from models.users import User
from utils import helper

store = FirebasePersistence()


class ArtRequest:

    def __init__(self):
        self._id = None
        self._data = {}

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, _id: int):
        self._id = _id

    @property
    def creator(self):
        _id = helper.safe_list_get(self._data, "creator", None)
        if not _id or not isinstance(_id, int):
            raise TelegramError("Некорректный id желающего делать арт")
        return User.get(_id)

    @creator.setter
    def creator(self, creator: User):
        self._data["creator"] = creator.id

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
        store.art_requests.child(str(self._id)).update(self._data)

    def tech_data(self):
        return self._data

    # Functions

    def load(self):
        if not self._id:
            raise TelegramError(f"Отсутстует id арт запроса")

        _data = store.art_requests.child(str(self._id)).get()
        if not _data:
            raise TelegramError(f"Нет данных по арт запросу с id: {self._id}")

        self._data = _data

    def pretty_html(self, index: int = None):
        html = f"Заявка от {self.creator.real_name} ({self.creator.username})\n" \
               f"Дата: {self.created}"
        return html

    @staticmethod
    def get(_id: str):
        if not ArtRequest.exists(_id):
            raise TelegramError(f"Нет арт запроса с id {_id}")

        art_request = ArtRequest()
        art_request.id = _id
        art_request.load()

        return art_request

    @staticmethod
    def exists(_id: str):
        return bool(store.art_requests.child(_id).get())

    @staticmethod
    def create_new(creator: User):

        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while ArtRequest.exists(code):
            print("Generating: Code is already exists")
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        store.art_requests.child(code).update({
            'creator': creator.id,
            'creator_name': creator.real_name,
            'created': datetime.now().timestamp()
        })

        art_request = ArtRequest()
        art_request.id = code
        art_request._data = store.art_requests.child(code).get()
        return art_request

    @staticmethod
    def all(sort: str = "created", reverse=True):
        fb_art_requests = store.art_requests.order_by_child(sort).get() if sort else store.art_requests.get()
        fb_art_requests = fb_art_requests if fb_art_requests else []

        fb_art_requests = reversed(fb_art_requests) if reverse else fb_art_requests
        return [ArtRequest.get(fb_art_request) for fb_art_request in fb_art_requests]

    @staticmethod
    def by_creator(creator: User):
        return list(filter(lambda fb_art_request: str(fb_art_request.creator.id) == str(creator.id), ArtRequest.all()))
