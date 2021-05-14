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

import logging
from typing import Dict

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    PicklePersistence,
    CallbackContext,
)

from ptb_firebase_persistence import FirebasePersistence

my_persistence = FirebasePersistence(
    database_url='https://badfest-invites-default-rtdb.europe-west1.firebasedatabase.app',
    credentials={
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
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

reply_keyboard = [
    ['Age', 'Favourite colour'],
    ['Number of siblings', 'Something else...'],
    ['Done'],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


def facts_to_str(user_data: Dict[str, str]) -> str:
    facts = []

    for key, value in user_data.items():
        facts.append(f'{key} - {value}')

    return "\n".join(facts).join(['\n', '\n'])


def start(update: Update, context: CallbackContext) -> int:
    reply_text = "Привет! Ты пришел без кода"
    if context.user_data:
        reply_text += (
            f" You already told me your {', '.join(context.user_data.keys())}. Why don't you "
            f"tell me something more about yourself? Or change anything I already know."
        )
    else:
        reply_text += (
            " I will hold a more complex conversation with you. Why don't you tell me "
            "something about yourself?"
        )
    update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


def regular_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text.lower()
    context.user_data['choice'] = text
    if context.user_data.get(text):
        reply_text = (
            f'Your {text}? I already know the following about that: {context.user_data[text]}'
        )
    else:
        reply_text = f'Your {text}? Yes, I would love to hear about that!'
    update.message.reply_text(reply_text)

    return TYPING_REPLY


def custom_choice(update: Update, _: CallbackContext) -> int:
    update.message.reply_text(
        'Alright, please send me the category first, for example "Most impressive skill"'
    )

    return TYPING_CHOICE


def received_information(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    category = context.user_data['choice']
    context.user_data[category] = text.lower()
    del context.user_data['choice']

    update.message.reply_text(
        "Neat! Just so you know, this is what you already told me:"
        f"{facts_to_str(context.user_data)}"
        "You can tell me more, or change your opinion on "
        "something.",
        reply_markup=markup,
    )

    return CHOOSING


def show_data(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f"This is what you already told me: {facts_to_str(context.user_data)}"
    )


def done(update: Update, context: CallbackContext) -> int:
    if 'choice' in context.user_data:
        del context.user_data['choice']

    update.message.reply_text(
        "I learned these facts about you:" f"{facts_to_str(context.user_data)}Until next time!",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    # Create the Updater and pass it your bot's token.
    persistence = PicklePersistence(filename='conversationbot')
    updater = Updater("1729903490:AAERypw3yDXPCK4ikqKsc8um7NOHBXj5gBc", persistence=my_persistence)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(
                    Filters.regex('^(Age|Favourite colour|Number of siblings)$'), regular_choice
                ),
                MessageHandler(Filters.regex('^Something else...$'), custom_choice),
            ],
            TYPING_CHOICE: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^Done$')), regular_choice
                )
            ],
            TYPING_REPLY: [
                MessageHandler(
                    Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                    received_information,
                )
            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), done)],
        name="my_conversation",
        persistent=True,
    )

    dispatcher.add_handler(conv_handler)

    show_data_handler = CommandHandler('show_data', show_data)
    dispatcher.add_handler(show_data_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
