# -*- coding: utf-8 -*-
"""
Telegram QA Assistant Bot
========================

This script implements a single Telegram bot that combines functionality from two
separate bots: one that generates test payment card numbers and another that
creates files of arbitrary formats and sizes.  Instead of running two bots in
parallel, this unified bot presents a main menu on the ``/start`` command and
guides the user through the appropriate workflow depending on whether they want
to generate a credit card or a test file.

The bot uses the ``pyTelegramBotAPI`` library (imported as ``telebot``) for
interacting with Telegram and the ``Faker`` package for generating realistic
test card numbers.  To customise the bot for your own use you must replace
``TOKEN`` below with the API token provided by BotFather.

Usage
-----

Before running this script make sure you have installed its dependencies:

.. code-block:: bash

   pip install pyTelegramBotAPI faker

Then insert your bot token in the ``TOKEN`` variable and execute the script:

.. code-block:: bash

   python main.py

The bot will respond to the ``/start`` command by asking whether you want to
generate a card or a file.  It uses ``ReplyKeyboardMarkup`` to present
interactive buttons for choices throughout the conversation and automatically
handles returning to the main menu.
"""

from __future__ import annotations

import os
import time
from typing import Any

from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from faker import Faker

# Replace this with your BotFather token.  Without a valid token the bot will
# not be able to connect to Telegram.  Do not commit real tokens to version
# control or share them publicly.
TOKEN = os.environ.get('TELEGRAM_TOKEN', 'ВСТАВИТЬ_СВОЙ_ТОКЕН')

# Create a single bot instance for both card and file generation workflows.
bot = TeleBot(token=TOKEN, parse_mode='html')

# Instantiate Faker once; it will be reused for each credit card generation.
faker = Faker()

# Mapping from human-friendly button labels to Faker card type identifiers.
CARD_LABEL_TO_TYPE: dict[str, str] = {
    'VISA': 'visa',
    'Mastercard': 'mastercard',
    'Maestro': 'maestro',
    'JCB': 'jcb',
}

# Keyboard used when asking the user to pick a card type.
card_type_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
card_type_keyboard.row(
    types.KeyboardButton('VISA'),
    types.KeyboardButton('Mastercard'),
)
card_type_keyboard.row(
    types.KeyboardButton('Maestro'),
    types.KeyboardButton('JCB'),
)

# List of file extensions that can be generated.  Feel free to add or remove
# formats as needed; the buttons will update automatically.
FORMATS: list[str] = [
    '.jpg', '.png', '.svg', '.gif', '.ico', '.mp4', '.avi', '.webm',
    '.doc', '.docx', '.xls', '.xlsx', '.txt', '.pdf', '.css', '.html',
    '.js', '.json', '.zip', '.rar',
]

# NOTE: The main menu is now presented as an inline keyboard (see qa_start).
# If you prefer a reply keyboard instead, you can revert to using
# ReplyKeyboardMarkup and assign it to ``main_menu_keyboard`` as before.
main_menu_keyboard = None


@bot.message_handler(commands=['start'])
def qa_start(message: types.Message) -> None:
    """
    Entry point for the bot.  Greets the user and presents the main menu.

    This handler responds to the ``/start`` command by sending a welcome
    message and registering a callback for the next user message via
    ``qa_choose_mode``.  The user's name is interpolated into the greeting if
    available.
    """
    username = message.from_user.first_name or ''
    welcome_text = (
        f"Привет, <b>{username}</b>! 👋🏻\n"
        "Я бот‑помощник для QA. Я умею генерировать тестовые банковские карты "
        "и тестовые файлы различных форматов и размеров.\n\n"
        "Выберите, что вы хотите сгенерировать."
    )
    # Build an inline keyboard for the main menu. Inline buttons are displayed
    # directly beneath the message and are more prominent than reply keyboards.
    menu_markup = InlineKeyboardMarkup()
    menu_markup.add(
        InlineKeyboardButton('Генерировать карту', callback_data='menu_card'),
        InlineKeyboardButton('Генерировать файл', callback_data='menu_file'),
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=menu_markup,
    )
    # No need to register a next step here; interaction continues via callback
    # queries handled in ``handle_callbacks``.


def qa_choose_mode(message: types.Message) -> None:
    """
    Handles the user's selection from the main menu.

    Depending on the button pressed, this function triggers either the credit
    card generation workflow or the file generation workflow.  If the user
    sends an unexpected message or chooses to return to the start, the main
    menu is shown again.
    """
    text = message.text
    if text == 'Генерировать карту':
        # Prompt for the card type
        reply = bot.send_message(
            message.chat.id,
            "Выбери тип карты:",
            reply_markup=card_type_keyboard,
        )
        bot.register_next_step_handler(reply, qa_generate_card)
    elif text == 'Генерировать файл':
        # Prompt for the file extension
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        # Spread the list of formats across rows (max 5 per row)
        markup.add(*FORMATS, row_width=5)
        # Include a back-to-start button
        markup.add('Вернуться в начало')
        reply = bot.send_message(
            message.chat.id,
            "🔹 Выберите расширение файла:",
            reply_markup=markup,
        )
        bot.register_next_step_handler(reply, file_check_format)
    elif text in ('Вернуться в начало', '/start'):
        # Return to the beginning
        qa_start(message)
    else:
        # Unrecognised input; prompt again
        reply = bot.send_message(
            message.chat.id,
            "Пожалуйста, выберите один из вариантов.",
            reply_markup=main_menu_keyboard,
        )
        bot.register_next_step_handler(reply, qa_choose_mode)


def qa_generate_card(message: types.Message) -> None:
    """
    Generates a test credit card number based on the selected card type.

    The function looks up the user's choice in ``CARD_LABEL_TO_TYPE`` and uses
    ``faker.credit_card_number`` to produce a dummy number.  After sending the
    result back to the user, it presents a button to return to the main menu.
    If the user enters anything unexpected, the function re-prompts them to
    choose a valid card type.
    """
    text = message.text

    # Allow returning to the start from this step
    if text in ('Вернуться в начало', '/start'):
        qa_start(message)
        return

    # Check if the user pressed one of the valid card buttons
    if text in CARD_LABEL_TO_TYPE:
        card_type = CARD_LABEL_TO_TYPE[text]
        # Generate a dummy card number; Faker supports these identifiers
        card_number = faker.credit_card_number(card_type)
        # Prepare a keyboard with a single button to go back to the main menu
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Вернуться в начало')
        # Send the result
        reply_text = f'Тестовая карта {text}:\n<code>{card_number}</code>'
        reply = bot.send_message(
            message.chat.id,
            reply_text,
            reply_markup=markup,
        )
        # After showing the card number, wait for the user to go back to start
        bot.register_next_step_handler(reply, qa_start)
    else:
        # Invalid selection; ask again
        reply = bot.send_message(
            message.chat.id,
            'Не понимаю. Пожалуйста, выбери тип карты из предложенных.',
            reply_markup=card_type_keyboard,
        )
        bot.register_next_step_handler(reply, qa_generate_card)


# ---------------------------------------------------------------------------
# Callback query handlers for inline keyboards
#
# Telegram inline keyboards require a separate handler that reacts to button
# presses via callback_data.  The following function intercepts all callback
# queries and routes them based on the callback_data string.  Inline buttons
# are used for the main menu and card selection; file generation falls back
# to reply keyboards due to the large number of formats.
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery) -> None:
    """Process callbacks from inline buttons."""
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if data == 'menu_card':
        # Display card type selection as inline buttons
        card_markup = InlineKeyboardMarkup()
        card_markup.add(
            InlineKeyboardButton('VISA', callback_data='card_VISA'),
            InlineKeyboardButton('Mastercard', callback_data='card_Mastercard'),
        )
        card_markup.add(
            InlineKeyboardButton('Maestro', callback_data='card_Maestro'),
            InlineKeyboardButton('JCB', callback_data='card_JCB'),
        )
        # Edit the previous message to display the new inline keyboard
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text='Выберите тип карты:',
            reply_markup=card_markup,
        )
        bot.answer_callback_query(call.id)
        return
    elif data == 'menu_file':
        # Send a new message prompting for file extension with a reply keyboard
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*FORMATS, row_width=5)
        markup.add('Вернуться в начало')
        reply = bot.send_message(
            chat_id,
            '🔹 Выберите расширение файла:',
            reply_markup=markup,
        )
        # Delegate the next step to the file workflow
        bot.register_next_step_handler(reply, file_check_format)
        bot.answer_callback_query(call.id)
        return
    elif data.startswith('card_'):
        # Extract the card label from the callback data (e.g. card_VISA -> VISA)
        label = data.split('_', 1)[1]
        # Map the label to the corresponding faker card type; capitalise as needed
        card_label = label  # e.g. 'VISA' or 'Mastercard'
        card_type = CARD_LABEL_TO_TYPE.get(card_label)
        if card_type is None:
            # Unknown card; ignore
            bot.answer_callback_query(call.id)
            return
        # Generate a dummy card number
        card_number = faker.credit_card_number(card_type)
        # Compose a message with CVV hints for successful and failed payments
        card_text = (
            f'Тестовая карта {card_label}:\n'
            f'<code>{card_number}</code>\n\n'
            'Используйте следующие CVC/CVV коды для моделирования различных исходов:\n'
            '125 — успешная операция\n'
            '300 — отказ (недостаточно средств)'
        )
        # Remove the inline keyboard from the previous message
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
        # Provide a reply keyboard with a single button to return to the main menu
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add('Вернуться в начало')
        reply = bot.send_message(
            chat_id,
            card_text,
            reply_markup=kb,
        )
        # After sending card details, wait for user to return to start
        bot.register_next_step_handler(reply, qa_start)
        bot.answer_callback_query(call.id)
        return
    else:
        # For any other callback data, simply acknowledge
        bot.answer_callback_query(call.id)


def file_check_format(message: types.Message) -> None:
    """
    First step of the file generation workflow: verify the chosen file extension.

    If the extension is valid, the function prompts for a unit of measurement.
    If the user requests to go back to the start, the main menu is shown.
    Invalid entries re-prompt the user with the list of valid formats.
    """
    text = message.text
    # User wants to return to the beginning
    if text in ('Вернуться в начало', '/start'):
        qa_start(message)
        return
    # Valid extension selected
    if text in FORMATS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            'B (байты)',
            'KB (килобайты)',
            'MB (мегабайты)',
            'Вернуться в начало',
        )
        reply = bot.send_message(
            message.chat.id,
            (
                f"🔹 Выбранное расширение — <b>{text}</b>\n\n"
                "Теперь выбери единицу измерения.\n"
                "<u>Небольшая памятка по размерам:</u>\n"
                "1 килобайт = 1 024 байта\n"
                "1 мегабайт = 1 024 килобайта = 1 048 576 байт"
            ),
            reply_markup=markup,
        )
        # Pass along the chosen format as the second argument
        bot.register_next_step_handler(reply, file_check_unit, message)
    else:
        # Rebuild the extension keyboard, including a back-to-start button
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*FORMATS, row_width=5)
        markup.add('Вернуться в начало')
        reply = bot.send_message(
            message.chat.id,
            "Выбрано неверное расширение файла, пожалуйста выбери одно из меню ниже 🙂⬇️",
            reply_markup=markup,
        )
        bot.register_next_step_handler(reply, file_check_format)


def file_check_unit(message: types.Message, format_message: types.Message) -> None:
    """
    Second step of the file generation workflow: validate the unit of measurement.

    The user can go back to the previous step (choose extension) by pressing
    'Назад', return to the main menu, or pick a valid unit (B, KB or MB).  On
    success the function will ask for the numeric size.
    """
    text = message.text
    # Back to extension selection
    if text == 'Назад':
        file_check_format(format_message)
        return
    # Return to start
    if text in ('Вернуться в начало', '/start'):
        qa_start(message)
        return
    # Valid unit selected
    if text in ('B (байты)', 'KB (килобайты)', 'MB (мегабайты)'):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Назад', 'Вернуться в начало')
        reply = bot.send_message(
            message.chat.id,
            (
                f"🔹 Выбранное расширение — <b>{format_message.text}</b>\n"
                f"🔹 Единица измерения — <b>{text}</b>\n\n"
                "Остался последний шаг, напиши размер файла. "
                "Я принимаю только целые числа, без пробелов и прочих символов.\n"
                "⛔️ <u>Ограничения по размеру:</u>\n"
                "<b>Минимум</b> — 1 байт\n"
                "<b>Максимум</b> — 45 MB (это 46 080 KB или 47 185 920 байт)"
            ),
            reply_markup=markup,
        )
        # Pass along both the chosen format and unit
        bot.register_next_step_handler(reply, file_check_size, format_message, message)
    else:
        # Invalid unit; ask again
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            'B (байты)',
            'KB (килобайты)',
            'MB (мегабайты)',
            'Вернуться в начало',
        )
        reply = bot.send_message(
            message.chat.id,
            "Неверная единица измерения. Пожалуйста, выбери одну из меню ниже 🙂",
            reply_markup=markup,
        )
        bot.register_next_step_handler(reply, file_check_unit, format_message)


def file_check_size(
    message: types.Message,
    format_message: types.Message,
    unit_message: types.Message,
) -> None:
    """
    Final step of the file generation workflow: validate the numeric size, and
    generate and send the file if within limits.

    Supports returning to the previous step ('Назад'), going back to the main
    menu, or re‑prompting on invalid input.  When generating the file the code
    writes random bytes to disk, sends the file as a document, and then cleans
    up the temporary file.
    """
    text = message.text
    # Go back to unit selection
    if text == 'Назад':
        file_check_format(format_message)
        return
    # Return to start
    if text in ('Вернуться в начало', '/start'):
        qa_start(message)
        return
    # Validate numeric input: ensure we have text and it is composed of digits
    if not (isinstance(text, str) and text.isdigit()):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('Назад', 'Вернуться в начало')
        reply = bot.send_message(
            message.chat.id,
            "Неверный размер файла. Пожалуйста введи правильный, "
            "я принимаю только целые положительные числа, без пробелов и прочих символов 🙂",
            reply_markup=markup,
        )
        bot.register_next_step_handler(reply, file_check_size, format_message, unit_message)
        return

    # Convert to integer for calculations
    size = int(text)
    # Determine size in bytes based on the unit chosen
    if unit_message.text == 'MB (мегабайты)':
        size_bytes = size * 1024 * 1024
        unit_short = 'MB'
    elif unit_message.text == 'KB (килобайты)':
        size_bytes = size * 1024
        unit_short = 'KB'
    else:
        # Bytes
        size_bytes = size
        unit_short = 'B'

    # Enforce limits: minimum 1 byte and maximum 45 MB (45 * 1024 * 1024)
    if size_bytes < 1 or size_bytes > 47_185_920:
        reply = bot.send_message(
            message.chat.id,
            (
                "Размер файла выходит за границы моих возможностей.\n"
                "<u>Мои ограничения:</u>\n"
                "<b>Минимум</b> — 1 байт\n"
                "<b>Максимум</b> — 45 MB (это 46 080 KB или 47 185 920 байт)\n\n"
                "Пожалуйста, введи подходящий размер 🙂"
            ),
        )
        bot.register_next_step_handler(reply, file_check_size, format_message, unit_message)
        return

    # Notify the user that file generation has started.  Without this message
    # the bot appears unresponsive while performing heavy disk I/O and network
    # operations.  We also trigger a chat action to indicate that a document
    # upload is in progress, which displays an animated status in the chat.
    bot.send_message(
        message.chat.id,
        "⏳ Генерирую тестовый файл. Пожалуйста, подождите...",
    )
    # Notify Telegram that the bot is uploading a document (shows a progress
    # indicator like "Sending document...").  This helps users understand
    # that the bot is still working.
    bot.send_chat_action(message.chat.id, action='upload_document')

    # Generate a unique filename based on timestamp and size
    timestamp = int(time.time())
    filename = f"{timestamp}-{size_bytes}-bytes{format_message.text}"
    # Write random bytes to the file
    with open(filename, "wb") as f:
        f.write(os.urandom(size_bytes))

    # Build a user-friendly caption with formatted numbers
    if unit_short in ('MB', 'KB'):
        size_str = f"{size:,}".replace(",", " ")
        size_bytes_str = f"{size_bytes:,}".replace(",", " ")
        caption = (
            f"🙌🏻 Ура, твой тестовый файлик с расширением "
            f"<b>{format_message.text}</b> успешно сгенерирован!\n\n"
            f"Его размер — <b>{size_str} {unit_short}</b>\n"
            f"В байтах — <b>{size_bytes_str} B</b>"
        )
    else:
        size_bytes_str = f"{size_bytes:,}".replace(",", " ")
        caption = (
            f"🙌🏻 Ура, твой тестовый файлик с расширением "
            f"<b>{format_message.text}</b> успешно сгенерирован!\n\n"
            f"Его размер — <b>{size_bytes_str} {unit_short}</b>"
        )

    # Send the generated file as a document with robust error handling
    try:
        with open(filename, "rb") as f:
            # Use a larger timeout when uploading files to avoid connection
            # timeouts on slower networks.  Passing ``timeout`` here overrides
            # the default read timeout and allows the request to take up to
            # several minutes if necessary.
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('Вернуться в начало')
            reply = bot.send_document(
                message.chat.id,
                f,
                caption=caption,
                reply_markup=markup,
                timeout=300,
            )
    except Exception as e:
        # Catch any exception during upload to prevent the bot from crashing.
        # Telegram sometimes drops large uploads due to network conditions or
        # server-side limits; inform the user and suggest a smaller file size.
        bot.send_message(
            message.chat.id,
            (
                "⚠️ Произошла ошибка при отправке файла.\n"
                "Возможно, нестабильное соединение или размер файла слишком велик.\n"
                "Пожалуйста, попробуйте ещё раз с меньшим размером."
            ),
        )
        # Ensure temporary file is cleaned up before returning to start
        try:
            os.unlink(filename)
        except FileNotFoundError:
            pass
        # Prompt the user to choose another size or return to main menu
        qa_start(message)
        return
    finally:
        # Always attempt to remove the temporary file from disk
        try:
            os.unlink(filename)
        except FileNotFoundError:
            pass

    # After sending the file successfully, wait for the user to return to start
    bot.register_next_step_handler(reply, qa_start)


def main() -> None:
    """
    Entry point for the bot when the module is executed as a script.

    Calls ``infinity_polling`` to start listening for messages.  The ``main``
    function is separated to allow importing this module without immediately
    running the bot.
    """
    bot.infinity_polling()


if __name__ == '__main__':
    main()