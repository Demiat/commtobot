# О Проекте

@DemmiatBot (ver. 1.0) - это ретранслятор запросов к нейросети в системе телеграмм.

## Доступный функционал

Что умеет бот:
- Ретранслирует ваши запросы к API GPT.
- Ведёт базу данных своих пользователей в словаре, сохраняя его средствами модуля pickle.
- Хранит для каждого пользователя историю общения с GPT, опционально
подставляя её в контекст общения.
- По команде динамически перегружает модуль файла настроек.
- По команде пересчитывает активных пользователей и удаляет старых.
- Принимает запросы в голосовом виде
- Принимает в качестве ответа от ИИ изображения

# Развёртывание проекта

Внимание! Проект работает с версией Python 3.10+

1) Склонировать репозиторий:
```git clone git@github.com:Demiat/commtobot.git```

2) Создать виртуальное окружение: 
```
cd <ваша_папка>/
python -m venv venv
```

3) Активировать виртуальное окружение:
- для linux ```source venv/bin/activate```
- для windows ```source venv/Scripts/activate```

4) Установить зависимости: 
```pip install -r requirements.txt```

5) Установить ffmpeg в систему, если её нет:
```sudo apt install ffmpeg```

6) Установить доверенный сертификат
```
curl -k "https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer" -w "\n" >> $(python -m certifi)
```

7) Создать и заполнить файл .env:
- DEMIAT_BOT_ID = <id вашего бота>
- DEMIAT_BOT_TOKEN = <token вашего бота>
- MY_TELEGRAM_ID = <id вашей учетки телеграм>
- SBER_AUTH_TOKEN = <токен от СБЕРА>
- RqUID = <уникальный идентификатор запроса для СБЕРА>

Ключ авторизации SBER_AUTH_TOKEN получается в личном кабинете Gigachat API
и передается в запросе на получение Access token

8) Запуск:
```python bot.py```


Автор: [Тарасов Дмитрий](https://github.com/Demiat)
