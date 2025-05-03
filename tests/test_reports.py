from datetime import datetime, timedelta

import pandas as pd

from src.reports import get_spending_by_category


def test_get_spending_by_category_happy_path():
    """Тест успешного сценария с корректными данными"""

    data = {
        "Дата операции": [
            "01.01.2023",
            "15.01.2023",
            "01.02.2023",
            "15.02.2023",
            "01.03.2023",
        ],
        "Категория": ["продукты", "продукты", "транспорт", "продукты", "продукты"],
        "Сумма операции": [-1000, -500, -200, -800, -1200],
    }
    df = pd.DataFrame(data)

    result = get_spending_by_category(df, "продукты", "2023-03-01")

    # Проверки
    assert isinstance(result, dict)
    assert len(result) == 3
    assert result.get("2023-01") == 1500
    assert result.get("2023-02") == 800
    assert result.get("2023-03") == 1200


def test_get_spending_by_category_no_transactions():
    """Тест случая, когда нет транзакций по указанной категории"""
    data = {
        "Дата операции": ["01.01.2023", "15.01.2023"],
        "Категория": ["транспорт", "транспорт"],
        "Сумма операции": [-100, -200],
    }
    df = pd.DataFrame(data)

    result = get_spending_by_category(df, "продукты")

    assert "message" in result
    assert "нет транзакций" in result["message"].lower()


def test_get_spending_by_category_missing_columns():
    """Тест случая с отсутствующими обязательными колонками"""
    data = {"date": ["01.01.2023"], "category": ["продукты"], "amount": [-100]}
    df = pd.DataFrame(data)

    result = get_spending_by_category(df, "продукты")

    assert "error" in result
    assert "Отсутствуют обязательные колонки" in result["error"]


def test_get_spending_by_category_invalid_dates():
    """Тест обработки невалидных дат"""
    data = {
        "Дата операции": ["invalid_date", "01.01.2023"],
        "Категория": ["продукты", "продукты"],
        "Сумма операции": [-100, -200],
    }
    df = pd.DataFrame(data)

    result = get_spending_by_category(df, "продукты")

    assert isinstance(result, dict)
    assert len(result) >= 1


def test_get_spending_by_category_empty_dataframe():
    """Тест с пустым DataFrame"""
    df = pd.DataFrame(columns=["Дата операции", "Категория", "Сумма операции"])

    result = get_spending_by_category(df, "продукты")

    assert "message" in result
    assert "нет транзакций" in result["message"].lower()


def test_get_spending_by_category_date_filtering():
    """Тест корректности фильтрации по дате"""
    today = datetime.now()
    two_months_ago = (today - timedelta(days=60)).strftime("%d.%m.%Y")
    four_months_ago = (today - timedelta(days=120)).strftime("%d.%m.%Y")

    data = {
        "Дата операции": [two_months_ago, four_months_ago, today.strftime("%d.%m.%Y")],
        "Категория": ["продукты", "продукты", "продукты"],
        "Сумма операции": [-100, -200, -300],
    }
    df = pd.DataFrame(data)

    result = get_spending_by_category(df, "продукты")

    assert isinstance(result, dict)
    assert len(result) >= 1
    assert float(four_months_ago.split(".")[-1]) not in [
        int(k.split("-")[-1]) for k in result.keys()
    ]


def test_get_spending_by_category_positive_amounts_fixed_date():
    """Тест с фиксированной датой"""
    data = {
        "Дата операции": ["01.01.2023", "02.01.2023", "03.01.2023"],
        "Категория": ["продукты", "продукты", "продукты"],
        "Сумма операции": [-100, 200, -300],
    }
    df = pd.DataFrame(data)

    result = get_spending_by_category(df, "продукты", target_date="2023-02-01")

    assert isinstance(result, dict)
    assert result.get("2023-01") == 400
