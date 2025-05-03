import os

import pandas as pd

from src.reports import get_spending_by_category
from src.services import analyze_cashback_categories
from src.views import generate_response, load_data

CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")
PATH_FILE = os.getenv("PATH_FILE")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
SETTINGS_PATH = os.getenv("SETTINGS_PATH")


def main():
    """Основная функция выполнения"""
    df = load_data(PATH_FILE)
    input_time = "2023-05-15 14:30:00"
    json_response = generate_response(input_time, df)
    print(json_response)

    path_file = PATH_FILE

    df = pd.read_excel(path_file)
    df = df[df["Статус"] == "OK"]

    print("Отчет по категории 'Переводы':")
    result1 = get_spending_by_category(df, "Переводы")
    print(result1)

    print("\nОтчет по категории 'Каршеринг':")
    result2 = get_spending_by_category(df, "Каршеринг", "2021-12-31")
    print(result2)

    year = 2021
    month = 10

    result = analyze_cashback_categories(path_file, year, month)
    print(result)


if __name__ == "__main__":
    main()
