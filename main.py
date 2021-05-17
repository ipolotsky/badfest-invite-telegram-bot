#!/usr/bin/env python
# pylint: disable=C0116
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
from datetime import datetime
from re import search
import logging
from typing import Dict, Optional

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext,
)

import firebase_admin
from firebase_admin import db

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from fire_persistence import FirebasePersistence

from utils import helper

cred = {
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

my_persistence = FirebasePersistence(
    store_bot_data=False,
    store_chat_data=False,
    database_url=db_url,
    credentials=cred
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

STARTING, WAITING_NAME, WAITING_INSTA, WAITING_VK, WAITING_APPROVE, ADMIN_DASHBOARD = range(4, 10)

WELCOME = 'just_open_bot'
IN_WAITING_LIST = 'waiting_list'
BY_REFERRAL = 'by_referral_link'
APPROVED = 'approved'
REJECTED = 'rejected'
READY = 'ready'

state_texts = dict([
    (STARTING, 'Привет! Это бот BadFest 2021'),
    (WAITING_NAME, 'Такс, давай знакомиться! Немного вопросиков, чтобы мы знали, кто ты такой(ая). \nКак тебя зовут?'),
    (WAITING_INSTA, 'Скинь, плиз, ссылку на инсту'),
    (WAITING_VK, 'Скинь, плиз, ссылку на vk'),
    (WAITING_APPROVE, 'Ееееее! Ну все, теперь жди - как только модераторы тебя чекнут, тебе прилетят реферальные '
                      'ссылки, чтобы пригласить друзей, а также ты сможешь оплатить билет прямо тут.')
])


def user_to_text(user: list, index = None):
    return "<b>{}{}</b> => {}\n" \
          "Data: {} ({}) / <a href='tg://user?id={}'>{}</a>\n" \
          "<a href='{}'>instagram</a> / <a href='{}'>vk</a>\n" \
           "{}\n\n" \
          "\n".format(str(index) + ". " if index else "",
                      helper.safe_list_get(user, "name", "Не указал имя"),
                      helper.safe_list_get(user, "status"),
                      helper.safe_list_get(user, "first_name", "No name") + " " + helper.safe_list_get(user,"last_name"),
                      helper.safe_list_get(user, "id"),
                      helper.safe_list_get(user, "id"),
                      "@" + helper.safe_list_get(user, "username") if helper.safe_list_get(user, "username") else "direct",
                      helper.safe_list_get(user, "insta", "инсты нет"),
                      helper.safe_list_get(user, "vk", "vk нет"),
                      datetime.fromtimestamp(helper.safe_list_get(user, "created", None)).strftime('%Y-%m-%d %H:%M:%S'))


def admin_keyboard():
    return ['List all', 'Back']


def is_admin(user_id: int):
    user_data = my_persistence.get_user_data().get(user_id)
    return bool(user_data and 'admin' in user_data and user_data["admin"] and user_data['status'] == READY)


def get_default_keyboard_bottom(user_id: int):
    key_board = ['Status', 'Info']
    if is_admin(user_id):
        in_admin_convs = my_persistence.get_conversations("admin_conversation").get(tuple([user_id, user_id]))
        if in_admin_convs:
            return admin_keyboard()

        key_board.append("Admin")

    return key_board


def facts_to_str(user_data: Dict[str, str]) -> str:
    facts = []

    for key, value in user_data.items():
        facts.append(f'{key} - {value}')

    return "\n".join(facts).join(['\n', '\n'])


def start(update: Update, context: CallbackContext) -> int:
    reply_text = state_texts[STARTING]
    for key, value in update.effective_user.to_dict().items():
        context.user_data[key] = value
    context.user_data["created"] = datetime.datetime.now().timestamp()
    context.user_data['status'] = WELCOME
    update.message.reply_text(
        reply_text,
        reply_markup=ReplyKeyboardMarkup([['Join waiting list'], get_default_keyboard_bottom(update.effective_user.id)],
                                         one_time_keyboard=True))

    return STARTING


def join_waiting_list(update: Update, context: CallbackContext) -> Optional[int]:
    if context.user_data['status'] is not WELCOME:
        update.message.reply_text(
            'Чет у тебя не тот статус, чтобы в списке ожидания быть'
        )
        return None
    context.user_data['status'] = IN_WAITING_LIST

    markup_buttons = []
    if "first_name" in context.user_data or "last_name" in context.user_data:
        full_name = helper.safe_list_get(context.user_data, "first_name", "") + ' ' + helper.safe_list_get(
            context.user_data, "last_name", "")
        markup_buttons = [[InlineKeyboardButton(text=full_name, callback_data=full_name)]]

    update.message.reply_text(
        text=state_texts[WAITING_NAME],
        reply_markup=InlineKeyboardMarkup(markup_buttons))

    return WAITING_NAME


def set_name(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    context.user_data['name'] = text
    reply_text = (
        f'Приветы, {text}! Скинь, плиз, ссылку на инсту'
    )
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup([
            get_default_keyboard_bottom(update.effective_user.id)], one_time_keyboard=True))

    return WAITING_INSTA


def set_name_callback(update: Update, context: CallbackContext) -> int:
    text = update.callback_query.data
    context.user_data['name'] = text
    reply_text = (
        f'Приветы, {text}! Скинь, плиз, ссылку на инсту'
    )

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=reply_text)

    return WAITING_INSTA


def set_insta(update: Update, context: CallbackContext) -> Optional[int]:
    text = update.message.text
    if not search('instagram.com', text):
        replay_text = "Хах, это не инста! Давай-ка ссылку на инсту, например, https://www.instagram.com/badfestbad"
        update.message.reply_text(
            replay_text, reply_markup=ReplyKeyboardMarkup([
                get_default_keyboard_bottom(update.effective_user.id)], one_time_keyboard=True))
        return None

    context.user_data['insta'] = text
    reply_text = "Супер! Еще чуть-чуть. Теперь ссылочку на VK, плиз"
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup([
            get_default_keyboard_bottom(update.effective_user.id)], one_time_keyboard=True))

    return WAITING_VK


def set_vk(update: Update, context: CallbackContext) -> Optional[int]:
    text = update.message.text
    if not search('vk.com', text):
        replay_text = "Хах, это не вк! Давай-ка ссылку на вк, например, https://vk.com/badfest/"
        update.message.reply_text(
            replay_text, reply_markup=ReplyKeyboardMarkup([
                get_default_keyboard_bottom(update.effective_user.id)], one_time_keyboard=True))
        return None

    context.user_data['vk'] = text
    reply_text = state_texts[WAITING_APPROVE]
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup([
            get_default_keyboard_bottom(update.effective_user.id)], one_time_keyboard=True))

    return WAITING_APPROVE


def done(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f"Все, что знаем о тебе: {facts_to_str(context.user_data)}"
    )


def state_text(update: Update, context: CallbackContext):
    convs = my_persistence.get_conversations("my_conversation")
    state = convs.get(tuple([update.effective_user.id, update.effective_user.id]))
    if state:
        update.message.reply_text(
            state_texts[state], reply_markup=ReplyKeyboardMarkup([
                get_default_keyboard_bottom(update.effective_user.id)],
                resize_keyboard=True,
                one_time_keyboard=True))
    else:
        update.message.reply_text("Жамкни /start")

    return None


def admin_dashboard(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    update.message.reply_text(
        'Милорд!', reply_markup=ReplyKeyboardMarkup([
            ['List all', 'Back']
        ], one_time_keyboard=True))

    return ADMIN_DASHBOARD


def admin_list(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    i = 1  # что это блять, Илюша?
    reply_html = "<b>Все участники:</b> \n"
    users = my_persistence.fb_user_data.order_by_child("created").get()
    for user_id, user in reversed(users.items()):
        # user = my_persistence.fb_user_data.child(str(user_id)).get()
        reply_html += user_to_text(user, i)
        i += 1

    update.message.reply_html(
        reply_html, reply_markup=ReplyKeyboardMarkup([
            ['List all', 'Back']
        ],
            disable_web_page_preview=True,
            one_time_keyboard=True))
    return None


def admin_back(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Возвращайтесь, админка ждет своего господина!', reply_markup=ReplyKeyboardMarkup([
            get_default_keyboard_bottom(update.effective_user.id)
        ], one_time_keyboard=True))
    return -1


def show_data(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f"Все, что знаем о тебе: {facts_to_str(context.user_data)}"
    )
    return None


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater("1729903490:AAERypw3yDXPCK4ikqKsc8um7NOHBXj5gBc", persistence=my_persistence)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    show_data_handler = MessageHandler(Filters.regex('^Status$'), done)
    dispatcher.add_handler(show_data_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STARTING: [
                MessageHandler(Filters.regex('^Join waiting list$'), join_waiting_list),
            ],
            WAITING_NAME: [
                MessageHandler(
                    Filters.text, set_name
                ),
                CallbackQueryHandler(set_name_callback),
            ],
            WAITING_INSTA: [
                MessageHandler(
                    Filters.text, set_insta,
                )
            ],
            WAITING_VK: [
                MessageHandler(
                    Filters.text, set_vk,
                )
            ],
            WAITING_APPROVE: [],
        },
        fallbacks=[],
        name="my_conversation",
        persistent=True,
    )
    dispatcher.add_handler(conv_handler)

    conv_admin_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Admin$'), admin_dashboard)],
        states={
            ADMIN_DASHBOARD: [
                MessageHandler(Filters.regex('^List all'), admin_list),
                MessageHandler(Filters.regex('^Back'), admin_back)
            ]
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)],
        name="admin_conversation",
        persistent=True,
    )
    dispatcher.add_handler(conv_admin_handler)

    show_data_handler = MessageHandler(Filters.text, state_text)
    dispatcher.add_handler(show_data_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
