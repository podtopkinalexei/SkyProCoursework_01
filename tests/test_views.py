from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.views import get_greeting, process_cards_data, process_top_transactions


# Тест на обычные случаи
@pytest.mark.parametrize(
    "time_str, expected",
    [
        ("2023-01-01 06:00:00", "Доброе утро"),
        ("2023-01-01 11:59:59", "Доброе утро"),
        ("2023-01-01 12:00:00", "Добрый день"),
        ("2023-01-01 16:59:59", "Добрый день"),
        ("2023-01-01 17:00:00", "Добрый вечер"),
        ("2023-01-01 22:59:59", "Добрый вечер"),
        ("2023-01-01 23:00:00", "Доброй ночи"),
        ("2023-01-01 04:59:59", "Доброй ночи"),
        ("2023-01-01 00:00:00", "Доброй ночи"),
    ],
)
def test_get_greeting_normal_cases(time_str, expected):
    """Тестирование стандартных случаев"""
    assert get_greeting(time_str) == expected


# Тест на обработку ошибок
def test_get_greeting_invalid_format(caplog):
    """Тестирование обработки неверного формата времени"""
    invalid_time = "неправильный формат"
    result = get_greeting(invalid_time)

    # Проверяем возвращаемое значение по умолчанию
    assert result == "Добрый день"


# Тест на граничные случаи времени
@pytest.mark.parametrize(
    "hour, expected",
    [
        (4, "Доброй ночи"),
        (5, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (16, "Добрый день"),
        (17, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
        (0, "Доброй ночи"),
    ],
)
def test_get_greeting_edge_cases(hour, expected):
    """Тестирование граничных случаев по часам"""
    time_str = f"2023-01-01 {hour:02d}:30:00"
    assert get_greeting(time_str) == expected


@pytest.fixture
def sample_dataframe():
    """Фикстура с тестовыми данными карт"""
    data = {
        "Номер карты": ["*1234", "*5678", "*1234", "*9012", "*5678", "*1234"],
        "Сумма операции": [-100.50, -200.75, -50.25, -300.00, -150.00, 100.00],
        "Категория": ["A", "B", "A", "C", "B", "D"],
    }
    return pd.DataFrame(data)


# Тест на нормальную работу
def test_process_cards_data_normal(sample_dataframe, caplog):
    """Тест нормальной обработки данных"""
    result = process_cards_data(sample_dataframe)

    # Проверяем структуру результата
    assert isinstance(result, list)
    assert len(result) == 3

    # Проверяем правильность расчета
    expected_results = {
        "1234": {"total": 150.75, "cashback": 1.51},
        "5678": {"total": 350.75, "cashback": 3.51},
        "9012": {"total": 300.00, "cashback": 3.00},
    }

    for card in result:
        expected = expected_results[card["last_digits"]]
        assert card["total_spent"] == pytest.approx(expected["total"])
        assert card["cashback"] == pytest.approx(expected["cashback"])


# Тест на пустые данные
def test_process_cards_data_empty():
    """Тест с пустым DataFrame"""
    empty_df = pd.DataFrame(columns=["Номер карты", "Сумма операции"])
    result = process_cards_data(empty_df)
    assert result == []


# Тест на отсутствие отрицательных операций
def test_process_cards_data_no_negative():
    """Тест когда нет отрицательных операций"""
    data = {"Номер карты": ["*1234", "*5678"], "Сумма операции": [100.50, 200.75]}
    df = pd.DataFrame(data)
    result = process_cards_data(df)
    assert result == []


# Тест на обработку ошибок
def test_process_cards_data_invalid(caplog):
    """Тест обработки невалидных данных"""
    invalid_df = pd.DataFrame(
        {"Номер карты": [1234, 5678], "Сумма операции": [-100, -200]}
    )

    result = process_cards_data(invalid_df)
    assert result == []


# Тест на граничные значения
def test_process_cards_data_edge_cases():
    """Тест граничных значений сумм"""
    data = {
        "Номер карты": ["*1234", "*1234", "*5678"],
        "Сумма операции": [-0.01, -999999.99, -1000000.00],
    }
    df = pd.DataFrame(data)
    result = process_cards_data(df)

    assert len(result) == 2
    for card in result:
        if card["last_digits"] == "1234":
            assert card["total_spent"] == pytest.approx(1000000.00)
            assert card["cashback"] == pytest.approx(10000.00)
        else:
            assert card["total_spent"] == pytest.approx(1000000.00)
            assert card["cashback"] == pytest.approx(10000.00)


# Тест на корректность округления
def test_process_cards_data_rounding():
    """Тест корректности округления сумм"""
    data = {"Номер карты": ["*1234", "*1234"], "Сумма операции": [-100.499, -100.501]}
    df = pd.DataFrame(data)
    result = process_cards_data(df)

    assert len(result) == 1
    assert result[0]["total_spent"] == pytest.approx(201.00)
    assert result[0]["cashback"] == pytest.approx(2.01)


# Тест на обработку None и NaN значений
def test_process_cards_data_missing_values():
    """Тест обработки пропущенных значений"""
    data = {
        "Номер карты": ["*1234", None, np.nan, "*5678"],
        "Сумма операции": [-100, -200, -300, None],
    }
    df = pd.DataFrame(data)
    result = process_cards_data(df)

    # Ожидаем что только валидные строки будут обработаны
    assert len(result) == 1
    assert result[0]["last_digits"] == "1234"
    assert result[0]["total_spent"] == pytest.approx(100.00)


@pytest.fixture
def sample_transactions():
    """Фикстура с тестовыми данными транзакций"""
    data = {
        "Дата операции": [
            "01.01.2023 10:00:00",
            "02.01.2023 15:30:00",
            "03.01.2023 09:15:00",
            "04.01.2023 12:45:00",
            "05.01.2023 18:20:00",
            "06.01.2023 11:10:00",
            "07.01.2023 14:05:00",
        ],
        "Сумма операции": [
            -1000.50,
            -200.75,
            -1500.25,
            -300.00,
            -500.00,
            100.00,
            -1200.00,
        ],
        "Категория": [
            "Супермаркет",
            "Кафе",
            "Техника",
            "АЗС",
            "Ресторан",
            "Зарплата",
            "Одежда",
        ],
        "Описание": [
            "Пятерочка",
            "Starbucks",
            "iPhone",
            "Лукойл",
            "Мясо & Рыба",
            "ЗП",
            "Zara",
        ],
    }
    return pd.DataFrame(data)


# Тест на формат даты
def test_date_formatting(sample_transactions):
    """Тест корректности форматирования даты"""
    result = process_top_transactions(sample_transactions)
    for transaction in result:
        try:
            datetime.strptime(transaction["date"], "%d.%m.%Y")
        except ValueError:
            pytest.fail(f"Неверный формат даты: {transaction['date']}")


# Тест на разное количество запрашиваемых транзакций
@pytest.mark.parametrize("n, expected_len", [(1, 1), (5, 5), (10, 6), (0, 0)])
def test_different_n_values(sample_transactions, n, expected_len):
    """Тест с разным количеством запрашиваемых транзакций"""
    result = process_top_transactions(sample_transactions, n=n)
    assert len(result) == expected_len


# Тест на пустые данные
def test_empty_dataframe():
    """Тест с пустым DataFrame"""
    empty_df = pd.DataFrame(
        columns=["Дата операции", "Сумма операции", "Категория", "Описание"]
    )
    result = process_top_transactions(empty_df)
    assert result == []


# Тест на отсутствие отрицательных операций
def test_no_negative_transactions():
    """Тест когда нет отрицательных операций"""
    data = {
        "Дата операции": ["01.01.2023 10:00:00", "02.01.2023 15:30:00"],
        "Сумма операции": [100.50, 200.75],
        "Категория": ["A", "B"],
        "Описание": ["Desc1", "Desc2"],
    }
    df = pd.DataFrame(data)
    result = process_top_transactions(df)
    assert result == []


# Тест на обработку ошибок в данных
def test_invalid_data(caplog):
    """Тест обработки невалидных данных"""
    invalid_df = pd.DataFrame(
        {
            "Дата операции": ["invalid_date", "02.01.2023 15:30:00"],
            "Сумма операции": [-100, -200],
            "Категория": ["A", "B"],
            "Описание": ["Desc1", "Desc2"],
        }
    )

    result = process_top_transactions(invalid_df)
    assert result == []


# Тест на корректность округления сумм
def test_amount_rounding():
    """Тест корректности округления сумм"""
    data = {
        "Дата операции": ["01.01.2023 10:00:00", "02.01.2023 15:30:00"],
        "Сумма операции": [-100.499, -100.501],
        "Категория": ["A", "B"],
        "Описание": ["Desc1", "Desc2"],
    }
    df = pd.DataFrame(data)
    result = process_top_transactions(df)

    assert result[0]["amount"] == pytest.approx(100.50)
    assert result[1]["amount"] == pytest.approx(100.50)
