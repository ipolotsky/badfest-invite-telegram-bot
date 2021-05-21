from datetime import datetime

from telegram import TelegramError

from fire_persistence import FirebasePersistence
from utils import helper

store = FirebasePersistence()


class User:

    STATUS_WELCOME = 'just_open_bot'
    STATUS_IN_WAITING_LIST = 'waiting_list'
    STATUS_IN_WAITING_LIST_CHECKED = 'waiting_list_checked'
    STATUS_BY_REFERRAL = 'by_referral_link'
    STATUS_BY_REFERRAL_CHECKED = 'by_referral_link_checked'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_READY = 'ready'

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
    def admin(self):
        return helper.safe_list_get(self._data, "admin", False)

    @admin.setter
    def admin(self, admin: bool):
        raise TelegramError("Нельзя устанавливать пользователя в админа")

    @property
    def status(self):
        return helper.safe_list_get(self._data, "status")

    @status.setter
    def status(self, status: str):
        self._data["status"] = status

    @property
    def first_name(self):
        return helper.safe_list_get(self._data, "first_name")

    @first_name.setter
    def first_name(self, first_name: str):
        self._data["first_name"] = first_name

    @property
    def last_name(self):
        return helper.safe_list_get(self._data, "last_name")

    @last_name.setter
    def last_name(self, last_name: str):
        self._data["last_name"] = last_name

    @property
    def username(self):
        return f"@{helper.safe_list_get(self._data, 'username', 'direct')}"

    @username.setter
    def username(self, username: str):
        self._data["username"] = username

    @property
    def real_name(self):
        return helper.safe_list_get(self._data, "real_name")

    @real_name.setter
    def real_name(self, real_name: str):
        self._data["real_name"] = real_name

    @property
    def insta(self):
        return helper.safe_list_get(self._data, "insta")

    @insta.setter
    def insta(self, insta: str):
        self._data["insta"] = insta

    @property
    def vk(self):
        return helper.safe_list_get(self._data, "vk")

    @vk.setter
    def vk(self, vk: str):
        self._data["vk"] = vk

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
        store.users.child(str(self._id)).update(self._data)

    def full_name(self):
        if self.real_name:
            return self.real_name

        return f"{self.first_name} {self.last_name}"

    def tech_data(self):
        return self._data

    # Functions

    def set_data(self, data: dict):
        if "first_name" in data:
            self.first_name = data["first_name"]
        if "last_name" in data:
            self.last_name = data["last_name"]
        if "username" in data:
            self.username = data["username"]

    def load(self):
        if not self._id:
            raise TelegramError(f"Отсутстует id")

        _data = store.users.child(str(self._id)).get()
        if not _data:
            raise TelegramError(f"Нет данных по пользователю с id: {self._id}")

        self._data = _data

    def pretty_html(self, index: int = None):
        return "<b>{}{}</b> => {}\n" \
                "Data: {} ({}) / <a href='tg://user?id={}'>{}</a>\n" \
                "<a href='{}'>instagram</a> / <a href='{}'>vk</a>\n" \
                "{}\n\n" \
                "\n".format(str(index) + ". " if index else "",
                            self.real_name,
                            self.status,
                            self.full_name(),
                            self.id,
                            self.id,
                            self.username,
                            self.insta,
                            self.vk,
                            self.created)

    @staticmethod
    def get(_id: int):
        if not User.exists(_id):
            raise TelegramError(f"Нет пользователя с id {_id}")
        user = User()
        user.id = _id
        user.load()

        return user

    @staticmethod
    def exists(_id: int):
        return bool(store.users.child(str(_id)).get())

    @staticmethod
    def create_new(_id: int):
        if User.exists(_id):
            raise TelegramError(f"Попытка создать пользователя с существующем id {_id}")

        store.users.child(str(_id)).update({
            'id': _id,
            'created': datetime.now().timestamp()
        })

        user = User()
        user.id = _id
        user._data = store.users.child(str(_id)).get()
        return user

    @staticmethod
    def all(sort: str = "created", reverse=True):
        fb_users = store.users.order_by_child(sort).get() if sort else store.users.get()
        fb_users = reversed(fb_users) if reverse else fb_users
        return list(map(lambda fb_user: User.get(fb_user), fb_users))

    @staticmethod
    def admins():
        return list(filter(lambda user: user.admin, User.all()))

    @staticmethod
    def by_status(_status: str):
        return list(filter(lambda user: user.status == _status, User.all()))

