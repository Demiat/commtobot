"""
Telegram-Bot
Version 1.0 (under construct)
"""

import os
import datetime as dt
import pickle
import time
import logging
import logging.config
import importlib
import json
import re
import signal

import requests
import speech_recognition as sr
import portalocker as prtl
from dotenv import load_dotenv
from telebot import TeleBot, types, apihelper

import config
import message as ms
from logger_conf import get_config


load_dotenv()
logger = logging.getLogger(__name__)

DEMIAT_BOT_ID = os.getenv('DEMIAT_BOT_ID')
DEMIAT_BOT_TOKEN = os.getenv('DEMIAT_BOT_TOKEN')
MY_TELEGRAM_ID = os.getenv('MY_TELEGRAM_ID')
SBER_AUTH_TOKEN = os.getenv('SBER_AUTH_TOKEN')
RqUID = os.getenv('RqUID')
SECRET_NAMES = (
    'DEMIAT_BOT_ID',
    'DEMIAT_BOT_TOKEN',
    'MY_TELEGRAM_ID',
    'SBER_AUTH_TOKEN',
    'RqUID'
)

GIGA_URL = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
GIGA_AUTH_URL = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
PAYLOAD = 'scope=GIGACHAT_API_PERS'
HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'RqUID': RqUID,
    'Authorization': f'Basic {SBER_AUTH_TOKEN}'
}

bot = TeleBot(token=DEMIAT_BOT_TOKEN)

# КЛАВИАТУРА
bot_memory_keyboard = types.InlineKeyboardMarkup()
button_bot_mem = types.InlineKeyboardButton(
    text='Память Робота',
    callback_data='memory'
)
bot_memory_keyboard.add(button_bot_mem)

if not os.path.exists('data_users.pkl'):  # if not exist file, create!
    fdu = open('data_users.pkl', 'wb')
    pickle.dump(dict(), fdu)
    fdu.close()


def open_database():
    f = open('data_users.pkl', 'r+b')
    prtl.lock(f, prtl.LOCK_EX)
    data_users = pickle.load(f)
    return data_users, f


def close_database(f, data_users):
    f.seek(0)
    pickle.dump(data_users, f)
    f.flush()
    prtl.unlock(f)
    f.close()


def check_envs():
    """Проверяет наличие переменных окружения."""
    find_no_envs = ''
    for name in SECRET_NAMES:
        if not globals()[name]:
            find_no_envs += f'{name}, '
    if find_no_envs:
        envs_message = ms.NO_ENVS.format(envs=find_no_envs)
        logger.critical(envs_message)
        raise ValueError(envs_message)


def send_message(pars_to_send, stype=None):
    """Отправляет сообщения."""
    try:
        match stype:
            case 'text':
                bot.send_message(**pars_to_send)
            case 'photo':
                bot.send_photo(**pars_to_send)
            case 'typing':
                bot.send_chat_action(**pars_to_send)
            case _:
                raise ValueError(ms.UNKNOWN_STYPE.format(stype=stype))
        logger.debug(
            ms.MESSAGE_WAS_SENT.format(chat_id=pars_to_send['chat_id'])
        )
    except apihelper.ApiException as e:
        logger.error(
            ms.BAD_SEND_MESSAGE.format(
                chat_id=pars_to_send['chat_id'], exc_error=e
            )
        )


@bot.callback_query_handler(func=None)
def handle_callback(call):
    user_id = call.from_user.id
    data_users, f = open_database()
    if call.data == 'memory':
        store_hys = data_users[user_id]['history']
        if store_hys == ms.STORE_HYS_YES:
            data_users[user_id]['history'] = ms.STORE_HYS_NO
            txt = ms.BOT_OFF_MEMORY
        else:
            data_users[user_id]['history'] = ms.STORE_HYS_YES
            txt = ms.BOT_ON_MEMORY
        repl = ms.CAP.format(
            name=call.from_user.first_name,
            bot_on_mem=data_users[user_id]['history'],
            lim_at_day=config.QUERY_LIM_AT_DAY
        )
    close_database(f, data_users)
    try:
        bot.answer_callback_query(call.id, text=txt)
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=repl,
            reply_markup=bot_memory_keyboard,
            parse_mode='HTML'
        )
    except apihelper.ApiException as e:
        logger.error(
            ms.BAD_SEND_MESSAGE.format(
                chat_id=call.message.chat.id, exc_error=e
            )
        )


@bot.message_handler(commands=['start'])
def wake_up(message):
    """Старт!"""
    user_id = message.chat.id
    data_users, f = open_database()
    if user_id not in data_users:  # if user new
        data_users[user_id] = {
            'name': message.chat.username,
            'count_query': 0,
            'query_limit': 0,
            'count_tokens': 0,
            'last_enter': dt.datetime.now().strftime("%Y-%m-%d"),
            'history': 'НЕТ'
        }
    close_database(f, data_users)

    send_message(dict(
        chat_id=message.chat.id,
        photo=open(config.DEMBOT_PHOTO, 'rb'),
        caption=ms.CAP.format(
            name=message.chat.first_name,
            lim_at_day=config.QUERY_LIM_AT_DAY,
            bot_on_mem=data_users[user_id]['history'],
        ),
        reply_markup=bot_memory_keyboard,
        parse_mode='HTML'
    ), stype='photo')


@bot.message_handler()
def quest(message):
    """Ретранслятор к GPT."""
    # Выйти, если сообщение пришло из канала, а не от отдельного пользователя
    if re.match(r'^-\d+', str(message.from_user.id)):
        return None

    username = message.chat.username
    user_id = message.chat.id

    send_message(
        dict(chat_id=message.chat.id, action='typing'), stype='typing'
    )


def stop_bot(signum, frame):
    logger.info("Завершение работы бота...")
    sys.exit(0)


signal.signal(signal.SIGINT, stop_bot)


def main():
    # pwd = os.getcwd()
    # os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(
    #     pwd, 'static', 'russian_trusted_root_ca.cer'
    # )
    check_envs()
    while True:
        logger.info(ms.START_LOG_MESSAGE)
        try:
            bot.polling()
        except BaseException:
            exit(1)
        except Exception as e:
            logger.exception(ms.FRONTIER_ERROR.format(e=e))
            time.sleep(10)


if __name__ == '__main__':
    logging.config.dictConfig(get_config(__name__, __file__))
    main()
