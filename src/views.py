import json
from datetime import datetime
from typing import Dict, List

import pandas as pd

from src.utils import get_currency_rate, format_currency_rates, get_stock_prices, load_data, logger, Config


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
