"""
Telegram-Bot
Version 3.3 turbo (under construct)
"""

import os
import datetime as dt
import pickle
import logging
import importlib
import json
import re

import requests
from pydub import AudioSegment
import speech_recognition as sr
import portalocker as prtl
import telegram
from telegram.ext import (filters, MessageHandler, ApplicationBuilder,
                          CommandHandler, CallbackQueryHandler
                          )

import config


# Настроим модуль ведения журнала логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def quest(update, context):
    """Общение с GPT ботом."""
    # Выйти, если сообщение пришло из канала, а не от отдельного пользователя
    if not re.match(r'^-\d+', str(update.effective_chat.id)) is None:
        return None

    username = update.effective_user.username
    user_id = update.effective_user.id

    await context.bot.send_chat_action(
        chat_id=update.effective_user.id,
        action=telegram.constants.ChatAction.TYPING
    )

    # Проверка подписки пользователя на канал телеграмма
    # try:
    #     chat_member = await context.bot.get_chat_member(
    #         config.id_channel_telegram, user_id
    #     )
    # except Exception:
    #     pass
    # else:
    #     if chat_member['status'] == 'left':
    #         await context.bot.send_message(
    #             chat_id=update.effective_chat.id,
    #             text=config.subscribe_message,
    #             reply_markup=keyboard_anka
    #         )
    #         return None
    # <

    # Если сообщение от пользователя - аудио
    from_voice_flag = False
    au_to_text = ''
    if getattr(update.message, 'voice', None):
        voice_file = await context.bot.getFile(update.message.voice.file_id)
        oganame = f'voice_{user_id}.oga'
        wavname = f'voice_{user_id}.wav'
        path = voice_file.file_path
        answ = requests.get(path)
        if answ.status_code == 200:
            with open(oganame, 'wb') as wr:
                wr.write(answ.content)

            AudioSegment.from_file(oganame).export(
                f'voice_{user_id}.wav', format='wav')

            g = sr.Recognizer()
            with sr.AudioFile(wavname) as source:
                audio = g.record(source)  # read the entire voice file
            try:
                au_to_text = g.recognize_google(audio, language='ru')
            except sr.UnknownValueError:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text='Речь неразборчива! Повторите запрос!'
                )
                return None
            except sr.RequestError as e:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f'Ошибка связи: {e}! Повторите запрос!'
                )
                return None
            from_voice_flag = True

            os.remove(oganame)
            os.remove(wavname)
    # <

    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    now_day = now[:-6]

    f = open('data_users.pkl', 'r+b')
    prtl.lock(f, prtl.LOCK_EX)
    data_users = pickle.load(f)  # Получить базу данных пользователей

    if user_id not in data_users:  # Если пользователь новый
        data_users[user_id] = {
            'name': username,
            'count_query': 0,
            'query_limit': 0,
            'count_tokens': 0,
            'last_enter': now_day,
            'history': 'no'
        }
    else:
        data_users[user_id]['count_query'] += 1
        if (
            data_users[user_id]['query_limit'] >= config.query_lim_at_day
            and now_day in data_users[user_id]['last_enter']
        ):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='DemmiatBot: Вы исчерпали дневной лимит запросов!'
            )
            return None
        elif now_day not in data_users[user_id]['last_enter']:
            data_users[user_id]['query_limit'] = 0
        data_users[user_id]['last_enter'] = now_day
        data_users[user_id]['query_limit'] += 1

    # Читаем историю сообщений
    hys_responce = []
    if data_users[user_id]['history'] == 'yes':
        try:
            uh = open(fr'{cwd}/hys/{user_id}.pkl', 'rb')
            hys_responce = pickle.load(uh)
            uh.close()
        except IOError:
            pass
            # open(fr'{cwd}/hys/{user_id}.pkl', 'wb').close()
    # <

    # Формирование вопроса вместе с историей сообщений
    mess = au_to_text if from_voice_flag else update.message.text
    hys_responce.append('user: ' + mess)
    context_diag = ''.join(hys_responce)

    # Получение сначала токена доступа (живет 30 мин)
    response_1 = requests.request(
        "POST",
        config.giga_auth_url,
        headers=config.headers_1,
        data=config.payload_1
    )
    response_json_1 = json.loads(response_1.text)
    giga_access_token = response_json_1['access_token']

    # Формирование запроса к ИИ
    payload_2 = json.dumps({
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
        "repetition_penalty": 1
    })
    headers_2 = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {giga_access_token}'
    }

    # Ответ ИИ
    response = requests.request(
        "POST", config.giga_url, headers=headers_2, data=payload_2)
    response_json = json.loads(response.text)

    # Если прислано изображение
    if '<img src=' in (
        imgsrc := response_json['choices'][0]['message']['content']
    ):
        # imgsrc_id = re.match('.*<img src=\"(.+)(\" fuse=\".*)', imgsrc)
        imgsrc_id = imgsrc.split('\"')
        urlimg = (
            f'https://gigachat.devices.sberbank.ru/api/v1/files/'
            f'{imgsrc_id[1]}/content'
        )
        headers_3 = {
            'Accept': 'application/jpg',
            'Authorization': f'Bearer {giga_access_token}'
        }
        responseimg = requests.request(
            "GET",
            urlimg,
            headers=headers_3,
            stream=True
        )
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=responseimg.raw,
            parse_mode='HTML'
        )
        del responseimg
    else:  # Если прислан текст
        itog_answ = response_json['choices'][0]['message']['content']
        if data_users[user_id]['history'] == 'yes':
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=itog_answ, parse_mode='HTML',
                reply_markup=keyboard_clean
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=itog_answ,
                parse_mode='HTML'
            )

        # Запись истории сообщений
        if data_users[user_id]['history'] == 'yes':
            uh = open(f'{cwd}/hys/{user_id}.pkl', 'wb')
            if len(hys_responce) > 20:
                del hys_responce[:2]
            hys_responce.append('assistant: ' + itog_answ)
            pickle.dump(hys_responce, uh)
            uh.close()
        # <

    # Запись информации о пользователе
    if response.text:
        tokens_used = response_json['usage']['total_tokens']
        data_users[user_id]['count_tokens'] += tokens_used
    # <

    f.seek(0)
    pickle.dump(data_users, f)
    f.flush()
    prtl.unlock(f)
    f.close()


async def start(update, context):
    user_id = update.effective_user.id
    username = update.effective_user.username
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    now_day = now[:-6]

    with open('data_users.pkl', 'r+b') as f:
        prtl.lock(f, prtl.LOCK_EX)
        data_users = pickle.load(f)
        if user_id not in data_users:  # if user new
            data_users[user_id] = {
                'name': username,
                'count_query': 0,
                'query_limit': 0,
                'count_tokens': 0,
                'last_enter': now_day,
                'history': 'no'
            }
            f.seek(0)
            pickle.dump(data_users, f)
            f.flush()
        prtl.unlock(f)
    repl = cap.format(config.query_lim_at_day, data_users[user_id]['history'])
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open('static/dembot.jpg', 'rb'),
        caption=repl,
        reply_markup=keyboard_start,
        parse_mode='HTML'
    )


async def button_handler(update, context):
    query = update.callback_query
    button_data = query.data
    user_id = update.effective_user.id
    if button_data == 'memory':
        with open('data_users.pkl', 'r+b') as f:
            prtl.lock(f, prtl.LOCK_EX)
            data_users = pickle.load(f)
            store_hys = data_users[user_id]['history']
            if store_hys == 'yes':
                data_users[user_id]['history'] = 'no'
                txt = 'Робот отключил свою память!'
            else:
                data_users[user_id]['history'] = 'yes'
                txt = 'Память робота включена!'
            f.seek(0)
            pickle.dump(data_users, f)
            f.flush()
            prtl.unlock(f)
        repl = cap.format(config.query_lim_at_day,
                          data_users[user_id]['history'])
        await context.bot.answer_callback_query(
            update.callback_query.id,
            text=txt,
            show_alert=False
        )
        try:
            await context.bot.edit_message_caption(
                chat_id=update.effective_chat.id,
                message_id=query.message.message_id,
                caption=repl,
                reply_markup=keyboard_start,
                parse_mode='HTML'
            )
        except Exception:
            await context.bot.answer_callback_query(
                update.callback_query.id,
                text='Ошибка запроса смены сообщения!',
                show_alert=False
            )
    elif button_data == 'clean_dialog':
        if os.path.exists(f'{cwd}/hys/{user_id}.pkl'):
            os.remove(f'{cwd}/hys/{user_id}.pkl')
            await context.bot.answer_callback_query(
                update.callback_query.id,
                text='Контекст общения с роботом удалён!',
                show_alert=False
            )
        else:
            await context.bot.answer_callback_query(
                update.callback_query.id,
                text='Контекст общения с роботом отсутствует!',
                show_alert=False
            )


async def info(update, context):
    f = open('data_users.pkl', 'rb')
    prtl.lock(f, prtl.LOCK_SH)
    data_users = pickle.load(f)
    prtl.unlock(f)
    f.close()
    user_id = update.effective_user.id
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f'Отправленных запросов {data_users[user_id]["query_limit"]} '
            'из {config.query_lim_at_day}'
        )
    )


async def mtu(update, context):
    if hasattr(update.message, 'text'):
        match = re.match(r'/mtu i(-*\d+)[ \t]*(.+)', update.message.text)
        match_all = re.match('/mtu ([^d|u].+)', update.message.text)
        dw = True if '/mtu d' in update.message.text else False
        up = True if '/mtu u' in update.message.text else False
        if match:
            try:
                await context.bot.send_message(
                    chat_id=match.group(1),
                    text=match.group(2)
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f'Не удалось связаться с {match.group(1)}'
                )
            return None
        elif match_all or dw or up:
            if match_all:
                mess_to_users = match_all.group(1)
            elif dw:
                mess_to_users = (
                    'Я готовлюсь отключиться для профилактики. '
                    'При включении сообщу!'
                )
            elif up:
                mess_to_users = (
                    'Протокол включения выполнен! Готов к обслуживанию!'
                )
            now_data = dt.datetime.now()
            f = open('data_users.pkl', 'r+b')
            prtl.lock(f, prtl.LOCK_EX)
            data_users = pickle.load(f)
            keys_to_remove = []
            for usr_id in data_users:
                usr_dt = dt.datetime.strptime(
                    data_users[usr_id]['last_enter'], '%Y-%m-%d')
                t_delta = now_data - usr_dt
                # if user long time ago have chat with bot, del user
                if t_delta.days > 15:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=(
                            f'Удален из-за старости {usr_id} -> '
                            f"{data_users[usr_id]['name']}"
                        )
                    )
                    # Готовим старых пользвоателей для удаления
                    keys_to_remove.append(usr_id)
                    try:
                        # Del history with Bot
                        os.remove(fr'{cwd}/hys/{usr_id}.pkl')
                    except Exception as e:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f'Не удалось удалить {usr_id}.pkl: {e}'
                        )
                else:
                    try:
                        await context.bot.send_message(
                            chat_id=usr_id,
                            text=f'DemmiatBot: {mess_to_users}'
                        )
                    except Exception:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f'Не удалось связаться с {usr_id}'
                        )
            for key in keys_to_remove:  # Удаляем старых пользователей
                del data_users[key]
            f.seek(0)
            pickle.dump(data_users, f)
            f.flush()
            prtl.unlock(f)
            f.close()


async def recalc(update, context):
    now_data = dt.datetime.now()
    with open('data_users.pkl', 'r+b') as f:
        prtl.lock(f, prtl.LOCK_EX)
        data_users = pickle.load(f)
        count_del = 0
        keys_to_remove = []
        for usr_id in data_users:
            usr_dt = dt.datetime.strptime(
                data_users[usr_id]['last_enter'], '%Y-%m-%d')
            t_delta = now_data - usr_dt
            # if user long time ago have chat with bot, del user
            if t_delta.days > 15:
                count_del += 1
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        f'Удален из-за старости {usr_id} -> '
                        f"{data_users[usr_id]['name']}"
                    )
                )
                # Готовим старых пользователей для удаления
                keys_to_remove.append(usr_id)
                try:
                    # Del history with Bot
                    os.remove(fr'{cwd}/hys/{usr_id}.pkl')
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f'Не удалось удалить {usr_id}.pkl: {e}'
                    )
        for key in keys_to_remove:  # Удаляем старых пользователей
            del data_users[key]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Удалено: {count_del}, активных: {len(data_users)}'
        )
        f.seek(0)
        pickle.dump(data_users, f)
        f.flush()
        prtl.unlock(f)


async def mir(update, context):
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=open('unknowability.pdf', 'rb')
    )


async def rel(update, context):
    importlib.reload(config)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Config перезагружен!'
    )


async def nofu(update, context):
    f = open('data_users.pkl', 'rb')
    prtl.lock(f, prtl.LOCK_SH)
    data_users = pickle.load(f)
    prtl.unlock(f)
    f.close()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'Пользователей робота: {len(data_users)}'
    )


if __name__ == '__main__':

    os.environ['REQUESTS_CA_BUNDLE'] = '/static/russian_trusted_root_ca.cer'

    if not os.path.exists('data_users.pkl'):  # if not exist file, create!
        fdu = open('data_users.pkl', 'wb')
        pickle.dump(dict(), fdu)
        fdu.close()

    cwd = os.getcwd()

    cap = '''Привет! Я Demmiat бот-ретранслятор
генеративного предварительно обученного преобразователя (GPT).
Мой внешний вид сформирован искусственной нейротической сетью.

Дневной лимит запросов: {0}
Память робота включена: <b>{1}</b>

/info - вывод технической информации.
/mir - отдать статью создателя о непознаваемом Мире и человеке в нём!'''

    TOKEN = config.demmiatbot_token
    # Cоздание экземпляра бота через ApplicationBuilder
    application = ApplicationBuilder().token(TOKEN).build()

    # Cоздаем обработчик для команды '/start'
    # говорим обработчику, если увидишь команду /start,
    # то вызови функцию start()
    start_handler = CommandHandler('start', start)
    info_handler = CommandHandler('info', info)
    mtu_handler = CommandHandler('mtu', mtu)
    mir_handler = CommandHandler('mir', mir)
    rel_handler = CommandHandler('rel', rel)
    nofu_handler = CommandHandler('nofu', nofu)
    recalc_handler = CommandHandler('recalc', recalc)

    # Создаем обработчик текстовых сообщений,которые будут поступать в функцию
    # quest()
    # Говорим обработчику MessageHandler: если увидишь текстовое сообщение
    # (фильтр `Filters.text`) и это будет не команда
    # (фильтр ~Filters.command), то вызови функцию quest()
    quest_handler = MessageHandler(
        (filters.TEXT | filters.VOICE) & (~filters.COMMAND), quest)

    # Регистрируем обработчики в приложение
    application.add_handler(mtu_handler)
    application.add_handler(start_handler)
    application.add_handler(info_handler)
    application.add_handler(quest_handler)
    application.add_handler(mir_handler)
    application.add_handler(rel_handler)
    application.add_handler(nofu_handler)
    application.add_handler(recalc_handler)
    application.add_handler(CallbackQueryHandler(button_handler))

    # KEYBOARDS
    button_list_start = [
        [telegram.InlineKeyboardButton(
            'Память робота', callback_data='memory')]
    ]
    keyboard_start = telegram.InlineKeyboardMarkup(button_list_start)

    button_list_clean = [
        [telegram.InlineKeyboardButton(
            'Очистить диалог с роботом', callback_data='clean_dialog')]
    ]
    keyboard_clean = telegram.InlineKeyboardMarkup(button_list_clean)

    button_list_channel = [
        [telegram.InlineKeyboardButton(
            "АНКА ПАРТИZАНКА", url='https://t.me/anka_partizanka1010')]
    ]
    keyboard_anka = telegram.InlineKeyboardMarkup(button_list_channel)
    # <

    # Запускаем приложение, слушаем серверы Телеграмм
    application.run_polling()
