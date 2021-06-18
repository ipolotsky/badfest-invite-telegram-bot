#!/usr/bin/env python
# pylint: disable=C0116

import logging
import time
from datetime import datetime

from emoji import emojize
from typing import Optional
from telegram import ReplyKeyboardMarkup, Update, ParseMode, TelegramError, ReplyKeyboardRemove, LabeledPrice
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from models.art_requests import ArtRequest
from models.merch_purchases import MerchPurchase
from models.merchs import Merch
from models.ticket_purchases import TicketPurchase
from settings import Settings
from models.tickets import Ticket
from models.users import User
from models.invites import Invite
from handlers.error_handler import error_handler
from persistence.firebase_persistence import FirebasePersistence
from utils import helper
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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

BULK_SEND_SLEEP_STEP = 25

CONVERSATION_NAME = "user_states_conversation"
CONVERSATION_ADMIN_NAME = "admin_states_conversation"

store = FirebasePersistence()

# Conversation states
STARTING, WAITING_START_MANUAL_CODE, WAITING_NAME, WAITING_INSTA, \
WAITING_VK, WAITING_APPROVE, WAITING_PAYMENT, \
WAITING_FOR_MANUAL_CODE, READY_DASHBOARD, ADMIN_DASHBOARD, ADMIN_BROADCAST = range(1, 12)

state_texts = dict([
    (STARTING, 'Привет! Это бот BadFest 2021. Вводи код от друга либо нажимай на кнопку "Хочу на фест"!'),
    (WAITING_START_MANUAL_CODE, 'Отлично! Вводи его скорее!'),
    (WAITING_NAME, 'Такс, давай знакомиться! Пара вопросов, чтобы мы узнали, кто ты такой(ая). \nКак тебя зовут?'),
    (WAITING_INSTA, 'Скинь, плиз, ссылку на свою инсту'),
    (WAITING_VK, 'А теперь ссылку на свой vk'),
    (WAITING_APPROVE, 'Ну все, теперь жди - как только модераторы тебя подтвердят, тебе прилетят реферальные '
                      'ссылки, чтобы пригласить друзей, а также ты сможешь оплатить билет прямо тут в боте.'),
    (WAITING_PAYMENT, "Хей! Ты принят! Теперь ты можешь покупать билет, а также у тебя есть две ссылки,"
                      " по которым ты можешь пригласить друзей.\n"
                      "Приглашай только тех, за кого можешь поручиться =)" \
                      "\nИ не забывай про билеты - они будут дорожать каждую неделю." \
                      "\n\nИспользуй кнопки бота для перехода к билетам и ссылкам для друзей."),
    (WAITING_FOR_MANUAL_CODE, "Супер! Введи код, плиз:"),
    (READY_DASHBOARD, "Ура! У тебя есть билет на BadFest 2021!\n"
                      "Полезные ссылки:\n"
                      " - <a href='https://t.me/badfest'>Канал с новостями фестиваля</a>\n"
                      " - <a href='https://t.me/joinchat/S6eWQnc4LxbJs_bU'>Чат участников фестиваля</a>\n"
     ),
])

# Bot buttons

BUTTON_JOIN_WAITING_LIST = "Хочу на Фест!"
BUTTON_START_MANUAL_CODE = "Ввести код"
BUTTON_ADMIN_CHECK_NEEDED = "Надо проверить"
BUTTON_ADMIN_STATS = "Статистика"
BUTTON_ADMIN_MERCH = "Весь мерч"
BUTTON_ADMIN_KARINA = "Карина-кнопка"
BUTTON_ADMIN_WAITING_LIST = "В списке ожидания"
BUTTON_ADMIN_ALL = "Все пользователи"
BUTTON_ADMIN_BROADCAST = "Broadcast"
BUTTON_ADMIN_ART_REQUESTS = "Карина"
BUTTON_I_HAVE_CODE = "У меня есть код"
BUTTON_BACK = "Назад"
BUTTON_INVITES = "Приглашения"
BUTTON_TICKETS = "Билеты"
BUTTON_MY_TICKET = "Мой билет"
BUTTON_INFO = "Про BadFest2021"
BUTTON_STATUS = "Как у меня дела"
BUTTON_MERCH = "Мерч"
BUTTON_REQUEST_FOR_ART = "Хочу делать арт-объект!"
CALLBACK_ACCEPT_INVITE = "Accept"
CALLBACK_DECLINE_INVITE = "Decline"
CALLBACK_MORE_INVITES = "Moreinvites"
CALLBACK_ART_REQUEST = "ArtRequest"
CALLBACK_BUTTON_REALNAME = "Realname"
CALLBACK_BUTTON_GIFT_TICKET = "Gift"


# Telegram bot keyboards functions

def admin_keyboard(buttons=None):
    if buttons is None:
        buttons = []
    buttons.append([str(BUTTON_ADMIN_BROADCAST), str(BUTTON_ADMIN_STATS)])
    buttons.append([str(BUTTON_ADMIN_CHECK_NEEDED), str(BUTTON_ADMIN_WAITING_LIST), str(BUTTON_ADMIN_ALL)])
    buttons.append([str(BUTTON_ADMIN_ART_REQUESTS), str(BUTTON_ADMIN_MERCH), str(BUTTON_BACK)])
    return buttons


def get_default_keyboard_bottom(user: User, buttons=None, is_admin_in_convs=True):
    convs = store.get_conversations(str(CONVERSATION_NAME))
    state = convs.get(tuple([user.id]))

    if buttons is None:
        buttons = []

    if state in [WAITING_APPROVE] and user.status == User.STATUS_IN_WAITING_LIST_CHECKED:
        buttons.append([str(BUTTON_I_HAVE_CODE)])

    if user.status == User.STATUS_WELCOME:
        buttons.append([str(BUTTON_START_MANUAL_CODE), str(BUTTON_JOIN_WAITING_LIST)])

    if state in [WAITING_PAYMENT] and user.status == User.STATUS_APPROVED:
        buttons.append([str(BUTTON_INVITES), str(BUTTON_TICKETS)])

    if state in [READY_DASHBOARD]:
        buttons.append([str(BUTTON_INVITES), str(BUTTON_MY_TICKET), str(BUTTON_REQUEST_FOR_ART)])

    key_board = [str(BUTTON_STATUS), str(BUTTON_INFO)]
    if Settings.enable_merch():
        key_board.append(str(BUTTON_MERCH))

    if user.admin:
        in_admin_convs = store.get_conversations(str(CONVERSATION_ADMIN_NAME)).get(tuple([user.id]))
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
            "Нет такого кода реферального. Ты можешь пользоваться ботом и нажать кнопку Хочу на Фест! и ждать, "
            "но это такое...\n"
            "Лучше проверь ссылку от друга на актуальность и перейди по ней заново ;)",
        )
        return False

    if invite.activated():
        update.message.reply_text(
            "Код по этой ссылке уже активирован. Если ты только-только пришел, напиши боту что-нибудь."
            "Если уже зареганый - то смотри, что написано выше.\n"
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
        reply_text = f"Хей! Это персональное тебе приглашение на BadFest 2021 от {invite.creator.real_name}.\n"
        update.message.reply_text(reply_text,
                                  reply_markup=ReplyKeyboardMarkup([[str(BUTTON_MERCH)] if Settings.enable_merch() else []],
                                                                   resize_keyboard=True,
                                                                   one_time_keyboard=True),
                                  disable_web_page_preview=True)

        markup_buttons = [[
            InlineKeyboardButton(text="Принять", callback_data=f"{str(CALLBACK_ACCEPT_INVITE)}:{code}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"{str(CALLBACK_DECLINE_INVITE)}:{code}"),
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


def action_start_inside(update: Update, context: CallbackContext):
    if len(context.args) and context.args[0]:
        code = context.args[0]
        check = check_code_on_start(update, code)
        if not check:
            return None

        user = User.get(update.effective_user.id)
        if not (user.status in [User.STATUS_IN_WAITING_LIST_CHECKED,
                               User.STATUS_IN_WAITING_LIST, User.STATUS_WELCOME]):
            return None

        if user.status == User.STATUS_WELCOME:
            update_conversation(str(CONVERSATION_NAME), user, WAITING_NAME)

        if user.status == User.STATUS_IN_WAITING_LIST_CHECKED:
            user.status = User.STATUS_BY_REFERRAL_CHECKED

        if user.status in [User.STATUS_IN_WAITING_LIST, User.STATUS_WELCOME]:
            user.status = User.STATUS_BY_REFERRAL

        user.save()

        invite = Invite.get(code)
        invite.participant = user
        invite.save()
        context.bot.send_message(chat_id=invite.creator.id,
                                 text=f"Ееееее! {user.full_name()} {user.username} принял(а) твое приглашение! :)")

        context.bot.send_message(user.id, "Шик! Код успешно применен!")
        show_state_text(update, context)

    update.message.reply_text("Ты уже зареган. Есть думаешь, что что-то идет не так, то напиши в поддержку @ipolotsky")


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

    update.callback_query.answer()
    update.callback_query.delete_message()
    context.bot.send_message(user.id, "Отлично! Держи сразу полезные ссылки:\n"
                                      " - <a href='https://t.me/badfest'>Канал с новостями фестиваля</a>\n"
                                      " - <a href='https://t.me/joinchat/S6eWQnc4LxbJs_bU'>Чат участников фестиваля</a>",
                             reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)

    markup_buttons = []
    if user.first_name or user.last_name:
        markup_buttons = [
            [InlineKeyboardButton(text=user.full_name(),
                                  callback_data=f"{CALLBACK_BUTTON_REALNAME}:{user.full_name()}")]]

    context.bot.send_message(
        chat_id=user.id,
        text=state_texts[WAITING_NAME],
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(markup_buttons))

    return WAITING_NAME


def decline_invite(update: Update, context: CallbackContext) -> Optional[int]:
    code = update.callback_query.data.split(':')[1]
    invite = Invite.get(code)
    context.bot.send_message(chat_id=invite.creator.id, text=f"Штош. Твое приглашение ({code}) не приняли :(")

    update.callback_query.answer()
    update.callback_query.delete_message()

    context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Штош. Если передумаешь, можешь заново пройти по ссылке"
             " либо нажать кнопку Хочу на Фест и ждать. Для этого напиши что-нибудь сюда.",
        disable_web_page_preview=True)

    return None


def action_enter_waiting_start_code(update: Update, context: CallbackContext):
    update.message.reply_text(
        state_texts[WAITING_START_MANUAL_CODE], reply_markup=ReplyKeyboardMarkup(
            [[str(BUTTON_BACK)]], resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)

    return WAITING_START_MANUAL_CODE


def action_enter_start_manual_code(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    code = update.message.text.strip().replace('/', '').split(' ')
    try:
        invite = Invite.get(code[0])
    except TelegramError:
        try:
            invite = Invite.get(code[1])
        except:
            update.message.reply_text("Нет такого кода реферального", reply_markup=ReplyKeyboardMarkup(
                [[str(BUTTON_BACK)]], resize_keyboard=True,
                one_time_keyboard=True), disable_web_page_preview=True)
            return None

    if invite.activated():
        update.message.reply_text("Этот код уже активирован - попроси у друга новый", reply_markup=ReplyKeyboardMarkup(
            [[str(BUTTON_BACK)]], resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)
        return None

    user.status = User.STATUS_BY_REFERRAL
    user.save()

    invite.participant = user
    invite.save()

    context.bot.send_message(chat_id=invite.creator.id,
                             text=f"Ееееее! {user.full_name()} {user.username} принял(а) твое приглашение! :)")

    update.message.reply_text(f"Шик! Код успешно применен!",
                              reply_markup=ReplyKeyboardRemove(),
                              disable_web_page_preview=True)

    markup_buttons = []
    if user.first_name or user.last_name:
        markup_buttons = [
            [InlineKeyboardButton(text=user.full_name(),
                                  callback_data=f"{CALLBACK_BUTTON_REALNAME}:{user.full_name()}")]]

    update.message.reply_text(
        text=state_texts[WAITING_NAME],
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(markup_buttons))

    return WAITING_NAME


def action_back_from_start_manual_code(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    update.message.reply_text(
        "Код можно ввести сейчас, а можно и потом (если нажата кнопка Хочу на Фест!)", reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)

    return STARTING


def action_join_waiting_list(update: Update, context: CallbackContext) -> Optional[int]:
    user = User.get(update.effective_user.id)
    if user.status != User.STATUS_WELCOME:
        update.message.reply_text(
            'Чет у тебя не тот статус, чтобы в списке ожидания быть'
        )
        return None

    user.status = User.STATUS_IN_WAITING_LIST
    user.save()

    update.message.reply_text("Отлично! Держи сразу полезные ссылки:\n"
                              " - <a href='https://t.me/badfest'>Канал с новостями фестиваля</a>\n"
                              " - <a href='https://t.me/joinchat/S6eWQnc4LxbJs_bU'>Чат участников фестиваля</a>",
                              reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.HTML)

    markup_buttons = []
    if user.first_name or user.last_name:
        markup_buttons = [
            [InlineKeyboardButton(text=user.full_name(),
                                  callback_data=f"{CALLBACK_BUTTON_REALNAME}:{user.full_name()}")]]

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
        f"Приветы, {user.real_name}! Сначала скинь, как тебя найти в инсте (имя профиля или ссылка, "
        f"например, https://www.instagram.com/badfestbad)\n"
        f"Не забудь проверить, что у тебя открытый профиль!"
    )
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True)

    return WAITING_INSTA


def action_set_name_callback(update: Update, context: CallbackContext) -> int:
    user = User.get(update.effective_user.id)
    real_name = update.callback_query.data.split(':')[1]
    user.real_name = real_name.strip()
    user.save()

    reply_text = (
        f"Приветы, {user.real_name}! Сначала скинь, как тебя найти в инсте (имя профиля или ссылка, "
        f"например, https://www.instagram.com/badfestbad)\n"
        f"Не забудь проверить, что у тебя открытый профиль!"
    )

    update.callback_query.answer()
    update.callback_query.delete_message()

    context.bot.send_message(chat_id=user.id, text=reply_text, disable_web_page_preview=True)

    return WAITING_INSTA


def action_set_insta(update: Update, context: CallbackContext) -> Optional[int]:
    user = User.get(update.effective_user.id)
    text = update.message.text.strip()

    insta_link = helper.get_insta(text)
    if not insta_link:
        replay_text = f"Хах, это не инста! Скинь, как тебя найти в инсте (имя профиля или ссылка, " \
                      f"например, https://www.instagram.com/badfestbad)\n" \
                      f"Не забудь проверить, что у тебя открытый профиль!"
        update.message.reply_text(
            replay_text, reply_markup=ReplyKeyboardMarkup(
                get_default_keyboard_bottom(user),
                resize_keyboard=True, one_time_keyboard=True), disable_web_page_preview=True, )
        return None

    user.insta = insta_link
    user.save()

    reply_text = "Супер! Еще чуть-чуть. Теперь скинь, как тебя найти в VK (имя профиля или ссылка, " \
                 f"например, https://vk.com/badfest/)\n" \
                 f"Не забудь проверить, что у тебя открытый профиль!"
    update.message.reply_text(
        reply_text, reply_markup=ReplyKeyboardMarkup(
            get_default_keyboard_bottom(user), resize_keyboard=True,
            one_time_keyboard=True), disable_web_page_preview=True, )

    return WAITING_VK


def action_set_vk(update: Update, context: CallbackContext) -> Optional[int]:
    user = User.get(update.effective_user.id)
    text = update.message.text.strip()

    vk_link = helper.get_vk(text)
    if not vk_link:
        replay_text = "Хах, это не VK! Cкинь, как тебя найти в VK (имя профиля или ссылка, " \
                 f"например, https://vk.com/badfest/)\n" \
                 f"Не забудь проверить, что у тебя открытый профиль!"
        update.message.reply_text(
            replay_text, reply_markup=ReplyKeyboardMarkup(
                get_default_keyboard_bottom(user),
                resize_keyboard=True, one_time_keyboard=True), disable_web_page_preview=True, )
        return None

    user.vk = vk_link

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


def action_request_for_art(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    try:
        art_request = ArtRequest.by_creator(user)[0]
        update.message.reply_text(
            f"Ты уже подал(а) заявку на арт-объект {art_request.created}", disable_web_page_preview=True)
        return None
    except:
        pass

    reply_text = "<b>В этом году мы хотим делать творческую выставку. Принять участие в ней может кто угодно!</b>\n\n" \
                 "Объекты могут быть полезными, как арт-толчок или кабинка для уединения, так и просто красивыми, как статуя Давида, — все зависит от твоей фантазии!\n\n" \
                 "<b>Чтобы добавить мотивации на старте</b>, мы решили наградить самый творческий коллектив грантом на реализацию. Принимаем заявки до 21:00 екб 22 июня, а 23 июня объявим тех, кто выиграл деньги на свой арт-объект\n\n" \
                 "<b>Чтобы добавить мотивации на финише</b>, на фесте будет конкурс на самый клёвый арт-объект. Компетентное жюри выберет самую стильную/всратую/невероятную фигуру и авторы получат фирменный бэд-мерч!\n\n" \
                 "Короче, тема классная. Собирай команду и регистрируйся"
    markup_buttons = [
        [InlineKeyboardButton(text="Подать заявку на арт-объект", callback_data=f"{CALLBACK_ART_REQUEST}:{user.id}")]]

    update.message.reply_html(
        text=reply_text,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(markup_buttons))


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
    code = update.message.text.strip().replace('/', '').split(' ')
    try:
        invite = Invite.get(code[0])
    except:
        try:
            invite = Invite.get(code[1])
        except:
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

    invite.participant = user
    invite.save()

    context.bot.send_message(chat_id=invite.creator.id,
                             text=f"Ееееее! {user.full_name()} {user.username} принял(а) твое приглашение! :)")

    update.message.reply_text("Шик! Код успешно применен! Жди проверку модератора.", reply_markup=ReplyKeyboardMarkup(
        get_default_keyboard_bottom(user), resize_keyboard=True,
        one_time_keyboard=True), disable_web_page_preview=True)

    return WAITING_APPROVE


def action_successful_payment_callback(update: Update, context: CallbackContext) -> None:
    payment = update.message.successful_payment

    try:
        Ticket.get(payment.invoice_payload)
        return process_successful_ticket(update, context)
    except:
        try:
            Merch.get(payment.invoice_payload)
            return process_successful_merch(update, context)
        except:
            logging.exception("Failed to pay ticket")
            raise TelegramError(f"Пришла оплата на хер пойми что: {str(payment)}")


def process_successful_ticket(update: Update, context: CallbackContext):
    payment = update.message.successful_payment
    user = User.get(update.effective_user.id)
    ticket = Ticket.get(payment.invoice_payload)
    purchase = TicketPurchase.create_new(update.message.successful_payment.provider_payment_charge_id)
    purchase.currency = payment.currency
    purchase.total_amount = payment.total_amount
    purchase.set_ticket_info(ticket)
    purchase.user = user
    purchase.phone_number = helper.safe_list_get(payment.order_info, "phone_number")
    purchase.email = helper.safe_list_get(payment.order_info, "email")
    purchase.customer_name = helper.safe_list_get(payment.order_info, "name")
    purchase.telegram_payment_charge_id = payment.telegram_payment_charge_id
    purchase.provider_payment_charge_id = payment.provider_payment_charge_id
    purchase.save()

    purchase.create_image()
    ticket.increase_price()

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

    for admin in User.admins():
        message = emojize(":money_bag:", use_aliases=True) + f" {user.real_name} ({user.username})" \
                                                             f" купил(а) билет '{purchase.ticket_name}' за {purchase.total_amount / 100} р."
        context.bot.send_message(chat_id=admin.id, text=message)

    return READY_DASHBOARD


def process_successful_merch(update: Update, context: CallbackContext) -> None:
    payment = update.message.successful_payment

    purchase = MerchPurchase.create_new(update.message.successful_payment.provider_payment_charge_id)
    purchase.currency = payment.currency
    purchase.total_amount = payment.total_amount
    purchase.set_merch_info(Merch.get(payment.invoice_payload))
    purchase.user_id = update.effective_user.id
    purchase.phone_number = helper.safe_list_get(payment.order_info, "phone_number")
    purchase.email = helper.safe_list_get(payment.order_info, "email")
    purchase.customer_name = helper.safe_list_get(payment.order_info, "name")
    purchase.telegram_payment_charge_id = payment.telegram_payment_charge_id
    purchase.provider_payment_charge_id = payment.provider_payment_charge_id
    purchase.save()

    reply_html = purchase.pretty_html()
    context.bot.send_message(
        update.effective_user.id,
        text=reply_html,
        disable_web_page_preview=True)

    for admin in User.admins():
        message = emojize(":fire:", use_aliases=True) + \
                  f"  <a href='tg://user?id={purchase.user_id}'>{purchase.customer_name}</a>" \
                  f" купил(а) мерч '{purchase.merch_name}' за {purchase.total_amount / 100} р."
        context.bot.send_message(chat_id=admin.id, text=message, parse_mode=ParseMode.HTML)


# User show data functions:

def show_info(update: Update, context: CallbackContext):
    update.message.reply_html(
        "<b>BADFEST 2021</b>\n\n"
        "Время быть плохим!\n"
        "Ежегодный фестиваль музыки, алкоголя, веселья, творчества с твоим участием в главной роли. Ничего особо не обещаем, будет плохо, обязательно приезжай. Ты пожалеешь, но тебе понравится.\n"
        "Увидимся скоро!\n\n"
        "BadFest в соцсетях: "
        "<a href='https://instagram.com/badfestbad'>Instagram</a> / "
        "<a href='https://t.me/badfest'>Telegram</a> / "
        "<a href='https://vk.com/badfest'>VK</a>", disable_web_page_preview=True, disable_notification=True)
    update.message.reply_html("<b>Что почитать перед тем как соглашаться на движ:</b>", disable_notification=True)
    update.message.reply_html("<a href='https://vk.com/@badfest-manifest'>Манифест BADFEST</a>", disable_notification=True)
    update.message.reply_html("<a href='https://vk.com/@badfest-fuck'>F.A.Q.</a>", disable_notification=True)
    update.message.reply_html(
        "Команда <a href='https://t.me/barbadbar'>BadBar</a> и друзья.\n", disable_web_page_preview=True)


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

    for purchase in TicketPurchase.by_user(user):
        reply_html = purchase.pretty_html()
        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True)
        try:
            with open(f'images/{purchase.id}.png', 'rb') as f:
                pass
        except:
            purchase.create_image()

        with open(f'images/{purchase.id}.png', 'rb') as f:
            context.bot.send_photo(user.id, photo=f, timeout=50)


def show_merch(update: Update, context: CallbackContext):
    index = 1
    update.message.reply_html(
        text="Выбирай мерч и покупай прямо тут в телеграме (да, так уже можно, начиная с апреля этого года)\n"
             "Продолжая покупку, ты соглашаешься с <a href='https://badbar.ru/policy'>"
             "политикой конфеденциальности</a> и <a href='https://vk.com/@badfest-manifest'>прочей лабудой</a>,"
             " которая нам, к сожалению, нужна:\n\n",
        disable_web_page_preview=True)

    for merch in Merch.by_type(Merch.ACTIVE_TYPE):
        payload = merch.id
        provider_token = Settings.provider_token()
        currency = "RUB"
        prices = [LabeledPrice(merch.id, merch.price * 100)]

        context.bot.send_invoice(
            chat_id=update.effective_user.id, title=emojize(":penguin:", use_aliases=True) + merch.id,
            description=merch.description, payload=payload, provider_token=provider_token,
            currency=currency, prices=prices,
            photo_url=merch.photo, photo_width=500, photo_height=500, need_name=True,
            need_email=True, need_phone_number=True, max_tip_amount=2000000,
            suggested_tip_amounts=[int(merch.price * 10), int(merch.price * 100), int(merch.price * 300)]
        )

        index += 1

    merchs = MerchPurchase.by_user_id(update.effective_user.id)
    if len(merchs) > 0:
        update.message.reply_html(
            text="А это то, что ты уже купил(а):\n\n ",
            disable_web_page_preview=True)

        for merch in merchs:
            reply_html = merch.pretty_html()
            update.message.reply_html(
                text=reply_html,
                disable_web_page_preview=True)


def show_tickets(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if user.status != User.STATUS_APPROVED:
        update.message.reply_text("Рано еще!")
        return None

    index = 1
    update.message.reply_html(
        text="Выбирай билет и покупай прямо тут в телеграме (да, так уже можно, начиная с апреля этого года)\n"
             "Продолжая покупку, ты соглашаешься с <a href='https://badbar.ru/policy'>"
             "политикой конфеденциальности</a> и <a href='https://vk.com/@badfest-manifest'>прочей лабудой</a>,"
             " которая нам, к сожалению, нужна:\n\n",
        disable_web_page_preview=True)

    for ticket in Ticket.by_type(Ticket.PAID_TYPE):
        payload = ticket.id
        provider_token = Settings.provider_token()
        currency = "RUB"
        prices = [LabeledPrice(ticket.id, ticket.price * 100)]

        context.bot.send_invoice(
            chat_id=user.id, title=emojize(":admission_tickets:", use_aliases=True) + ticket.id,
            description=ticket.description, payload=payload, provider_token=provider_token,
            currency=currency, prices=prices,
            photo_url=ticket.photo, photo_width=500, photo_height=500, need_name=True,
            need_email=True, need_phone_number=True, max_tip_amount=2000000,
            suggested_tip_amounts=[int(ticket.price * 10), int(ticket.price * 100), int(ticket.price * 300)]
        )

        index += 1


def precheckout_callback(update: Update, _: CallbackContext) -> None:
    query = update.pre_checkout_query

    if not query.invoice_payload:
        query.answer(ok=False, error_message=f"Payload какой-то не такой... пустой, нет его")
        return None

    ticket = None
    merch = None
    error_text = ""

    try:
        ticket = Ticket.get(query.invoice_payload)
    except:
        # query.answer(ok=False, error_message=f"Нет билета с таким id:{query.invoice_payload}")
        error_text = f"Нет билета с таким id:{query.invoice_payload}"

    try:
        merch = Merch.get(query.invoice_payload)
    except:
        # query.answer(ok=False, error_message=f"Нет билета с таким id:{query.invoice_payload}")
        error_text = f"Нет мерча с таким id:{query.invoice_payload}"

    if (not ticket) and (not merch):
        query.answer(ok=False, error_message=error_text)
        return None

    if ticket:
        try:
            user = User.get(query.from_user.id)

            if user.status == User.STATUS_READY:
                query.answer(ok=False, error_message=f"Ты уже купил(а) билет на себя. "
                                                     f"Если просто хочешь донатить нам - напиши ограм, "
                                                     f"мы будем счастливы!")
                return None

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
            state_texts[state] + f"\nИспользуй кнопочки снизу, если что-то хочешь.", reply_markup=ReplyKeyboardMarkup(
                get_default_keyboard_bottom(User.get(update.effective_user.id)),
                resize_keyboard=True,
                one_time_keyboard=True), disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text("Жамкни /start")

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


def admin_broadcast_set(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    text = update.message.text.strip()\
        .replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    try:
        store.broadcasts.child('current').set({
            "text": text
        })
        update.message.reply_html(
            f"Текст для отправки:\n\n{text}",
            reply_markup=ReplyKeyboardMarkup(admin_keyboard([[str(BUTTON_BACK)]]), resize_keyboard=True, one_time_keyboard=True),
            disable_web_page_preview=True)

        groups = User.group_by_status()
        buttons = [[InlineKeyboardButton(text=f"{User.status_to_buttons()[status]} ({len(groups[status])})", callback_data=status)] for status in groups]
        update.message.reply_text("Если все ок, выбери, кому отправить. Если нет - напиши еще раз нужный текст в ответ. Милорд!",
                                  reply_markup=InlineKeyboardMarkup(buttons))
    except:
        update.message.reply_text("Чет не то, проверь синтаксис",
                                  reply_markup=ReplyKeyboardMarkup(admin_keyboard([[str(BUTTON_BACK)]]), resize_keyboard=True,one_time_keyboard=True))
    finally:
        return None


def admin_action_broadcast(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    update.message.reply_text(
        'Милорд, напиши сообщение, можна юзать теги b и a разметку, потом посмотрим, как оно выглядит и отправим, если что.',
        reply_markup=ReplyKeyboardMarkup(admin_keyboard([[str(BUTTON_BACK)]]), resize_keyboard=True,
                                         one_time_keyboard=True), disable_web_page_preview=True)

    return ADMIN_BROADCAST


def admin_action_broadcast_back(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None
    update.message.reply_text(
        'Приходи в другой раз с готовым текстом!',
        reply_markup=ReplyKeyboardMarkup(admin_keyboard(), resize_keyboard=True,
                                         one_time_keyboard=True), disable_web_page_preview=True)
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

def admin_show_stats(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    update.message.reply_text("Статистика")
    update.message.reply_text("Пользователи: \n" + User.statistics())
    update.message.reply_text("Покупки: \n" + TicketPurchase.statistics())


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

            purchase = TicketPurchase.get(user.purchase_id)
            reply_html += f"\nБилет: {purchase.ticket_name} {purchase.total_amount / 100} р." \
                          f"\nВремя покупки: {purchase.created}"

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


def admin_show_art_requests(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    i = 1
    art_requests = ArtRequest.all()
    for a_request in art_requests:
        reply_html = a_request.pretty_html(i)
        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True)
        i += 1

    stats = f"Всего заявок: {str(len(art_requests))}"

    update.message.reply_html(
        stats, reply_markup=ReplyKeyboardMarkup(
            admin_keyboard(),
            resize_keyboard=True,
            one_time_keyboard=False), disable_web_page_preview=True)
    return None


def admin_show_merch_list(update: Update, context: CallbackContext):
    user = User.get(update.effective_user.id)
    if not user or not user.admin:
        update.message.reply_text("Ну-ка! Куда полез!?")
        return None

    i = 1
    total_amount = 0
    merchs = MerchPurchase.all()
    for merch in merchs:
        total_amount += merch.total_amount
        reply_html = merch.admin_pretty_html(i)
        update.message.reply_html(
            text=reply_html,
            disable_web_page_preview=True)
        i += 1

    stats = f"Всего мерча: {str(len(merchs))}\n" \
            f"Всего денег: {str(total_amount / 100)} р."

    update.message.reply_html(
        stats, reply_markup=ReplyKeyboardMarkup(
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
            pass

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

def art_request(update: Update, context: CallbackContext) -> None:
    string_user_id = update.callback_query.data.split(':')[1]
    user = User.get(int(string_user_id))

    ArtRequest.create_new(user)
    update.callback_query.answer()
    update.callback_query.delete_message()
    reply_text = "<b>Супер!</b> \n"\
                 "Что нужно сделать в ближайшее время:\n"\
                 "- Придумай название вашего творческого коллектива\n"\
                 "- Собери участников творческого коллектива\n"\
                 "- Придумай название арт-объекта и краткое описание, что это будет, из чего и для чего\n\n"\
                 "<b>Придумал? Отлично!</b> Напиши это всё нашему красивому куратору " \
                 "<a href='tg://user?id=211433130'>Карине Тиничевой</a>"
    "\n\nТы восхитителен!"
    context.bot.send_message(user.id, reply_text, parse_mode=ParseMode.HTML)

    for admin in User.admins():
        message = emojize(":building_construction:", use_aliases=True) + f" {user.real_name} ({user.username})" \
                                                                         f" подал(a) заявку на арт-объект"
        context.bot.send_message(chat_id=admin.id, text=message)


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

def admin_send_broadcast(update: Update, context: CallbackContext):
    admin_user = User.get(update.effective_user.id)
    if not admin_user or not admin_user.admin:
        update.callback_query.answer()
        update.callback_query.edit_message_text(text="Ну-ка! Куда полез!?", parse_mode=ParseMode.HTML)
        return None

    update.callback_query.answer()
    update.callback_query.delete_message()
    status = update.callback_query.data.strip()

    text = store.broadcasts.child("current").get()['text']
    date = datetime.now().timestamp()
    users = User.by_status(status)

    context.bot.send_message(admin_user.id, f"Отправляю вот это: \n\n{text}\n\n"
                                            f"Сколько пользователей получат: {len(users)}\n\n"
                                            f"Ожидай, пока я не напишу, что все всем отправил!")
    bad_users = send_bulk(text, users, context)
    store.broadcasts.child("history")\
        .child(datetime.fromtimestamp(date).strftime('%Y-%m-%d %H:%M:%S')).set({
            "timestamp": date,
            "text": text,
            "for_whom": User.status_to_buttons()[status],
            "sender": admin_user.full_name(),
            "amount": len(users),
            "failed": len(bad_users),
        }
    )

    context.bot.send_message(admin_user.id, f"Терпение - золото (хуита, конечно). {len(users) - len(bad_users)} успешно отправилось!")
    if len(bad_users) > 0:
        bad_nicknames = [user.username for user in bad_users]
        context.bot.send_message(admin_user.id, f"Кроме этих пидорасов: {', '.join(bad_nicknames)}")


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
        purchase = TicketPurchase.create_new_gift(admin_user)
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
        user_reply = "Сори, но тебя реджектнули! Причин может быть тысячи, ведь мы знаем, что ты плохо вел себя в этом году. Или хорошо. Не важно!\nАдминистрация феста в праве отклонять заявки без указания причины," \
                     " таковы правила.\nЧто теперь? Если ты считаешь что произошла ошибка, попробуй чуть позже снова нажать кнопку Хочу на фест."
        context.bot.send_message(chat_id=user.id,
                                 reply_markup=ReplyKeyboardMarkup(
                                     get_default_keyboard_bottom(user, None, False), resize_keyboard=True),
                                 disable_web_page_preview=True, text=user_reply, parse_mode=ParseMode.HTML)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=reply_text, parse_mode=ParseMode.HTML)

    return None


def send_bulk(text: str, users: list[User], context: CallbackContext):
    index = 1
    bad_users = []
    for user in users:
        if index % BULK_SEND_SLEEP_STEP == 0:
            logging.log(logging.INFO, "sleeping for 2 sec")
            time.sleep(2)
        try:
            context.bot.send_message(user.id, text, parse_mode=ParseMode.HTML)
        except:
            bad_users.append(user)
        index = index + 1

    return bad_users


conv_admin_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.regex('^Admin$'), admin_action_dashboard)],
    states={
        ADMIN_DASHBOARD: [
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_ALL)}'), admin_show_list),
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_STATS)}'), admin_show_stats),
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_CHECK_NEEDED)}$'),
                           admin_show_approval_list, pass_user_data=True),
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_MERCH)}$'), admin_show_merch_list),
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_ART_REQUESTS)}$'), admin_show_art_requests),
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_WAITING_LIST)}$'),
                           admin_show_approval_list, pass_user_data=True),
            MessageHandler(Filters.regex(f'^{str(BUTTON_BACK)}$'), admin_action_back),
            MessageHandler(Filters.regex(f'^{str(BUTTON_ADMIN_BROADCAST)}$'), admin_action_broadcast),
            CallbackQueryHandler(admin_gift, pattern=rf'^({str(CALLBACK_BUTTON_GIFT_TICKET)}.*$)'),
            CallbackQueryHandler(admin_approve, pattern=r'^(Approve.*$)'),
            CallbackQueryHandler(admin_reject, pattern=r'^(Reject.*$)'),
        ],
        ADMIN_BROADCAST: [
            MessageHandler(Filters.regex(f'^{BUTTON_BACK}'), admin_action_broadcast_back),
            MessageHandler(Filters.text, admin_broadcast_set),
            CallbackQueryHandler(admin_send_broadcast),
        ]
    },
    fallbacks=[],
    name=str(CONVERSATION_ADMIN_NAME),
    persistent=True,
    per_chat=False,
    per_message=False
)
# Conversations


conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('start', action_start),
        CallbackQueryHandler(accept_invite, pattern=rf'^({str(CALLBACK_ACCEPT_INVITE)}.*$)'),
        CallbackQueryHandler(decline_invite, pattern=rf'^({str(CALLBACK_DECLINE_INVITE)}.*$)'),
    ],
    states={
        STARTING: [
            CommandHandler('start', action_start_inside),
            MessageHandler(Filters.regex(f'^{str(BUTTON_JOIN_WAITING_LIST)}'), action_join_waiting_list),
            MessageHandler(Filters.regex(f'^{str(BUTTON_START_MANUAL_CODE)}'), action_enter_waiting_start_code),
        ],
        WAITING_START_MANUAL_CODE: [
            MessageHandler(Filters.regex(f'^{BUTTON_BACK}'), action_back_from_start_manual_code),
            MessageHandler(Filters.text, action_enter_start_manual_code),
        ],
        WAITING_NAME: [
            CommandHandler('start', action_start_inside),
            MessageHandler(
                Filters.text, action_set_name
            ),
            CallbackQueryHandler(action_set_name_callback, pattern=rf'^{CALLBACK_BUTTON_REALNAME}:.*$'),
        ],
        WAITING_INSTA: [
            CommandHandler('start', action_start_inside),
            MessageHandler(
                Filters.text, action_set_insta,
            )
        ],
        WAITING_VK: [
            CommandHandler('start', action_start_inside),
            MessageHandler(
                Filters.text, action_set_vk,
            )
        ],
        WAITING_APPROVE: [
            CommandHandler('start', action_start_inside),
            MessageHandler(Filters.regex(f'^{str(BUTTON_I_HAVE_CODE)}'), action_wait_code)
        ],
        WAITING_FOR_MANUAL_CODE: [
            MessageHandler(Filters.regex(f'^{BUTTON_BACK}'), action_back_from_manual_code),
            MessageHandler(Filters.text, action_enter_code),
        ],
        WAITING_PAYMENT: [
            PreCheckoutQueryHandler(precheckout_callback),
            MessageHandler(Filters.successful_payment, action_successful_payment_callback),
            MessageHandler(Filters.regex(f'^{BUTTON_INVITES}$'), show_invites),
            MessageHandler(Filters.regex(f'^{BUTTON_TICKETS}$'), show_tickets),
            CallbackQueryHandler(add_more_invite, pattern=rf'^{str(CALLBACK_MORE_INVITES)}$'),
        ],
        READY_DASHBOARD: [
            MessageHandler(Filters.regex(f'^{BUTTON_INVITES}$'), show_invites),
            MessageHandler(Filters.regex(f'^{BUTTON_MY_TICKET}$'), show_my_ticket),
            MessageHandler(Filters.regex(f'^{BUTTON_REQUEST_FOR_ART}$'), action_request_for_art),
            CallbackQueryHandler(add_more_invite, pattern=rf'^{str(CALLBACK_MORE_INVITES)}$'),
            CallbackQueryHandler(art_request, pattern=rf'^({str(CALLBACK_ART_REQUEST)}.*$)'),
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
    updater = Updater(Settings.bot_token(), persistence=store)
    dispatcher = updater.dispatcher

    # Add handlers
    dispatcher.add_handler(MessageHandler(Filters.regex(f'^{str(BUTTON_STATUS)}$'), show_status))
    dispatcher.add_handler(MessageHandler(Filters.regex(f'^{str(BUTTON_INFO)}'), show_info))
    dispatcher.add_handler(MessageHandler(Filters.regex(f'^{BUTTON_MERCH}$'), show_merch))

    dispatcher.add_handler(conv_admin_handler)
    dispatcher.add_handler(conv_handler)

    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, action_successful_payment_callback))
    dispatcher.add_handler(MessageHandler(Filters.text, show_state_text))
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
