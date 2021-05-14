#!/usr/bin/env python
# pylint: disable=C0116
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using nested ConversationHandlers.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from typing import Tuple, Dict, Any

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
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

# State definitions for top level conversation
SELECTING_ACTION, ADDING_MEMBER, ADDING_SELF, DESCRIBING_SELF = map(chr, range(4))
# State definitions for second level conversation
SELECTING_LEVEL, SELECTING_GENDER = map(chr, range(4, 6))
# State definitions for descriptions conversation
SELECTING_FEATURE, TYPING = map(chr, range(6, 8))
# Meta states
STOPPING, SHOWING = map(chr, range(8, 10))
# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Different constants for this example
(
    PARENTS,
    CHILDREN,
    SELF,
    GENDER,
    MALE,
    FEMALE,
    AGE,
    NAME,
    START_OVER,
    FEATURES,
    CURRENT_FEATURE,
    CURRENT_LEVEL,
) = map(chr, range(10, 22))


# Helper
def _name_switcher(level: str) -> Tuple[str, str]:
    if level == PARENTS:
        return 'Father', 'Mother'
    return 'Brother', 'Sister'


# Top level conversation callbacks
def start(update: Update, context: CallbackContext) -> str:
    """Select an action: Adding parent/child or show data."""
    text = (
        "You may choose to add a family member, yourself, show the gathered data, or end the "
        "conversation. To abort, simply type /stop."
    )

    buttons = [
        [
            InlineKeyboardButton(text='Add family member', callback_data=str(ADDING_MEMBER)),
            InlineKeyboardButton(text='Add yourself', callback_data=str(ADDING_SELF)),
        ],
        [
            InlineKeyboardButton(text='Show data', callback_data=str(SHOWING)),
            InlineKeyboardButton(text='Done', callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need to send a new message
    if context.user_data.get(START_OVER):
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        update.message.reply_text(
            "Hi, I'm Family Bot and I'm here to help you gather information about your family."
        )
        update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_ACTION


def adding_self(update: Update, context: CallbackContext) -> str:
    """Add information about yourself."""
    context.user_data[CURRENT_LEVEL] = SELF
    text = 'Okay, please tell me about yourself.'
    button = InlineKeyboardButton(text='Add info', callback_data=str(MALE))
    keyboard = InlineKeyboardMarkup.from_button(button)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return DESCRIBING_SELF


def show_data(update: Update, context: CallbackContext) -> str:
    """Pretty print gathered data."""

    def prettyprint(user_data: Dict[str, Any], level: str) -> str:
        people = user_data.get(level)
        if not people:
            return '\nNo information yet.'

        text = ''
        if level == SELF:
            for person in user_data[level]:
                text += f"\nName: {person.get(NAME, '-')}, Age: {person.get(AGE, '-')}"
        else:
            male, female = _name_switcher(level)

            for person in user_data[level]:
                gender = female if person[GENDER] == FEMALE else male
                text += f"\n{gender}: Name: {person.get(NAME, '-')}, Age: {person.get(AGE, '-')}"
        return text

    user_data = context.user_data
    text = f"Yourself:{prettyprint(user_data, SELF)}"
    text += f"\n\nParents:{prettyprint(user_data, PARENTS)}"
    text += f"\n\nChildren:{prettyprint(user_data, CHILDREN)}"

    buttons = [[InlineKeyboardButton(text='Back', callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    user_data[START_OVER] = True

    return SHOWING


def stop(update: Update, _: CallbackContext) -> int:
    """End Conversation by command."""
    update.message.reply_text('Okay, bye.')

    return END


def end(update: Update, _: CallbackContext) -> int:
    """End conversation from InlineKeyboardButton."""
    update.callback_query.answer()

    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)

    return END


# Second level conversation callbacks
def select_level(update: Update, _: CallbackContext) -> str:
    """Choose to add a parent or a child."""
    text = 'You may add a parent or a child. Also you can show the gathered data or go back.'
    buttons = [
        [
            InlineKeyboardButton(text='Add parent', callback_data=str(PARENTS)),
            InlineKeyboardButton(text='Add child', callback_data=str(CHILDREN)),
        ],
        [
            InlineKeyboardButton(text='Show data', callback_data=str(SHOWING)),
            InlineKeyboardButton(text='Back', callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_LEVEL


def select_gender(update: Update, context: CallbackContext) -> str:
    """Choose to add mother or father."""
    level = update.callback_query.data
    context.user_data[CURRENT_LEVEL] = level

    text = 'Please choose, whom to add.'

    male, female = _name_switcher(level)

    buttons = [
        [
            InlineKeyboardButton(text=f'Add {male}', callback_data=str(MALE)),
            InlineKeyboardButton(text=f'Add {female}', callback_data=str(FEMALE)),
        ],
        [
            InlineKeyboardButton(text='Show data', callback_data=str(SHOWING)),
            InlineKeyboardButton(text='Back', callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_GENDER


def end_second_level(update: Update, context: CallbackContext) -> int:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    start(update, context)

    return END


# Third level callbacks
def select_feature(update: Update, context: CallbackContext) -> str:
    """Select a feature to update for the person."""
    buttons = [
        [
            InlineKeyboardButton(text='Name', callback_data=str(NAME)),
            InlineKeyboardButton(text='Age', callback_data=str(AGE)),
            InlineKeyboardButton(text='Done', callback_data=str(END)),
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we collect features for a new person, clear the cache and save the gender
    if not context.user_data.get(START_OVER):
        context.user_data[FEATURES] = {GENDER: update.callback_query.data}
        text = 'Please select a feature to update.'

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # But after we do that, we need to send a new message
    else:
        text = 'Got it! Please select a feature to update.'
        update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_FEATURE


def ask_for_input(update: Update, context: CallbackContext) -> str:
    """Prompt user to input data for selected feature."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = 'Okay, tell me.'

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return TYPING


def save_input(update: Update, context: CallbackContext) -> str:
    """Save input for feature and return to feature selection."""
    user_data = context.user_data
    user_data[FEATURES][user_data[CURRENT_FEATURE]] = update.message.text

    user_data[START_OVER] = True

    return select_feature(update, context)


def end_describing(update: Update, context: CallbackContext) -> int:
    """End gathering of features and return to parent conversation."""
    user_data = context.user_data
    level = user_data[CURRENT_LEVEL]
    if not user_data.get(level):
        user_data[level] = []
    user_data[level].append(user_data[FEATURES])

    # Print upper level menu
    if level == SELF:
        user_data[START_OVER] = True
        start(update, context)
    else:
        select_level(update, context)

    return END


def stop_nested(update: Update, _: CallbackContext) -> str:
    """Completely end conversation from within nested conversation."""
    update.message.reply_text('Okay, bye.')

    return STOPPING


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater("1729903490:AAERypw3yDXPCK4ikqKsc8um7NOHBXj5gBc",
                      persistence=my_persistence,
                      use_context=True,
                      )

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Set up third level ConversationHandler (collecting features)
    description_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                select_feature, pattern='^' + str(MALE) + '$|^' + str(FEMALE) + '$'
            )
        ],
        states={
            SELECTING_FEATURE: [
                CallbackQueryHandler(ask_for_input, pattern='^(?!' + str(END) + ').*$')
            ],
            TYPING: [MessageHandler(Filters.text & ~Filters.command, save_input)],
        },
        fallbacks=[
            CallbackQueryHandler(end_describing, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested),
        ],
        map_to_parent={
            # Return to second level menu
            END: SELECTING_LEVEL,
            # End conversation altogether
            STOPPING: STOPPING,
        },
    )

    # Set up second level ConversationHandler (adding a person)
    add_member_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_level, pattern='^' + str(ADDING_MEMBER) + '$')],
        states={
            SELECTING_LEVEL: [
                CallbackQueryHandler(select_gender, pattern=f'^{PARENTS}$|^{CHILDREN}$')
            ],
            SELECTING_GENDER: [description_conv],
        },
        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested),
        ],
        map_to_parent={
            # After showing data return to top level menu
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation altogether
            STOPPING: END,
        },
    )

    # Set up top level ConversationHandler (selecting action)
    # Because the states of the third level conversation map to the ones of the second level
    # conversation, we need to make sure the top level conversation can also handle them
    selection_handlers = [
        add_member_conv,
        CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
        CallbackQueryHandler(adding_self, pattern='^' + str(ADDING_SELF) + '$'),
        CallbackQueryHandler(end, pattern='^' + str(END) + '$'),
    ]
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SHOWING: [CallbackQueryHandler(start, pattern='^' + str(END) + '$')],
            SELECTING_ACTION: selection_handlers,
            SELECTING_LEVEL: selection_handlers,
            DESCRIBING_SELF: [description_conv],
            STOPPING: [CommandHandler('start', start)],
        },
        fallbacks=[CommandHandler('stop', stop)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
