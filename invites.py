import random
import string
from datetime import datetime
from telegram import TelegramError
from emoji import emojize
from fire_persistence import FirebasePersistence
from users import User
from utils import helper

store = FirebasePersistence()


class Invite:
    DEFAULT_INVITE_AMOUNT = 2

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
    def creator(self):
        _id = helper.safe_list_get(self._data, "creator", None)
        if not _id or not isinstance(_id, int):
            raise TelegramError("Некорректный id автора приглашения")
        return User.get(_id)

    @creator.setter
    def creator(self, creator: User):
        self._data["creator"] = creator.id

    @property
    def participant(self):
        _id = helper.safe_list_get(self._data, "participant", None)
        return User.get(_id) if _id else None

    @participant.setter
    def participant(self, participant: User):
        self._data["participant"] = participant.id
        self._data["participant_name"] = participant.real_name

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
        store.invites.child(str(self._id)).update(self._data)

    def activated(self):
        return bool(self.participant)

    def tech_data(self):
        return self._data

    # Functions

    def load(self):
        if not self._id:
            raise TelegramError(f"Отсутстует id приглашения")

        _data = store.invites.child(str(self._id)).get()
        if not _data:
            raise TelegramError(f"Нет данных по приглашению с id: {self._id}")

        self._data = _data

    def pretty_html(self, index: int = None):
        html = emojize(":handshake:",
                       use_aliases=True) + f" <b>Приглашение на BadFest2021 от {self.creator.real_name}</b>\n"
        if self.activated():
            html += f"Выдано и активировано <a href='tg://user?id={self.participant.id}'>{self.participant.username}</a>"
        else:
            html += f"Твой код: {self.id}. Переходи по этой ссылке и регайся в боте: " \
                    f"<a href='https://t.me/badbarbot?start={self.id}'>https://t.me/badbarbot?start={self.id}</a> " \
                    f"и нажимай Start"
        return html

    @staticmethod
    def get(_id: str):
        if not Invite.exists(_id):
            raise TelegramError(f"Нет приглашения с id {_id}")

        invite = Invite()
        invite.id = _id
        invite.load()

        return invite

    @staticmethod
    def generate_invites(creator: User):
        for i in range(Invite.DEFAULT_INVITE_AMOUNT):
            Invite.create_new(creator)

    @staticmethod
    def exists(_id: str):
        return bool(store.invites.child(_id).get())

    @staticmethod
    def create_new(creator: User):

        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Invite.exists(code):
            print("Generating: Code is already exists")
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        store.invites.child(code).update({
            'creator': creator.id,
            'creator_name': creator.real_name,
            'created': datetime.now().timestamp()
        })

        invite = Invite()
        invite.id = code
        invite._data = store.invites.child(code).get()
        return invite

    @staticmethod
    def all(sort: str = "created", reverse=True):
        fb_invites = store.invites.order_by_child(sort).get() if sort else store.invites.get()
        fb_invites = reversed(fb_invites) if reverse else fb_invites
        return list(map(lambda fb_invite: Invite.get(fb_invite), fb_invites))

    @staticmethod
    def activated_list():
        return list(filter(lambda invite: invite.activated(), Invite.all()))

    @staticmethod
    def by_creator(creator: User):
        return list(filter(lambda invite: invite.creator.id == creator.id, Invite.all()))

    @staticmethod
    def by_participant(participant: User, cached_invites: list = None):
        return list(
            filter(lambda invite: invite.participant and str(invite.participant.id) == str(participant.id),
                   cached_invites if cached_invites else Invite.all())
        )
