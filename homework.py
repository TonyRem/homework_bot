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
    required_tokens = ["PRACTICUM_TOKEN", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
    for token in required_tokens:
        if not os.getenv(token):
            logging.critical("Отсутствует обязательная переменная окружения: '{token}'")
            sys.exit("Программа принудительно остановлена.")


def send_message(bot, message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f"Бот отправил сообщение: {message}")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения в Telegram: {e}")


def get_api_answer(timestamp):
    params = {"from_date": timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        return response.json()
    except Exception as e:
        logging.error(f"Сбой при запросе к эндпоинту {ENDPOINT}: {e}")
        return None


def check_response(response):
    if "homeworks" not in response:
        logging.error("Отсутствует ожидаемый ключ 'homeworks' в ответе API")
        return None
    return response["homeworks"]


def parse_status(homework):
    if "status" not in homework or "id" not in homework:
        logging.error("Отсутствуют ожидаемые ключи 'status' или 'id' в ответе API")
        return None
    status = homework["status"]
    homework_name = homework["id"]
    if status not in HOMEWORK_VERDICTS:
        logging.error(f"Обнаружен неожиданный статус работы: {status}")
        return None
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            if api_answer is None:
                time.sleep(5)
                continue

            homeworks = check_response(api_answer)
            if homeworks is None:
                time.sleep(5)
                continue

            if homeworks:
                for homework in homeworks:
                    status_text = parse_status(homework)
                    if status_text:
                        send_message(bot, status_text)
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
