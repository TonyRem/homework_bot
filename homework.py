import os
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
import logging
import logging.handlers
import requests
import telegram

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Проверяет переменные окружения, необходимые для работы программы."""
    required_tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    if not all(required_tokens):
        logging.critical(
            "Отсутствует обязательная переменная окружения: '{token}'"
        )
        sys.exit("Программа принудительно остановлена.")


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    logger = logging.getLogger()

    try:
        logger.debug(f"Бот готовится отправить сообщение: {message}")
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f"Бот отправил сообщение: {message}")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")


def get_api_answer(timestamp):
    """Делает запрос к API-сервису для получения ответа."""
    params = {"from_date": timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            error_message = (
                f"Ошибка при запросе к эндпоинту {ENDPOINT}. "
                f"Код ответа: {response.status_code}. "
                f"Параметры запроса: {params}"
            )
            raise Exception(error_message)
    except Exception as e:
        raise Exception(f"Сбой при запросе к эндпоинту {ENDPOINT}: {e}")


def check_response(response):
    """Проверяет и возвращает последнюю работу из ответа API."""
    if not isinstance(response["homeworks"], list):
            raise TypeError(
            "Данные о работах должны быть представлены в виде списка"
        )
    try:
        homeworks = response["homeworks"]
        last_homework = homeworks[0]
    except KeyError:
        raise Exception("Отсутствует ожидаемый ключ 'homeworks' в ответе API")
    except IndexError:
        raise Exception("Список работ пуст")
    return last_homework


def parse_status(homework):
    """Извлекает статус работы из информации о домашней работе."""
    try:
        status = homework["status"]
        homework_name = homework["homework_name"]
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise Exception(
            "Отсутствуют ожидаемые ключи 'status' или 'id' в ответе API"
        )
    except Exception as e:
        raise Exception(f"Обнаружена ошибка при обработке статуса работы: {e}")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    formatter = logging.Formatter(log_format)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_status_message = None

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            last_homework = check_response(api_answer)
            status_message = parse_status(last_homework)

            if status_message != last_status_message:
                send_message(bot, status_message)
                last_status_message = status_message
            else:
                logger.debug("Отсутствуют новые статусы работы")

            time.sleep(RETRY_PERIOD)

        except Exception as e:
            message = f"Сбой в работе программы: {e}"
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
