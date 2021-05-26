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
import json
from emoji import emojize
from re import search
from typing import Optional
from telegram import ReplyKeyboardMarkup, Update, ParseMode, TelegramError, ReplyKeyboardRemove, LabeledPrice
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.types import ConversationDict

from purchases import Purchase
from settings import Settings
from tickets import Ticket
from users import User
from invites import Invite
from error_handler import error_handler
from fire_persistence import FirebasePersistence
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackQueryHandler,
    CallbackContext, PreCheckoutQueryHandler,
)

# Enable logging
from utils import helper

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

store = FirebasePersistence()

STARTING, WAITING_NAME, WAITING_INSTA, \
WAITING_VK, WAITING_APPROVE, WAITING_PAYMENT, \
WAITING_FOR_MANUAL_CODE, READY_DASHBOARD, ADMIN_DASHBOARD = range(1, 10)

BUTTON_JOIN_WAITING_LIST = "Join waiting list"
BUTTON_ADMIN_CHECK_NEEDED = "Надо проверить"
BUTTON_ADMIN_KARINA = "Карина-кнопка"
BUTTON_ADMIN_WAITING_LIST = "В списке ожидания"
BUTTON_ADMIN_ALL = "Все пользователи"
BUTTON_I_HAVE_CODE = "У меня есть код"
BUTTON_BACK = "Назад"
BUTTON_INVITES = "Приглашения"
BUTTON_TICKETS = "Билеты"
BUTTON_MY_TICKET = "Мой билет"
CALLBACK_MORE_INVITES = "Moreinvites"
CALLBACK_BUTTON_BACK = "Realname"
CALLBACK_BUTTON_GIFT_TICKET = "Gift"

state_texts = dict([
    (STARTING, 'Привет! Это бот BadFest 2021'),
    (WAITING_NAME, 'Такс, давай знакомиться! Немного вопросиков, чтобы мы знали, кто ты такой(ая). \nКак тебя зовут?'),
    (WAITING_INSTA, 'Скинь, плиз, ссылку на инсту'),
    (WAITING_VK, 'Скинь, плиз, ссылку на vk'),
    (WAITING_APPROVE, 'Ну все, теперь жди - как только модераторы тебя чекнут, тебе прилетят реферальные '
                      'ссылки, чтобы пригласить друзей, а также ты сможешь оплатить билет прямо тут.'),
    (WAITING_PAYMENT, "Хей! Тебя заапрувили! Теперь ты можешь покупать билет, а также у тебя есть две ссылки,"
                      " по которым ты можешь пригласить друзей.\n"
                      "Приглашай только тех, за кого можешь поручиться =)" \
                      "\nИ не забывай про билеты - они будут дорожать пропорционально изменению курса битка по модулю раз в несколько дней." \
                      "\n\nИспользуй кнопки бота для перехода к билетам и ссылкам для друзей."),
    (WAITING_FOR_MANUAL_CODE, "Супер! Введи код, плиз:"),
    (READY_DASHBOARD, "Ура! У тебя есть билет на BadFest 2021!")
])

CONVERSATION_NAME = "user_states_conversation"


# Telegram bot keyboards functions

def admin_keyboard(buttons=None):
    if buttons is None:
        buttons = []
    buttons.append([str(BUTTON_ADMIN_CHECK_NEEDED), str(BUTTON_ADMIN_WAITING_LIST)])
    buttons.append([str(BUTTON_ADMIN_ALL), 'Back'])
    return buttons


def get_default_keyboard_bottom(user: User, buttons=None, is_admin_in_convs=True):
    convs = store.get_conversations(str(CONVERSATION_NAME))
    state = convs.get(tuple([user.id]))

    if buttons is None:
        buttons = []

    if state in [WAITING_APPROVE] and user.status == User.STATUS_IN_WAITING_LIST_CHECKED:
        buttons.append([str(BUTTON_I_HAVE_CODE)])

    if user.status == User.STATUS_WELCOME:
        buttons.append([str(BUTTON_JOIN_WAITING_LIST)])

    if state in [WAITING_PAYMENT] and user.status == User.STATUS_APPROVED:
        buttons.append([str(BUTTON_INVITES), str(BUTTON_TICKETS)])

    if state in [READY_DASHBOARD]:
        buttons.append([str(BUTTON_INVITES), str(BUTTON_MY_TICKET)])

    key_board = ['Status', 'Info']
    if user.admin:
        in_admin_convs = store.get_conversations("admin_conversation").get(tuple([user.id]))
        if is_admin_in_convs and in_admin_convs:
            return admin_keyboard(buttons)

        key_board.append("Admin")

    buttons.append(key_board)
    return buttons


# Helpers

def check_code_on_start(update: Update, code: str):
    try:
        invite = Invite.get(code)
    except TelegramError:
        update.message.reply_text(
            "Нет такого кода реферального. Ты можешь пользоваться ботом и записаться в список ожидания, "
            "но это такое...\n"
            "Лучше проверь ссылку от друга на актуальность и перейди по ней заново ;)",
        )
        return False

    if invite.activated():
        update.message.reply_text(
            "Эта ссылка уже активирована - попроси у друга новую и перейди по ней заново.\n"
            "Ты можешь пользоваться ботом и записаться в список ожидания, но это такое.\n"
        )
        return False

    return True


def create_new_user(_id: int, _data: dict, status):
    user = User.create_new(_id)
    user.set_data(_data)
    user.status = status
    user.save()
    return user


# User actions (changes conversation state)

def action_start(update: Update, context: CallbackContext) -> None:
    if len(context.args) and context.args[0]:
        code = context.args[0]
        check = check_code_on_start(update, code)
        if not check:
            return None

        invite = Invite.get(code)
        reply_text = f"Хей! Это персональное тебе приглашение на BadFest 2021 от {invite.creator.real_name}.\n" \
                     f"Почитай информацию по кнопке Info внизу."
        update.message.reply_text(reply_text,
                                  reply_markup=ReplyKeyboardMarkup([['Info']],
                                                                   resize_keyboard=True,
                                                                   one_time_keyboard=True),
                                  disable_web_page_preview=True)

        markup_buttons = [[
            InlineKeyboardButton(text="Принять", callback_data=f"Accept:{code}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"Decline:{code}"),
        ]]
        update.message.reply_text(
            text=f"И принимай решение по приглашению:",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(markup_buttons))
        return None

    reply_text = state_texts[STARTING]

    user = create_new_user(update.effective_user.id, update.effective_user.to_dict(), User.STATUS_WELCOME)
    update.message.reply_text(
        reply_text,
        reply_markup=ReplyKeyboardMarkup(get_default_keyboard_bottom(user),
                                         resize_keyboard=True, one_time_keyboard=True), disable_web_page_preview=True, )

    return STARTING


def accept_invite(update: Update, context: CallbackContext) -> Optional[int]:
    code = update.callback_query.data.split(':')[1]
    check = check_code_on_start(update, code)
    if not check:
        return None
    invite = Invite.get(code)
    user = create_new_user(update.effective_user.id, update.effective_user.to_dict(), User.STATUS_BY_REFERRAL)
    invite.participant = user
    invite.save()

    context.bot.send_message(chat_id=invite.creator.id,
                             text=f"Ееееее! {user.full_name()} {user.username} принял(а) твое приглашение! :)")

    markup_buttons = []
    if user.first_name or user.last_name:
        markup_buttons = [
            [InlineKeyboardButton(text=user.full_name(), callback_data=f"{CALLBACK_BUTTON_BACK}:{user.full_name()}")]]

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=state_texts[WAITING_NAME],
                                            disable_web_page_preview=True,
                                            reply_markup=InlineKeyboardMarkup(markup_buttons),
                                            parse_mode=ParseMode.HTML)

    return WAITING_NAME


def decline_invite(update: Update, context: CallbackContext) -> Optional[int]:
    code = update.callback_query.data.split(':')[1]
    invite = Invite.get(code)
    context.bot.send_message(chat_id=invite.creator.id, text=f"Твое приглашение ({code}) не приняли :(")

    update.callback_query.answer()
    update.callback_query.edit_message_text(text="Штош. Если передумаешь, можешь заново пройти по ссылке"
                                                 " либо записаться в список ожидания - для этого напиши что-нибудь сюда.",
                                            disable_web_page_preview=True,
                                            parse_mode=ParseMode.HTML)

    return None


def action_join_waiting_list(update: Update, context: CallbackContext) -> Optional[int]:
    user = User.get(update.effective_user.id)
    if user.status != User.STATUS_WELCOME:
        update.message.reply_text(
            'Чет у тебя не тот статус, чтобы в списке ожидания быть'
        )
        return None

    user.status = User.STATUS_IN_WAITING_LIST
    user.save()

    markup_buttons = []
    if user.first_name or user.last_name:
        markup_buttons = [
            [InlineKeyboardButton(text=user.full_name(), callback_data=f"{CALLBACK_BUTTON_BACK}:{user.full_name()}")]]

    update.message.reply_text(
        text=state_texts[WAITING_NAME],
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(markup_buttons))

    return WAITING_NAME


def action_set_name(update: Update, context: CallbackContext) -> int:
    user = User.get(update.effective_user.id)
    text = update.message.text
    user.real_name = text.strip()
    user.save()

    reply_text = (
        f'Приветы, {user.real_name}! Скинь, плиз, ссылку на инсту'
    )
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True, )

    return WAITING_INSTA


def action_set_name_callback(update: Update, context: CallbackContext) -> int:
    user = User.get(update.effective_user.id)
    real_name = update.callback_query.data.split(':')[1]
    user.real_name = real_name.strip()
    user.save()

    reply_text = (
        f'Приветы, {user.real_name}! Скинь, плиз, ссылку на инсту'
    )

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=reply_text)

    return WAITING_INSTA


def action_set_insta(update: Update, context: CallbackContext) -> Optional[int]:
    user = User.get(update.effective_user.id)
    text = update.message.text.strip()
    if not search('instagram.com', text):
        replay_text = "Хах, это не инста! Давай-ка ссылку на инсту, например, https://www.instagram.com/badfestbad"
        update.message.reply_text(
            replay_text, reply_markup=ReplyKeyboardMarkup(
                get_default_keyboard_bottom(user),
                resize_keyboard=True, one_time_keyboard=True), disable_web_page_preview=True, )
        return None

    user.insta = text
    user.save()

    reply_text = "Супер! Еще чуть-чуть. Теперь ссылочку на VK, плиз"
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True, )

    return WAITING_VK


def action_set_vk(update: Update, context: CallbackContext) -> Optional[int]:
    user = User.get(update.effective_user.id)
    text = update.message.text.strip()
    if not search('vk.com', text):
        replay_text = "Хах, это не вк! Давай-ка ссылку на вк, например, https://vk.com/badfest/"
        update.message.reply_text(
            replay_text, reply_markup=ReplyKeyboardMarkup(
                get_default_keyboard_bottom(user),
                resize_keyboard=True, one_time_keyboard=True), disable_web_page_preview=True, )
        return None

    user.vk = text

    if user.status == User.STATUS_IN_WAITING_LIST:
        user.status = User.STATUS_IN_WAITING_LIST_CHECKED

    if user.status == User.STATUS_BY_REFERRAL:
        user.status = User.STATUS_BY_REFERRAL_CHECKED

    user.save()

    update_conversation(str(CONVERSATION_NAME), user, WAITING_APPROVE)

    reply_text = state_texts[WAITING_APPROVE]
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user),
            resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)

    for admin in User.admins():
        message = "Надо проверить нового участника: " + user.pretty_html() + "\n"
        context.bot.send_message(chat_id=admin.id, text=message, parse_mode=ParseMode.HTML)

    return WAITING_APPROVE


def action_wait_code(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    update.message.reply_text(
        state_texts[WAITING_FOR_MANUAL_CODE], reply_markup=ReplyKeyboardRemove(), disable_web_page_preview=True)

    return WAITING_FOR_MANUAL_CODE


def action_back_from_manual_code(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    update.message.reply_text(
        state_texts[WAITING_APPROVE], reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user, [[str(BUTTON_I_HAVE_CODE)]]), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)

    return WAITING_APPROVE


def action_enter_code(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    code = update.message.text.strip()
    try:
        invite = Invite.get(code)
    except TelegramError:
        update.message.reply_text("Нет такого кода реферального", reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user, [[str(BUTTON_BACK)]]), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)
        return None

    if invite.activated():
        update.message.reply_text("Этот код уже активирован - попроси у друга новый", reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user, [[str(BUTTON_BACK)]]), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)
        return None

    user.status = User.STATUS_BY_REFERRAL_CHECKED
    user.save()

    invite = Invite.get(code)
    invite.participant = user
    invite.save()

    context.bot.send_message(chat_id=invite.creator.id,
                             text=f"Ееееее! {user.full_name()} {user.username} принял(а) твое приглашение! :)")

    update.message.reply_text("Шик! Код успешно применен! Жди проверку модератора.", reply_markup=ReplyKeyboardMarkup(
        get_default_keyboard_bottom(user), resize_keyboard=True,
        one_time_keyboard=True), disable_web_page_preview=True)

    return WAITING_APPROVE


def action_successful_payment_callback(update: Update, context: CallbackContext) -> None:
    # successfully receiving payment 1111 1111 1111 1026, 12/22, CVC 000.
    payment = update.message.successful_payment
    user = User.get(update.effective_user.id)

    purchase = Purchase.create_new(update.message.successful_payment.provider_payment_charge_id)
    purchase.currency = payment.currency
    purchase.total_amount = payment.total_amount
    purchase.ticket = Ticket.get(payment.invoice_payload)
    purchase.user = user
    purchase.phone_number = helper.safe_list_get(payment.order_info, "phone_number")
    purchase.email = helper.safe_list_get(payment.order_info, "email")
    purchase.telegram_payment_charge_id = payment.telegram_payment_charge_id
    purchase.provider_payment_charge_id = payment.provider_payment_charge_id
    purchase.save()

    purchase.create_image()

    user.status = User.STATUS_READY
    user.purchase_id = purchase.id
    user.save()

    update_conversation(str(CONVERSATION_NAME), user, READY_DASHBOARD)

    update.message.reply_text(state_texts[READY_DASHBOARD], reply_markup=ReplyKeyboardMarkup(
        get_default_keyboard_bottom(user), resize_keyboard=True, one_time_keyboard=True),
                              disable_web_page_preview=True,
                              parse_mode=ParseMode.HTML)

    reply_html = purchase.pretty_html()
    context.bot.send_message(
        user.id,
        text=reply_html,
        disable_web_page_preview=True)

    try:
        with open(f'images/{purchase.id}.png', 'rb') as f:
            context.bot.send_photo(user.id, photo=f, timeout=50)
    except:
        logging.log(logging.ERROR, "File not found")

    return READY_DASHBOARD


# User show data functions:

def show_info(update: Update, context: CallbackContext):
    update.message.reply_html(
        f"Здесь будет вся информация про фест"
    )


def show_invites(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    index = 1

    update.message.reply_html(
        text="Зови друзей, пересылая приглашения ниже:",
        disable_web_page_preview=True)

    invites = Invite.by_creator(user)

    for invite in invites:
        reply_html = invite.pretty_html(index)
        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True)
        index += 1

    max_invites = int(Settings.max_invites())
    if len(invites) >= max_invites:
        update.message.reply_html(
            text=f"Больше приглашений на одного участника выдать не получится :(",
            disable_web_page_preview=True)
    else:
        markup_buttons = [
            [InlineKeyboardButton(text="Выдайте мне еще", callback_data=f"{CALLBACK_MORE_INVITES}")]]

        update.message.reply_text(
            text=f"Всего у тебя {len(invites)} приглашения(ий)",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(markup_buttons))


def show_my_ticket(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    for purchase in Purchase.by_user(user):
        reply_html = purchase.pretty_html()
        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True)
        try:
            with open(f'images/{purchase.id}.png', 'rb') as f:
                context.bot.send_photo(user.id, photo=f, timeout=50)
        except:
            logging.log(logging.ERROR, "File not found")


def show_tickets(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if user.status != User.STATUS_APPROVED:
        update.message.reply_text("Рано еще!")
        return None

    index = 1
    update.message.reply_html(
        text="Выбирай билет и покупай прямо тут в телеграме (да, так уже можно, начиная с апреля этого года)\n"
             "Продолжая покупку, ты соглашаешься с <a href='http://badbar.ru'>правилами использования</a>, "
             "<a href='http://badbar.ru'>политикой конфеденциальности</a> и "
             "<a href='http://badbar.ru'>прочей лабудой</a>, которая нам, к сожалению, нужна:\n\n ",
        disable_web_page_preview=True)

    for ticket in Ticket.by_type(Ticket.PAID_TYPE):
        # reply_html = ticket.pretty_html(index)
        payload = ticket.id
        provider_token = "381764678:TEST:26026"
        currency = "RUB"
        prices = [LabeledPrice(ticket.id, ticket.price * 10000)]

        context.bot.send_invoice(
            user.id, emojize(":admission_tickets:", use_aliases=True) + ticket.id,
            ticket.description, payload, provider_token, currency, prices,
            need_email=True, need_phone_number=True, max_tip_amount=100000
        )

        index += 1


def precheckout_callback(update: Update, _: CallbackContext) -> None:
    query = update.pre_checkout_query

    if not query.invoice_payload:
        query.answer(ok=False, error_message=f"Payload какой-то не такой... пустой, нет его")
        return None

    try:
        Ticket.get(query.invoice_payload)
    except:
        query.answer(ok=False, error_message=f"Нет билета с таким id:{query.invoice_payload}")
        return None

    try:
        user = User.get(query.from_user.id)
        if user.status != User.STATUS_APPROVED:
            query.answer(ok=False, error_message=f"Так так... Пользователь {user.real_name} с id {user.id} "
                                                 f"и статусом {user.status} не подтвержден для покупки.")
            return None
    except:
        # answer False pre_checkout_query
        query.answer(ok=False, error_message=f"Нет пользователя с таким id:{query.from_user.id}")
        return None

    query.answer(ok=True)


def show_status(update: Update, context: CallbackContext) -> None:
    update.message.reply_html(
        f"Все, что знаем о тебе\n\n{User.get(update.effective_user.id).pretty_html()}"
    )


def show_state_text(update: Update, context: CallbackContext):
    convs = store.get_conversations(str(CONVERSATION_NAME))
    state = convs.get(tuple([update.effective_user.id]))
    if state:
        update.message.reply_text(
            state_texts[state], reply_markup=ReplyKeyboardMarkup(
                get_default_keyboard_bottom(User.get(update.effective_user.id)),
                resize_keyboard=True,
                one_time_keyboard=True), disable_web_page_preview=True, )
    else:
        update.message.reply_text("Жамкни /start, только если у тебя нет ссылки от друга/подруги")

    return None


# Admin actions:

def admin_action_dashboard(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    update.message.reply_text(
        'Милорд!',
        reply_markup=ReplyKeyboardMarkup(admin_keyboard(), resize_keyboard=True,
                                         one_time_keyboard=True), disable_web_page_preview=True, )

    return ADMIN_DASHBOARD


def admin_action_back(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    update.message.reply_text(
        'Возвращайтесь, админка ждет своего господина!', reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user, None, False),
            resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)
    return -1


# Admin show data functions:

def admin_show_list(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    if not len(context.matches):
        update.message.reply_text("Неверная команда")
        return None

    users = []
    if context.matches[0].string == BUTTON_ADMIN_ALL:
        users = User.all()

    if context.matches[0].string == BUTTON_ADMIN_KARINA:
        users = User.all()  # todo add filters

    i = 1
    invites = Invite.all()
    for user in users:
        reply_html = user.pretty_html(i)
        try:
            invite = Invite.by_participant(user, cached_invites=invites)[0]
            reply_html += f"\nКто пригласил: {invite.creator.real_name} {invite.creator.username}"
        except:
            pass

        markup_buttons = []
        if not user.purchase_id and (user.status in [User.STATUS_APPROVED]):
            markup_buttons.append([
                InlineKeyboardButton(
                    text='Выдать билет', callback_data=f"{str(CALLBACK_BUTTON_GIFT_TICKET)}:" + str(user.id))
            ])

        if user.purchase_id:
            reply_html = emojize(":admission_tickets:", use_aliases=True) + " " + reply_html

            purchase = Purchase.get(user.purchase_id)
            reply_html += f"Билет: {purchase.ticket_name} {purchase.total_amount / 100} р.\n" \
                          f"Время покупки: {purchase.created}"

        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(markup_buttons))
        i += 1

    update.message.reply_html(
        "Всего пользователей: " + str(len(users)), reply_markup=ReplyKeyboardMarkup(
            admin_keyboard(),
            resize_keyboard=True,
            one_time_keyboard=False), disable_web_page_preview=True, )
    return None


def admin_show_approval_list(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    if not len(context.matches):
        update.message.reply_text("Неверная команда")
        return None

    users = []
    if context.matches[0].string == BUTTON_ADMIN_WAITING_LIST:
        users = User.by_status(User.STATUS_IN_WAITING_LIST_CHECKED)

    if context.matches[0].string == BUTTON_ADMIN_CHECK_NEEDED:
        users = User.by_status(User.STATUS_BY_REFERRAL_CHECKED)

    i = 1
    invites = Invite.all()
    for user in users:
        reply_html = user.pretty_html(i)
        try:
            invite = Invite.by_participant(user, cached_invites=invites)[0]
            reply_html += f"\nКто пригласил: {invite.creator.real_name} {invite.creator.username}"
        except:
            logging.log(logging.INFO, "--")

        markup_buttons = [
            [
                InlineKeyboardButton(text='Approve', callback_data="Approve:" + str(user.id)),
                InlineKeyboardButton(text='Reject', callback_data="Reject:" + str(user.id))
            ]
        ]
        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(markup_buttons))
        i += 1

    update.message.reply_html(
        "Всего ждут: " + str(len(users)), reply_markup=ReplyKeyboardMarkup(
            admin_keyboard(),
            resize_keyboard=True,
            one_time_keyboard=False), disable_web_page_preview=True, )
    return None


# User functions:

def add_more_invite(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)

    invites = Invite.by_creator(user)
    max_invites = int(Settings.max_invites())

    if len(invites) >= max_invites:
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text="Больше приглашений на одного участника выдать не получится :(")
        return None

    invite = Invite.create_new(user)
    update.callback_query.answer()
    update.callback_query.delete_message()
    context.bot.send_message(
        user.id,
        text=invite.pretty_html(),
        disable_web_page_preview=True, parse_mode=ParseMode.HTML)

    if len(invites) + 1 >= max_invites:
        context.bot.send_message(user.id,
                                 text=f"Больше приглашений на одного участника выдать не получится :(",
                                 disable_web_page_preview=True)
    else:
        markup_buttons = [
            [InlineKeyboardButton(text="Выдайте мне еще", callback_data=f"{CALLBACK_MORE_INVITES}")]]

        context.bot.send_message(user.id,
                                 text=f"Всего у тебя {len(invites) + 1} приглашения(ий)",
                                 disable_web_page_preview=True,
                                 reply_markup=InlineKeyboardMarkup(markup_buttons))


# Admin functions:

def admin_gift(update: Update, context: CallbackContext) -> None:
    admin_user = User.get(update.effective_user.id)
    if not admin_user or not admin_user.admin:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text="Ну-ка! Куда полез!?", parse_mode=ParseMode.HTML)
        return None

    string_user_id = update.callback_query.data.split(':')[1]
    user = User.get(int(string_user_id))

    if not (user.status in [User.STATUS_APPROVED]):
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=f"Статус пользователя {user.status} не позволяет выдать билет.",
                                                parse_mode=ParseMode.HTML)
        return None

    if user.purchase_id:
        reply_text = emojize(":man_detective:",
                             use_aliases=True) + " Возможно другой админ уже выдал билет " + user.pretty_html()
    else:
        purchase = Purchase.create_new_gift(admin_user)
        purchase.user = user
        purchase.save()

        purchase.create_image()

        user.status = User.STATUS_READY
        user.purchase_id = purchase.id
        user.save()

        update_conversation(str(CONVERSATION_NAME), user, READY_DASHBOARD)

        context.bot.send_message(user.id, state_texts[READY_DASHBOARD], reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user),
            resize_keyboard=True,
            one_time_keyboard=True),
                                 disable_web_page_preview=True,
                                 parse_mode=ParseMode.HTML)

        reply_text = emojize(":admission_tickets:", use_aliases=True) + " БИЛЕТ ВЫДАН " + user.pretty_html()

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=reply_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    return None


def admin_approve(update: Update, context: CallbackContext) -> None:
    admin_user = User.get(update.effective_user.id)
    if not admin_user or not admin_user.admin:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text="Ну-ка! Куда полез!?", parse_mode=ParseMode.HTML)
        return None

    string_user_id = update.callback_query.data.split(':')[1]
    user = User.get(int(string_user_id))

    if not (user.status in [User.STATUS_IN_WAITING_LIST_CHECKED, User.STATUS_BY_REFERRAL_CHECKED]):
        reply_text = emojize(":man_detective:",
                             use_aliases=True) + " Возможно другой админ уже заапрувил " + user.pretty_html()
    else:
        user.status = User.STATUS_APPROVED
        user.save()
        Invite.generate_invites(user)

        update_conversation(str(CONVERSATION_NAME), user, WAITING_PAYMENT)

        # notify user about approval
        user_reply = state_texts[WAITING_PAYMENT]
        context.bot.send_message(chat_id=user.id,
                                 reply_markup=ReplyKeyboardMarkup(
                                     get_default_keyboard_bottom(user), resize_keyboard=True, one_time_keyboard=True),
                                 disable_web_page_preview=True, text=user_reply, parse_mode=ParseMode.HTML)

        reply_text = emojize(":check_mark_button:", use_aliases=True) + " APPROVED " + user.pretty_html()

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=reply_text, parse_mode=ParseMode.HTML)

    return None


def admin_reject(update: Update, context: CallbackContext) -> None:
    admin_user = User.get(update.effective_user.id)
    if not admin_user or not admin_user.admin:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text="Ну-ка! Куда полез!?", parse_mode=ParseMode.HTML)
        return None

    string_user_id = update.callback_query.data.split(':')[1]
    user = User.get(int(string_user_id))

    if not (user.status in [User.STATUS_IN_WAITING_LIST_CHECKED, User.STATUS_BY_REFERRAL_CHECKED]):
        reply_text = emojize(":face_with_symbols_on_mouth:",
                             use_aliases=True) + " Возможно другой админ уже заапрувил или отклонил " + user.pretty_html()
    else:
        user.status = User.STATUS_REJECTED
        user.save()

        reply_text = emojize(":face_with_symbols_on_mouth:", use_aliases=True) + " REJECTED " + user.pretty_html()

        # notify user about approval
        user_reply = "Сори, но тебя реджектнули! Администрация феста в праве отклонять заявки без указания причины," \
                     " таковы правила.\nЧто теперь? Если ты считаешь это несправедливым, то напиши нам " \
                     "(контакты в разделе Инфы) и обсудим."
        context.bot.send_message(chat_id=user.id,
                                 reply_markup=ReplyKeyboardMarkup(
                                     get_default_keyboard_bottom(user, None, False), resize_keyboard=True),
                                 disable_web_page_preview=True, text=user_reply, parse_mode=ParseMode.HTML)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=reply_text, parse_mode=ParseMode.HTML)

    return None


# Conversations

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('start', action_start),
        CallbackQueryHandler(accept_invite, pattern=r'^(Accept.*$)'),
        CallbackQueryHandler(decline_invite, pattern=r'^(Decline.*$)'),
    ],
    states={
        STARTING: [
            MessageHandler(Filters.regex(f'^{str(BUTTON_JOIN_WAITING_LIST)}'), action_join_waiting_list),
        ],
        WAITING_NAME: [
            MessageHandler(
                Filters.text, action_set_name
            ),
            CallbackQueryHandler(action_set_name_callback, pattern=rf'^{CALLBACK_BUTTON_BACK}:.*$'),
        ],
        WAITING_INSTA: [
            MessageHandler(
                Filters.text, action_set_insta,
            )
        ],
        WAITING_VK: [
            MessageHandler(
                Filters.text, action_set_vk,
            )
        ],
        WAITING_APPROVE: [
            MessageHandler(Filters.regex(f'^{str(BUTTON_I_HAVE_CODE)}'), action_wait_code)
        ],
        WAITING_FOR_MANUAL_CODE: [
            MessageHandler(Filters.regex(f'^{BUTTON_BACK}'), action_back_from_manual_code),
            MessageHandler(Filters.text, action_enter_code),
        ],
        WAITING_PAYMENT: [
            MessageHandler(Filters.regex(f'^{BUTTON_INVITES}$'), show_invites),
            MessageHandler(Filters.regex(f'^{BUTTON_TICKETS}$'), show_tickets),
            MessageHandler(Filters.successful_payment, action_successful_payment_callback),
            CallbackQueryHandler(add_more_invite, pattern=rf'^{str(CALLBACK_MORE_INVITES)}$'),
        ],
        READY_DASHBOARD: [
            MessageHandler(Filters.regex(f'^{BUTTON_INVITES}$'), show_invites),
            MessageHandler(Filters.regex(f'^{BUTTON_MY_TICKET}$'), show_my_ticket),
            CallbackQueryHandler(add_more_invite, pattern=rf'^{str(CALLBACK_MORE_INVITES)}$'),
        ]
    },
    fallbacks=[],
    name=str(CONVERSATION_NAME),
    persistent=True,
    per_chat=False,
    per_message=False
)


def update_conversation(conversation_name: str, user: User, state: int):
    store.update_conversation(conversation_name, tuple([user.id]), state)
    refresh_conversations(conv_handler)


def refresh_conversations(handler: ConversationHandler):
    handler.conversations = store.get_conversations(str(CONVERSATION_NAME))


# Main endpoint

def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater("1729903490:AAERypw3yDXPCK4ikqKsc8um7NOHBXj5gBc", persistence=store)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Pre-checkout handler to final check
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    dispatcher.add_handler(MessageHandler(Filters.regex('^Status$'), show_status))
    dispatcher.add_handler(MessageHandler(Filters.regex('^Info'), show_info))

    conv_admin_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Admin$'), admin_action_dashboard)],
        states={
            ADMIN_DASHBOARD: [
                MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_ALL)}'), admin_show_list),
                MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_CHECK_NEEDED)}$'),
                               admin_show_approval_list, pass_user_data=True),
                MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_WAITING_LIST)}$'),
                               admin_show_approval_list, pass_user_data=True),
                MessageHandler(Filters.regex('^Back'), admin_action_back),
                CallbackQueryHandler(admin_gift, pattern=rf'^({str(CALLBACK_BUTTON_GIFT_TICKET)}.*$)'),
                CallbackQueryHandler(admin_approve, pattern=r'^(Approve.*$)'),
                CallbackQueryHandler(admin_reject, pattern=r'^(Reject.*$)'),
            ]
        },
        fallbacks=[MessageHandler(Filters.regex('^Done$'), show_status)],
        name="admin_conversation",
        persistent=True,
    )
    dispatcher.add_handler(conv_admin_handler)
    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(MessageHandler(Filters.text, show_state_text))
    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
