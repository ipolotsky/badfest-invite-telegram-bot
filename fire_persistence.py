from ast import literal_eval
from collections import defaultdict
from typing import Dict

import firebase_admin
from firebase_admin import db
from telegram.ext import BasePersistence

credentials = {
    "type": "service_account",
    "project_id": "badfest-invites",
    "private_key_id": "4158f99ccf234c050bb44fb1e4363c45b121570a",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDmPpNpWZQNw2Nq\nQ0fsty9Myl/YJawrCsqIJntc2f2//TBs3aed8OHq664shCCBLx0HiCRxL7AdJ1pH\n4vRztapICf4J0D2lgfnNlYqh3myZrXayZw7afNnKkd1UhcO+oUDE1im7h5cvyRZo\nNoOgkC1dmSQ7NmwPt7CFQ+S4MNc4uAgPg4zMCOL5Sjf7LX5iAiqngB+kZSSn/bR+\nzWNik6L8gh4WRgIDXtzdxyLWJGea2qpt1JEr8zccVQwJgx8Y/a2HqL5CatIxZpGq\nJFqXJUGQdaDq0E1pg+6CcE7bijTBqOIP/YjceCIkD9E29N5TyZJtU3o2XwrYJD5r\nvWizvRJ1AgMBAAECggEAGW+ASXsj6AFV0j9sirIR/6G7xN0kj/y5MyFNL4zFg5gs\n6VnzUndx/cnbi/9st9jElDhuDjL+eboHNznTV5USIrM35U2kAczCE/wZPJid1rxb\nCIpqEakJRl+m29eLMFwQE661HYp1IUpNt2WOVQaYfGaWohP5DCN21MITWmXK4PD+\nAncI++clxeEL1r25XUV8XH1vFEpmA9so/+bit4VccVyWTwHIkwJYRo7SxWzMSm/F\nd9CBDq/eeggPeBWPcC2CFy6/AcEc8bJddgnSY1ONc8eyuy1/PVpV3x+nhZb09ADU\nlfGuEwHFAGcsgRk3XynfIfzxBYwIZ2RSXH6KYAGtYQKBgQD9PMglfHEacel5Qt7j\nv4Ut/uPQoVvW3lLhIiLDAEdiu26LRWKhVkA2T0BxMJ2cGrU/UMprMWiLUUfFBecO\n9P/u5f40Fx13Je/W5IdlFvH4TMpgj8UjaYI6yOpYWklAR5y01T6v/VcrMBLK1mum\nZIjV07d7ReAHXhz24euzbbsjZwKBgQDowZTPlk51wI9buNFJoIx8uu8Qb5t3tvTE\nQu3bj44FLc3/mE9zLShvXVaO/GI+X8FI5oRRkdiPuLeDizX2eqiFCt2FV7V/uApr\nRTbTqCiCbaKI88lzuqWngnNXWEp7ldj0sr60f4XzMuvhBzqQLXDipsKknW+HLKMU\nl6XnHEgtwwKBgGCivjnX2A1gZNj6VLYSUs8vkl3+BV7kbjotXZiOVa9umQuaib3J\nfS18ZroK9EoqwvmLagMn0p4/gSTFUNwbUEMpDy1vmLXsCy80/BnufJ3lJ+FbW75c\nt+6Y1xyqL4PREBLNwWNFSOtZKAKxelj/ylvWtBDdpFULbAAmTFynRh+HAoGBAOGi\np8wFfdIQ9eiI5fpmNUrFPPPF/gSzy9xmtYbfR2Il4UkiMgMJh+VNqpe6etLUqN8u\n+J7KsBHDk8NltM5YYf13Zv/Y4w4JL7CFzHyqy3qFJcd17ZjPG7+jaoUGBk6AGW49\nyTnZVdVJS/k9tLwIESLnXlGOfYug7gcMa7v7Ys1ZAoGBAISM159X+equvgPVDxlx\nCSDM/V9kEASy/2GhPUIrJJGNPqERr+DykCMss5w5wq+unH/Q8V5CO1gMPcAFfFni\nzpE8E1ddMfGCKHv/yY45NlKlkm4PGWgP1OqvDZQZjosJA7747Ag06FwaxoLwnbtc\n8Qhbbcq19HzrsEcBQPxSzMRc\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-pzg12@badfest-invites.iam.gserviceaccount.com",
    "client_id": "108525482249482548275",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-pzg12%40badfest-invites.iam.gserviceaccount.com"
}
db_url = 'https://badfest-invites-default-rtdb.europe-west1.firebasedatabase.app'
cred = firebase_admin.credentials.Certificate(credentials)
app = firebase_admin.initialize_app(cred, {"databaseURL": db_url})


class FirebasePersistence(BasePersistence):

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(FirebasePersistence, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        # cred = firebase_admin.credentials.Certificate(credentials)
        self.app = app
        self.fb_user_data = db.reference("user_data")
        self.users = db.reference("users")
        self.purchases = db.reference("purchases")
        self.tickets = db.reference("tickets")
        self.invites = db.reference("invites")
        self.fb_chat_data = db.reference("chat_data")
        self.fb_bot_data = db.reference("bot_data")
        self.fb_conversations = db.reference("conversations")
        super().__init__(
            store_user_data=False,
            store_chat_data=False,
            store_bot_data=False,
        )

    # @classmethod
    # def from_environment(cls, **kwargs):
    #     credentials = json.loads(os.environ["FIREBASE_CREDENTIALS"])
    #     database_url = os.environ["FIREBASE_URL"]
    #     return cls(database_url=database_url, credentials=credentials, **kwargs)

    def get_user_data(self):
        data = self.fb_user_data.get() or {}
        output = self.convert_keys(data)
        return defaultdict(dict, output)

    def get_chat_data(self):
        data = self.fb_chat_data.get() or {}
        output = self.convert_keys(data)
        return defaultdict(dict, output)

    def get_bot_data(self):
        return defaultdict(dict, self.fb_bot_data.get() or {})

    def get_conversations(self, name):
        res = self.fb_conversations.child(name).get() or {}
        res = {literal_eval(k): v for k, v in res.items()}
        return res

    def update_conversation(self, name, key, new_state):
        if new_state:
            self.fb_conversations.child(name).child(str(key)).set(new_state)
        else:
            self.fb_conversations.child(name).child(str(key)).delete()

    def update_user_data(self, user_id, data):
        self.fb_user_data.child(str(user_id)).update(data)

    def update_chat_data(self, chat_id, data):
        self.fb_chat_data.child(str(chat_id)).update(data)

    def update_bot_data(self, data):
        self.fb_bot_data = data

    @staticmethod
    def convert_keys(data: Dict):
        output = {}
        for k, v in data.items():
            if k.isdigit():
                output[int(k)] = v
            else:
                output[k] = v
        return output
