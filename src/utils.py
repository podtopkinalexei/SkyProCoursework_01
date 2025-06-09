import json
import logging
import os
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
