"""
Telegram-Bot
Version 1.0
"""

import os
import datetime as dt
import pickle
import time
import logging
import traceback
import logging.config
import importlib
import json
import re
from http import HTTPStatus

import requests
import speech_recognition as sr
from pydub import AudioSegment
import portalocker as prtl
from dotenv import load_dotenv
from telebot import TeleBot, types, apihelper

import config
import message as ms
from logger_conf import get_config
from exceptions import NoHttpStatusOk


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
GIGA_FILES_URL = (
    'https://gigachat.devices.sberbank.ru/api/v1/files/{file_uid}/content'
)
PAYLOAD = 'scope=GIGACHAT_API_PERS'
HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'RqUID': RqUID,
    'Authorization': f'Basic {SBER_AUTH_TOKEN}'
}
PARS_TO_AUTH_TOKEN = dict(
    method='POST',
    url=GIGA_AUTH_URL,
    headers=HEADERS,
    data=PAYLOAD
)
TYPE_PHOTO = 'photo'
TYPE_TEXT = 'text'
TYPE_TYPING = 'typing'
MEMORY_LENGHT = 20
DAY_TO_LEFT = 15


def send_request(pars_to_send, attempts_left=2):
    """Отправляет запросы."""
    global acc_token
    try:
        response = requests.request(**pars_to_send, verify=True)
    except requests.RequestException as e:
        raise ConnectionError(
            ms.BAD_CONNECTION.format(**pars_to_send, exc_error=e)
        )

    if response.status_code == HTTPStatus.OK:
        if pars_to_send.get('stream'):  # Отдать без преобразования в JSON
            return response
        return response.json()
    if (
        response.status_code == HTTPStatus.UNAUTHORIZED
        and attempts_left > 0
    ):
        # Получение токена доступа (живет 30 мин)
        logger.info(ms.AUTH_TOKEN_REQUESTED)
        access_token = send_request(
            PARS_TO_AUTH_TOKEN, attempts_left-1
        ).get("access_token")
        if access_token:
            pars_to_send['headers']['Authorization'] = f'Bearer {access_token}'
            acc_token = access_token
            return send_request(pars_to_send)
    raise NoHttpStatusOk(
        ms.BAD_HTTP_STATUS.format(
            **pars_to_send,
            status_code=response.status_code
        )
    )


# Начальное получение токена для ответов gpt
acc_token = send_request(PARS_TO_AUTH_TOKEN).get('access_token')

PWD = os.getcwd()

bot = TeleBot(token=DEMIAT_BOT_TOKEN)

# КЛАВИАТУРЫ
bot_memory_keyboard = types.InlineKeyboardMarkup()
button_bot_mem = types.InlineKeyboardButton(
    text='Память Робота',
    callback_data='memory'
)
bot_memory_keyboard.add(button_bot_mem)

bot_memory_keyboard_on_message = types.InlineKeyboardMarkup()
button_bot_mem_on_message = types.InlineKeyboardButton(
    text='Очистить диалог с роботом',
    callback_data='clean_dialog'
)
bot_memory_keyboard_on_message.add(button_bot_mem_on_message)

if not os.path.exists('data_users.pkl'):  # if not exist file, create!
    with open('data_users.pkl', 'wb') as fl:
        pickle.dump({}, fl)


def open_database(give_the_database=True):
    f = open('data_users.pkl', 'r+b')
    prtl.lock(f, prtl.LOCK_EX)
    if give_the_database:
        data_users = pickle.load(f)
        return data_users, f
    return f


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
    chat_id = (
        pars_to_send.get('chat_id') or pars_to_send.get('callback_query_id')
    )
    try:
        match stype:
            case 'text':
                bot.send_message(**pars_to_send)
            case 'photo':
                bot.send_photo(**pars_to_send)
            case 'typing':
                bot.send_chat_action(**pars_to_send)
            case 'answer_callback_query':
                bot.answer_callback_query(**pars_to_send)
            case 'edit_message_caption':
                bot.edit_message_caption(**pars_to_send)
            case _:
                raise ValueError(ms.UNKNOWN_STYPE.format(stype=stype))
        logger.debug(
            ms.MESSAGE_WAS_SENT.format(chat_id=chat_id)
        )
    except apihelper.ApiException as e:
        logger.error(
            ms.BAD_SEND_MESSAGE.format(
                chat_id=chat_id, exc_error=e
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

        send_message(dict(
            callback_query_id=call.id,
            text=txt
        ), stype='answer_callback_query'
        )
        send_message(dict(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=repl,
            reply_markup=bot_memory_keyboard,
            parse_mode='HTML'
        ), stype='edit_message_caption'
        )
    elif call.data == 'clean_dialog':
        pars_to_send = dict(
            callback_query_id=call.id,
            show_alert=False
        )
        if os.path.exists(f'{PWD}/hys/{user_id}.pkl'):
            os.remove(f'{PWD}/hys/{user_id}.pkl')
            pars_to_send['text'] = ms.DEL_BOT_CONTEXT
        else:
            pars_to_send['text'] = ms.NO_BOT_CONTEXT
        send_message(pars_to_send, stype='answer_callback_query')


@bot.message_handler(commands=['start'])
def wake_up(message):
    """Старт!"""
    user_id = message.chat.id
    data_users, f = open_database()
    if user_id not in data_users:  # Если пользователь новый
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
    ), stype=TYPE_PHOTO)


@bot.message_handler(commands=['info'])
def info(message):
    """Вывод информации для пользователя."""
    data_users, f = open_database()
    close_database(f, data_users)
    user_id = message.from_user.id
    send_message(dict(
        chat_id=user_id,
        text=ms.HOW_MANY_REQUESTS.format(
            how_req=data_users[user_id]['query_limit'],
            lim_at_day=config.QUERY_LIM_AT_DAY
        )), stype=TYPE_TEXT
    )


@bot.message_handler(commands=['conf_reload'])
def conf_reload(message):
    """Динамично перезагружает файл конфигурации."""
    importlib.reload(config)
    logger.warning(ms.CONF_RELOAD)
    send_message(dict(
        chat_id=message.from_user.id,
        text=ms.CONF_RELOAD
        ), stype=TYPE_TEXT
    )


@bot.message_handler(commands=['recalc'])
def recalc(message):
    """Удаляет старых пользователей."""
    now_data = dt.datetime.now()
    data_users, f = open_database()
    count_del = 0
    keys_to_remove = []
    for usr_id in data_users:
        usr_dt = dt.datetime.strptime(
            data_users[usr_id]['last_enter'], '%Y-%m-%d'
        )
        t_delta = now_data - usr_dt
        # Если пользователь древнее константных дней
        if t_delta.days > DAY_TO_LEFT:
            count_del += 1
            send_message(dict(
                chat_id=MY_TELEGRAM_ID,
                text=ms.DEL_OLD_USER.format(
                    usr_id=usr_id,
                    name=data_users[usr_id]['name']
                    )
                ), stype=TYPE_TEXT
            )
            # Готовим старых пользователей для удаления
            keys_to_remove.append(usr_id)
            # Удаляем историю старого пользователя
            if os.path.exists(f'{PWD}/hys/{usr_id}.pkl'):
                os.remove(fr'{PWD}/hys/{usr_id}.pkl')
    for key in keys_to_remove:  # Удаляем старых пользователей
        del data_users[key]
    send_message(dict(
        chat_id=MY_TELEGRAM_ID,
        text=ms.REMAKING_USERS.format(
            count_del=count_del,
            num_of_users=len(data_users)
            )
        ), stype=TYPE_TEXT
    )
    close_database(f, data_users)


@bot.message_handler(content_types=['voice', 'text'])
def quest(message):
    """Ретранслятор к GPT."""
    user_id = message.from_user.id
    # Выйти, если сообщение пришло из канала, а не от отдельного пользователя
    if re.match(r'^-\d+', str(user_id)):
        return None

    # Отправляем статус "печатает"
    send_message(
        dict(chat_id=user_id, action='typing'), stype=TYPE_TYPING
    )

    # Откроем базу данных для работы с данными data_users
    # И сразу закроем на время формирования ответа ИИ
    data_users, f = open_database()
    close_database(f, data_users)

    now_day = dt.datetime.now().strftime('%Y-%m-%d')

    # Если сообщение от пользователя - голосовое
    from_voice_flag = False
    au_to_text = ''
    if message.content_type == 'voice':
        voice_file_url = bot.get_file_url(message.voice.file_id)
        oganame = f'voice_{user_id}.oga'
        wavname = f'voice_{user_id}.wav'
        audio_answer = send_request({
            'method': 'GET',
            'url': f'{voice_file_url}',
            'stream': True
        })

        with open(oganame, 'wb') as fl:
            fl.write(audio_answer.content)

        # Перевод из oga в wav
        AudioSegment.from_file(oganame).export(
            f'voice_{user_id}.wav', format='wav')

        g = sr.Recognizer()
        with sr.AudioFile(wavname) as source:
            audio = g.record(source)  # read the entire voice file
        try:
            au_to_text = g.recognize_google(audio, language='ru')
        except sr.UnknownValueError as e:
            logger.error(ms.NO_SPEECH, e)
            send_message(
                chat_id=user_id,
                text=ms.NO_SPEECH
            )
            return None
        except sr.RequestError as e:
            logger.error(ms.CONNECT_ERROR.format(e=e))
            send_message(
                chat_id=user_id,
                text=ms.CONNECT_ERROR
            )
            return None
        from_voice_flag = True

        os.remove(oganame)
        os.remove(wavname)

    # Работаем с данными пользователя
    data_users[user_id]['count_query'] += 1
    if (
        data_users[user_id]['query_limit'] >= config.QUERY_LIM_AT_DAY
        and now_day in data_users[user_id]['last_enter']
    ):
        send_message(
            dict(chat_id=message.chat.id, text=ms.LIM_AT_DAY),
            stype=TYPE_TEXT
        )
        return None
    elif now_day not in data_users[user_id]['last_enter']:
        data_users[user_id]['query_limit'] = 0
    data_users[user_id]['last_enter'] = now_day
    data_users[user_id]['query_limit'] += 1

    # Читаем историю сообщений
    hys_responce = []
    if data_users[user_id]['history'] == ms.STORE_HYS_YES:
        if os.path.exists(f'{PWD}/hys/{user_id}.pkl'):
            with open(fr'{PWD}/hys/{user_id}.pkl', 'rb') as fl:
                hys_responce = pickle.load(fl)

    # Формирование вопроса вместе с историей сообщений
    mess = au_to_text if from_voice_flag else message.text
    hys_responce.append('user: ' + mess)
    context_diag = ''.join(hys_responce)

    # Формирование запроса к ИИ
    pars_to_send = dict(
        method='POST',
        url=GIGA_URL,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {acc_token}'
        },
        data=json.dumps({
            "model": "GigaChat",
            "messages": [
                {
                    "role": "user",
                    "content": context_diag
                }
            ],
            "temperature": 1,
            "top_p": 0.1,
            "n": 1,
            "stream": False,
            "max_tokens": 512,
            "repetition_penalty": 1,
            "function_call": "auto",
        })
    )

    # Ответ ИИ
    response = send_request(pars_to_send)

    # Если прислано изображение
    if '<img src=' in (
        img_src := response['choices'][0]['message']['content']
    ):
        img_uid = img_src.split('\"')
        url_img = GIGA_FILES_URL.format(file_uid=img_uid[1])
        response_img = send_request(dict(
            method='GET',
            url=url_img,
            headers={
                'Accept': 'application/jpg',
                'Authorization': f'Bearer {acc_token}'
            },
            stream=True
        ))
        send_message(dict(
            chat_id=message.chat.id,
            photo=response_img.raw,
            parse_mode='HTML'
        ), stype=TYPE_PHOTO
        )
        del response_img
    else:  # Если прислан текст
        text_from_ai = response['choices'][0]['message']['content']
        pars_to_send = dict(
            chat_id=message.chat.id,
            text=text_from_ai,
        )
        if data_users[user_id]['history'] == ms.STORE_HYS_YES:
            # Отправим клавиатуру в сообщении
            pars_to_send['reply_markup'] = bot_memory_keyboard_on_message
            # Запишем историю сообщений
            with open(f'{PWD}/hys/{user_id}.pkl', 'wb') as fl:
                if len(hys_responce) > MEMORY_LENGHT:
                    del hys_responce[:2]
                hys_responce.append('assistant: ' + text_from_ai)
                pickle.dump(hys_responce, fl)
        send_message(pars_to_send, stype=TYPE_TEXT)

    tokens_used = response['usage']['total_tokens']
    data_users[user_id]['count_tokens'] += tokens_used

    # Запишем всю накопленную информацию про пользователя
    f = open_database(give_the_database=False)
    close_database(f, data_users)


def main():
    """Основная функция работы."""
    check_envs()
    while True:
        logger.info(ms.START_LOG_MESSAGE)
        try:
            bot.polling()
        except Exception:
            logger.exception(ms.FRONTIER_ERROR.format(
                e=traceback.format_exc(limit=1)
            ))
        else:
            break
        finally:
            time.sleep(5)


if __name__ == '__main__':
    logging.config.dictConfig(get_config(__name__, __file__))
    main()
