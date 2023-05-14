import os
import time
import requests
import logging
import telegram
import sys
from dotenv import load_dotenv

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
    required_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(required_tokens):
        logging.critical("Отсутствует обязательная переменная окружения: '{token}'")
        sys.exit("Программа принудительно остановлена.")


def send_message(bot, message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f"Бот отправил сообщение: {message}")
    except Exception as e:
        # logging.error(f"Ошибка при отправке сообщения в Telegram: {e}")
        raise Exception(f"Ошибка при отправке сообщения в Telegram: {e}")


def get_api_answer(timestamp):
    params = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        return response.json()
    except Exception as e:
        # logging.error(f"Сбой при запросе к эндпоинту {ENDPOINT}: {e}")
        raise Exception(f"Сбой при запросе к эндпоинту {ENDPOINT}: {e}")


def check_response(response):
    try:
        last_homework = response["homeworks"][0]
    except KeyError:
        # logging.error("Отсутствует ожидаемый ключ 'homeworks' в ответе API")
        raise Exception("Отсутствует ожидаемый ключ 'homeworks' в ответе API")
    return last_homework


def parse_status(homework):
    try:
        status = homework["status"]
        homework_name = homework["homework_name"]
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        # logging.error("Отсутствуют ожидаемые ключи 'status' или 'id' в ответе API")
        raise Exception("Отсутствуют ожидаемые ключи 'status' или 'id' в ответе API")
    except Exception as e:
        # logging.error(f"Обнаружена ошибка при обработке статуса работы: {e}")
        raise Exception(f"Обнаружена ошибка при обработке статуса работы: {e}")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_response = None

    while True:
        try:
            api_answer = get_api_answer(timestamp)

            if api_answer != last_response:
                last_response = api_answer
                last_homework = check_response(api_answer)
                status_message = parse_status(last_homework)
                send_message(bot, status_message)
            else:
                logging.debug("Отсутствуют новые статусы работы")

            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logging.error(message)
            send_message(bot, message)
            time.sleep(5)


if __name__ == "__main__":
    main()
