"""
Telegram-Bot
Version 3.2 turbo (under construct)
"""

import speech_recognition as sr
import requests
import logging
import datetime as dt
import config
import openai
import os
import pickle
import re
import importlib
import portalocker as prtl
from pydub import AudioSegment
import telegram
# обработчик CommandHandler фильтрует сообщения с командами
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, CallbackQueryHandler

# Настроим модуль ведения журнала логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def quest(update, context):
    """
    Communication with AI
    :param update: auto from application handler
    :param context: auto from application handler
    :return: None
    """
    if not re.match(r'^-\d+', str(update.effective_chat.id)) is None:
        return None  # Exit if question from channel, not users

    username = update.effective_user.username
    user_id = update.effective_user.id

    await context.bot.send_chat_action(chat_id=update.effective_user.id, action=telegram.constants.ChatAction.TYPING)

    # Check subscribe of channel
    try:
        chat_member = await context.bot.get_chat_member(config.id_channel_telegram, user_id)
    except:
        pass
    else:
        if chat_member['status'] == 'left':
            await context.bot.send_message(chat_id=update.effective_chat.id, text=config.subscribe_message,
                                           reply_markup=keyboard_anka)
            return None
    # <

    # If message is voice
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

            AudioSegment.from_file(oganame).export(f'voice_{user_id}.wav', format='wav')

            g = sr.Recognizer()
            with sr.AudioFile(wavname) as source:
                audio = g.record(source)  # read the entire voice file
            try:
                au_to_text = g.recognize_google(audio, language='ru')
            except sr.UnknownValueError:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text='Речь неразборчива! Повторите запрос!')
                return None
            except sr.RequestError as e:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'Ошибка связи: {e}! Повторите запрос!')
                return None
            from_voice_flag = True

            os.remove(oganame)
            os.remove(wavname)
    # <

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    now_day = now[:-6]

    f = open('data_users.pkl', 'r+b')
    prtl.lock(f, prtl.LOCK_EX)
    data_users = pickle.load(f)  # Get users

    ind = 0
    try:
        ind = data_users['row_user_id'].index(user_id)
    except ValueError:  # if user new
        data_users['row_user_id'].append(user_id)
        data_users['row_name'].append(username)
        data_users['row_count_query'].append(1)
        data_users['row_count_tokens'].append(0)
        data_users['row_query_limit'].append(0)
        data_users['last_enter'].append(now_day)
        data_users['history'].append('no')
        store_hys = 'no'
        flag_new_user = True
    else:
        store_hys = data_users['history'][ind]
        data_users['row_count_query'][ind] += 1
        if data_users['row_query_limit'][ind] >= config.query_lim_at_day and now_day in data_users['last_enter'][
            ind]:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='DemmiatBot: Вы исчерпали дневной лимит запросов! '
                                                'Приходите завтра!')
            return None
        elif now_day not in data_users['last_enter'][ind]:
            data_users['row_query_limit'][ind] = 0
        data_users['last_enter'][ind] = now_day
        data_users['row_query_limit'][ind] += 1
        flag_new_user = False

    # History communication Log Reading
    hys_responce = []
    if store_hys == 'yes':
        try:
            uh = open(fr'{cwd}/hys/{user_id}.pkl', 'rb')
            hys_responce = pickle.load(uh)
            uh.close()
        except IOError:
            pass
            # open(fr'{cwd}/hys/{user_id}.pkl', 'wb').close()
    # <

    # OpenAI Answer
    mess = au_to_text if from_voice_flag else update.message.text
    hys_responce.append('User: ' + mess)
    context_diag = ''.join(hys_responce)
    completion = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'user', 'content': context_diag}
        ],
        temperature=0
    )
    result_regexp = re.sub('.+:', '', completion['choices'][0]['message']['content'], count=1)  # cut ~ 'Bot:'
    # <

    find_code = re.search('```|#', result_regexp)
    if find_code:
        itog_anws = f'<code>{result_regexp}</code>'
    else:
        itog_anws = result_regexp
    if store_hys == 'yes':
        await context.bot.send_message(chat_id=update.effective_chat.id, text=itog_anws, parse_mode='HTML',
                                       reply_markup=keyboard_clean)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=itog_anws, parse_mode='HTML')

    # History communication Log writing
    if store_hys == 'yes':
        uh = open(f'{cwd}/hys/{user_id}.pkl', 'wb')
        if len(hys_responce) > 20: del hys_responce[:2]
        hys_responce.append('Bot: ' + result_regexp)
        pickle.dump(hys_responce, uh)
        uh.close()
    # <

    # Log Users Data
    if completion['choices'][0]['message']['content']:
        tokens_used = completion['usage']['total_tokens']
        if not flag_new_user:
            data_users['row_count_tokens'][ind] += tokens_used
        else:
            data_users['row_count_tokens'].append(tokens_used)
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

    f = open('data_users.pkl', 'r+b')
    prtl.lock(f, prtl.LOCK_EX)
    data_users = pickle.load(f)
    if user_id not in data_users:  # if user new
        data_users[user_id] = {'name': username, 'count_query': 1, 'query_limit': 0, 'count_tokens': 0,
                               'last_enter': now_day, 'history': 'no'}
        f.seek(0)
        pickle.dump(data_users, f)
        f.flush()
    prtl.unlock(f)
    f.close()
        # try:
    #     ind = data_users['row_user_id'].index(user_id)
    # except ValueError:  # if user new
    #     data_users['row_user_id'].append(user_id)
    #     data_users['row_name'].append(username)
    #     data_users['row_count_query'].append(1)
    #     data_users['row_query_limit'].append(0)
    #     data_users['row_count_tokens'].append(0)
    #     data_users['last_enter'].append(now_day)
    #     data_users['history'].append('no')
    #     ind = data_users['row_user_id'].index(user_id)
    #     f = open('data_users.pkl', 'r+b')
    #     prtl.lock(f, prtl.LOCK_EX)
    #     pickle.dump(data_users, f)
    #     f.flush()
    #     prtl.unlock(f)
    #     f.close()
    repl = cap.format(config.query_lim_at_day, data_users[user_id]['history'])
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open('dembot.jpg', 'rb'),
                                 caption=repl, reply_markup=keyboard_start, parse_mode='HTML')


async def button_handler(update, context):
    query = update.callback_query
    button_data = query.data
    user_id = update.effective_user.id
    if button_data == 'memory':
        f = open('data_users.pkl', 'r+b')
        prtl.lock(f, prtl.LOCK_EX)
        data_users = pickle.load(f)
        ind = data_users['row_user_id'].index(user_id)
        store_hys = data_users['history'][ind]
        if store_hys == 'yes':
            data_users['history'][ind] = 'no'
            txt = 'Робот отключил свою память!'
        else:
            data_users['history'][ind] = 'yes'
            txt = 'Память робота включена!'
        f.seek(0)
        pickle.dump(data_users, f)
        f.flush()
        prtl.unlock(f)
        f.close()
        repl = cap.format(config.query_lim_at_day, data_users['history'][ind])
        await context.bot.answer_callback_query(update.callback_query.id, text=txt, show_alert=False)
        try:
            await context.bot.edit_message_caption(chat_id=update.effective_chat.id,
                                                   message_id=query.message.message_id,
                                                   caption=repl, reply_markup=keyboard_start)
        except:
            await context.bot.answer_callback_query(update.callback_query.id, text='Ошибка запроса смены сообщения!',
                                                    show_alert=False)
    elif button_data == 'clean_dialog':
        if os.path.exists(f'{cwd}/hys/{user_id}.pkl'):
            os.remove(f'{cwd}/hys/{user_id}.pkl')
            await context.bot.answer_callback_query(update.callback_query.id,
                                                    text='Контекст общения с роботом удалён!', show_alert=False)
        else:
            await context.bot.answer_callback_query(update.callback_query.id,
                                                    text='Контекст общения с роботом отсутствует!', show_alert=False)


async def info(update, context):
    f = open('data_users.pkl', 'rb')
    prtl.lock(f, prtl.LOCK_SH)
    data_users = pickle.load(f)
    prtl.unlock(f)
    f.close()
    user_id = update.effective_user.id
    try:
        ind = data_users['row_user_id'].index(user_id)
        usage = data_users['row_query_limit'][ind]
    except ValueError:
        usage = 0
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'Отправленных запросов {usage} из {config.query_lim_at_day}')


async def mtu(update, context):
    if getattr(update.message, 'text', None):
        match = re.match(r'/mtu i(-*\d+)[ \t]*(.+)', update.message.text)
        match_all = re.match('/mtu ([^d|u].+)', update.message.text)
        dw = True if '/mtu d' in update.message.text else False
        up = True if '/mtu u' in update.message.text else False
        if match:
            try:
                await context.bot.send_message(chat_id=match.group(1), text=match.group(2))
            except:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'Не удалось связаться с {match.group(1)}')
            return None
        elif match_all or dw or up:
            mess_to_users = ''
            if match_all:
                mess_to_users = match_all.group(1)
            elif dw:
                mess_to_users = 'Я готовлюсь отключиться для профилактики. При включении сообщу!'
            elif up:
                mess_to_users = 'Протокол включения выполнен! Готов к обслуживанию!'
            now_data = dt.datetime.now()
            f = open('data_users.pkl', 'r+b')
            prtl.lock(f, prtl.LOCK_EX)
            data_users = pickle.load(f)
            for usr_id in data_users['row_user_id'].copy():
                i = data_users['row_user_id'].index(usr_id)
                usr_dt = dt.datetime.strptime(data_users['last_enter'][i], '%Y-%m-%d')
                t_delta = now_data - usr_dt
                if t_delta.days > 15:  # if user long time ago have chat with bot, del user
                    await context.bot.send_message(chat_id=update.effective_chat.id,
                                                   text=f"Удален из-за старости {usr_id} -> {data_users['row_name'][i]}")
                    try:
                        os.remove(fr'{cwd}/hys/{usr_id}.pkl')  # Del history with Bot
                    except Exception as e:
                        await context.bot.send_message(chat_id=update.effective_chat.id,
                                                       text=f'Не удалось удалить {usr_id}.pkl: {e}')
                else:
                    try:
                        await context.bot.send_message(chat_id=usr_id, text=f'DemmiatBot: {mess_to_users}')
                    except:
                        await context.bot.send_message(chat_id=update.effective_chat.id,
                                                       text=f'Не удалось связаться с {usr_id}')
                for key in data_users:
                    del data_users[key][i]
            f.seek(0)
            pickle.dump(data_users, f)
            f.flush()
            prtl.unlock(f)
            f.close()


async def recalc(update, context):
    now_data = dt.datetime.now()
    f = open('data_users.pkl', 'r+b')
    prtl.lock(f, prtl.LOCK_EX)
    data_users = pickle.load(f)
    count_del = 0
    for usr_id in data_users['row_user_id'].copy():
        i = data_users['row_user_id'].index(usr_id)
        usr_dt = dt.datetime.strptime(data_users['last_enter'][i], '%Y-%m-%d')
        t_delta = now_data - usr_dt
        if t_delta.days > 15:  # if user long time ago have chat with bot, del user
            count_del += 1
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"Удален из-за старости {usr_id} -> {data_users['row_name'][i]}")
            try:
                os.remove(fr'{cwd}/hys/{usr_id}.pkl')  # Del history with Bot
            except Exception as e:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f'Не удалось удалить {usr_id}.pkl: {e}')
            for key in data_users:
                del data_users[key][i]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"Удалено: {count_del}, активных: {len(data_users['row_user_id'])}")
    f.seek(0)
    pickle.dump(data_users, f)
    f.flush()
    prtl.unlock(f)
    f.close()


async def mir(update, context):
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open('unknowability.pdf', 'rb'))


async def rel(update, context):
    importlib.reload(config)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text='Config перезагружен!')


async def nofu(update, context):
    f = open('data_users.pkl', 'rb')
    prtl.lock(f, prtl.LOCK_SH)
    data_users = pickle.load(f)
    prtl.unlock(f)
    f.close()
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"Пользователей робота: {len(data_users['row_user_id'])}")


if __name__ == '__main__':
    if not os.path.exists('data_users.pkl'):  # if not exist file, create!
        fdu = open('data_users.pkl', 'wb')
        # pickle.dump(dict(row_user_id=[], row_name=[], row_count_query=[],
        #                  row_count_tokens=[], row_query_limit=[], last_enter=[], history=[]), fdu)
        pickle.dump(dict(), fdu)
        fdu.close()

    cwd = os.getcwd()

    cap = '''Привет! Я Demmiat бот-ретранслятор (ver 3 on GPT-3.5-turbo) 
генеративного предварительно обученного преобразователя (GPT).
Мой внешний вид сформирован искусственной нейротической сетью.

Дневной лимит запросов: {0}
Память робота включена: <b>{1}</b>

/info - вывод технической информации.
/mir - отдать статью создателя о непознаваемом Мире и человеке в нём!'''

    openai.api_base = 'https://api.theb.ai/v1'
    openai.api_key = config.bai_token
    TOKEN = config.bot_token
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

    # Создаем обработчик текстовых сообщений,которые будут поступать в функцию quest()
    # Говорим обработчику MessageHandler: если увидишь текстовое сообщение
    # (фильтр `Filters.text`) и это будет не команда
    # (фильтр ~Filters.command), то вызови функцию quest()
    quest_handler = MessageHandler((filters.TEXT | filters.VOICE) & (~filters.COMMAND), quest)

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
        [telegram.InlineKeyboardButton('Память робота', callback_data='memory')]
    ]
    keyboard_start = telegram.InlineKeyboardMarkup(button_list_start)

    button_list_clean = [
        [telegram.InlineKeyboardButton('Очистить диалог с роботом', callback_data='clean_dialog')]
    ]
    keyboard_clean = telegram.InlineKeyboardMarkup(button_list_clean)

    button_list_channel = [
        [telegram.InlineKeyboardButton("АНКА ПАРТИZАНКА", url='https://t.me/anka_partizanka1010')]
    ]
    keyboard_anka = telegram.InlineKeyboardMarkup(button_list_channel)
    # <

    # Запускаем приложение, слушаем серверы Телеграмм
    application.run_polling()
