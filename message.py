FRONTIER_ERROR = 'Произошла ошибка: {e}'
NO_ENVS = 'Отсутствуют следующие переменные окружения: {envs}'
SUBSCRIBE_MESSAGE = (
    'Для доступа к боту необходимо подписаться на телеграмм-канал!'
)
AUTH_TOKEN_REQUESTED = 'Пытаемся получить новый access_token!..'
STORE_HYS_YES = 'ДА'
STORE_HYS_NO = 'НЕТ'
OPEN_FL_ERROR = 'Не удалось открыть файл истории: {e}'
UNKNOWN_STYPE = 'Неизвестный тип отправки пользователю: {stype}'
NO_SPEECH = 'Речь неразборчива! Повторите запрос!'
CONNECT_ERROR = 'Ошибка связи: {e}! Повторите запрос!'
BAD_CONNECTION = (
    'Нет соединения с эндпоинтом: {url}, {headers}, {data}. '
    'Ошибка исключения: {exc_error}.'
)
BAD_HTTP_STATUS = (
    'Проблема для {url}, {headers}, {data}: status code: {status_code}.'
)
MESSAGE_WAS_SENT = 'Сообщение отправлено в {chat_id}.'
BAD_SEND_MESSAGE = (
    'Невозможно отправить сообщение в чат {chat_id}! Ошибка: {exc_error}.'
)

START_LOG_MESSAGE = 'Робот начинает работу...'
LIM_AT_DAY = 'DemmiatBot: Вы исчерпали дневной лимит запросов!'
BOT_OFF_MEMORY = 'Робот отключил свою память!'
BOT_ON_MEMORY = 'Память робота включена!'
NO_BOT_CONTEXT = 'Контекст общения с роботом отсутствует!'
DEL_BOT_CONTEXT = 'Контекст общения с роботом удалён!'
BOT_TO_OFFLINE = (
    'DemmiatBot: Отключён для профилактики. При включении сообщу!'
)
BOT_ONLINE = 'DemmiatBot: Протокол включения выполнен! Готов к обслуживанию!'
BOT_TO_USERS = 'DemmiatBot: {mess_to_users}'
NO_BOT_CONTEXT = 'Контекст общения с роботом отсутствует!'

TO_EDIT_ERROR = 'Ошибка запроса на редактирование сообщения!'
HOW_MANY_REQUESTS = 'Отправленных запросов {how_req} из {lim_at_day}'

NO_USER_CONNECT = 'Не удалось связаться с {user_id}'
DEL_OLD_USER = 'Удален из-за старости {usr_id} -> {name}'
REMAKING_USERS = 'Пользователей удалено: {count_del}, активных: {num_of_users}'
HOW_MANY_USERS = 'Пользователей робота: {num_of_users}'

CONF_RELOAD = 'Config перезагружен!'

CAP = '''Привет, <b>{name}</b>! Я Demmiat бот-ретранслятор
генеративного предварительно обученного преобразователя (GPT).
Мой внешний вид сформирован искусственной нейротической сетью.

Дневной лимит запросов: {lim_at_day}
Память робота включена: <b>{bot_on_mem}</b>

/info - вывод технической информации.'''
