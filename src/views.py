import json
import logging
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv


def setup_logging():
    """Настраивает логирование в терминал и файл"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Форматтер для логов
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик для терминала
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Обработчик для файла
    file_handler = logging.FileHandler(filename=log_dir / "views.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Добавляем обработчики
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()

load_dotenv(override=True)


class Config:
    CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")
    PATH_FILE = os.getenv("PATH_FILE")
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    SETTINGS_PATH = os.getenv("SETTINGS_PATH")


@lru_cache(maxsize=1)
def load_user_settings() -> Dict:
    """Загружает пользовательские настройки из JSON-файла"""
    try:
        with open(Config.SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
            logger.info("Настройки пользователя успешно загружены")
            return settings
    except FileNotFoundError:
        logger.warning(
            f"Файл настроек {Config.SETTINGS_PATH} не найден. Используются настройки по умолчанию."
        )
        return {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
        }
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка чтения файла {Config.SETTINGS_PATH}: {str(e)}")
        return {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
        }


def load_data(file_path: str) -> pd.DataFrame:
    """Загружает данные из Excel файла"""
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Данные успешно загружены из {file_path}")
        return df
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {str(e)}")
        raise


def get_stock_prices() -> List[Dict[str, float]]:
    """Получает текущие цены акций через Alpha Vantage API"""
    if not Config.ALPHA_VANTAGE_API_KEY:
        logger.error("API ключ для Alpha Vantage не найден")
        raise ValueError("API ключ для Alpha Vantage не найден")

    try:
        user_settings = load_user_settings()
        symbols = user_settings.get(
            "user_stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
        )
        stock_prices = []

        for symbol in symbols:
            try:
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={Config.ALPHA_VANTAGE_API_KEY}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                if "Global Quote" in data:
                    price = float(data["Global Quote"]["05. price"])
                    stock_prices.append({"stock": symbol, "price": round(price, 2)})
                    logger.debug(f"Успешно получена цена для {symbol}")
                else:
                    logger.warning(
                        f"Не удалось получить данные для {symbol}: {data.get('Note', 'Unknown error')}"
                    )
            except requests.exceptions.RequestException as e:
                logger.error(f"Ошибка сети при запросе цены акции {symbol}: {str(e)}")
            except Exception as e:
                logger.error(f"Ошибка при обработке данных для {symbol}: {str(e)}")

        return stock_prices
    except Exception as e:
        logger.error(f"Общая ошибка при получении цен акций: {str(e)}")
        return []


def get_currency_rate() -> Dict:
    """Получает курс валют с учетом пользовательских настроек"""
    try:
        user_settings = load_user_settings()
        currencies = user_settings.get("user_currencies", ["USD", "EUR"])

        if not Config.CURRENCY_API_KEY:
            logger.error("API ключ для курсов валют не найден")
            raise ValueError("API ключ для курсов валют не найден")

        symbols_param = "%2C".join(currencies)
        url = f"https://api.apilayer.com/exchangerates_data/latest?symbols={symbols_param}&base=RUB"

        response = requests.get(
            url, headers={"apikey": Config.CURRENCY_API_KEY}, timeout=10
        )
        response.raise_for_status()
        logger.info("Курсы валют успешно получены")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при получении курсов валют: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при получении курсов валют: {str(e)}")
    return {"rates": {}}


def format_currency_rates(api_data: Dict) -> List[Dict[str, float]]:
    """Форматирует данные о курсах валют"""
    try:
        user_settings = load_user_settings()
        currencies = user_settings.get("user_currencies", ["USD", "EUR"])
        rates = api_data.get("rates", {})

        formatted_rates = []
        for currency in currencies:
            rate = rates.get(currency, 1)
            formatted_rates.append(
                {"currency": currency, "rate": round(1 / rate, 2) if rate != 0 else 0.0}
            )

        logger.debug("Курсы валют успешно отформатированы")
        return formatted_rates
    except Exception as e:
        logger.error(f"Ошибка форматирования курсов валют: {str(e)}")
        return [{"currency": "USD", "rate": 73.21}, {"currency": "EUR", "rate": 87.08}]


def get_greeting(time_str: str) -> str:
    """Возвращает приветствие в зависимости от времени суток"""
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour

        if 5 <= hour < 12:
            return "Доброе утро"
        elif 12 <= hour < 17:
            return "Добрый день"
        elif 17 <= hour < 23:
            return "Добрый вечер"
        return "Доброй ночи"
    except ValueError as e:
        logger.error(f"Неверный формат времени: {time_str}. Ошибка: {str(e)}")
        return "Добрый день"


def process_cards_data(df: pd.DataFrame) -> List[Dict]:
    """Обрабатывает данные по картам"""
    try:
        df["last_digits"] = df["Номер карты"].str.extract(r"\*(\d{4})")
        cards_grouped = (
            df[df["Сумма операции"] < 0].groupby("last_digits")["Сумма операции"].sum()
        )

        cards_data = []
        for last_digits, total_spent in cards_grouped.items():
            cards_data.append(
                {
                    "last_digits": last_digits,
                    "total_spent": abs(round(total_spent, 2)),
                    "cashback": abs(round(total_spent / 100, 2)),
                }
            )

        logger.info(f"Обработано {len(cards_data)} карт")
        return cards_data
    except Exception as e:
        logger.error(f"Ошибка обработки данных карт: {str(e)}")
        return []


def process_top_transactions(df: pd.DataFrame, n: int = 5) -> List[Dict]:
    """Обрабатывает топ-N транзакций"""
    try:
        expenses_df = df[df["Сумма операции"] < 0].copy()
        expenses_df["date"] = pd.to_datetime(
            expenses_df["Дата операции"], format="%d.%m.%Y %H:%M:%S", dayfirst=True
        ).dt.strftime("%d.%m.%Y")

        top_transactions = expenses_df.nlargest(n, "Сумма операции", keep="all")
        transactions_list = []

        for _, row in top_transactions.iterrows():
            transactions_list.append(
                {
                    "date": row["date"],
                    "amount": abs(round(row["Сумма операции"], 2)),
                    "category": row["Категория"],
                    "description": row["Описание"],
                }
            )

        logger.info(f"Обработано {len(transactions_list)} транзакций")
        return transactions_list
    except Exception as e:
        logger.error(f"Ошибка обработки транзакций: {str(e)}")
        return []


def validate_datetime_format(time_str: str) -> bool:
    """Проверяет корректность формата времени"""
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        logger.error(f"Неверный формат времени: {time_str}")
        return False


def generate_response(date_time_str: str, df: pd.DataFrame) -> str:
    """Генерирует JSON-ответ"""
    if not validate_datetime_format(date_time_str):
        raise ValueError("Неверный формат даты")

    try:
        currency_api_data = get_currency_rate()
        currency_rates = format_currency_rates(currency_api_data)
        logger.info("Курсы валют успешно обработаны")
    except Exception as e:
        logger.error(f"Ошибка при обработке курсов валют: {str(e)}")
        currency_rates = [
            {"currency": "USD", "rate": 73.21},
            {"currency": "EUR", "rate": 87.08},
        ]

    try:
        cards_data = process_cards_data(df)
        top_transactions = process_top_transactions(df)
        stock_prices = get_stock_prices()

        response = {
            "greeting": get_greeting(date_time_str),
            "cards": cards_data,
            "top_transactions": top_transactions,
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
        }

        logger.info("Успешно сформирован ответ")
        return json.dumps(response, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка формирования ответа: {str(e)}")
        raise


def main():
    """Основная функция выполнения"""
    try:
        logger.info("Запуск приложения")
        df = load_data(Config.PATH_FILE)
        input_time = "2023-05-15 14:30:00"

        json_response = generate_response(input_time, df)
        print(json_response)
        logger.info("Приложение завершило работу успешно")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {str(e)}")
        raise


if __name__ == "__main__":
    main()
