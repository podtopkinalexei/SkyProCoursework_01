import json
import os
import time
from datetime import datetime
from tempfile import NamedTemporaryFile

import pandas as pd
import pytest

from src.services import analyze_cashback_categories


@pytest.fixture
def sample_data_file():
    """Фикстура создает временный Excel-файл с тестовыми данными"""
    data = {
        "Дата операции": [
            "01.12.2021 12:00:00",
            "15.12.2021 18:30:00",
            "03.01.2022 09:15:00",
            "invalid_date",
        ],
        "Статус": ["OK", "OK", "FAILED", "OK"],
        "Кэшбэк": [100, 50, 200, "invalid"],
        "Категория": ["Супермаркеты", "АЗС", "Рестораны", "Такси"],
    }

    df = pd.DataFrame(data)

    # Создаем временный файл с уникальным именем
    temp_path = os.path.join(
        os.getenv("TEMP", os.path.dirname(__file__)), f"test_data_{os.getpid()}.xlsx"
    )
    df.to_excel(temp_path, index=False)

    yield temp_path

    # Даем системе время освободить файл
    time.sleep(0.1)
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    except PermissionError:
        pass  # Игнорируем ошибку, если файл все еще заблокирован


@pytest.fixture
def empty_data_file():
    """Фикстура создает пустой Excel-файл"""
    temp_path = os.path.join(
        os.getenv("TEMP", os.path.dirname(__file__)), f"empty_data_{os.getpid()}.xlsx"
    )
    pd.DataFrame().to_excel(temp_path)

    yield temp_path

    time.sleep(0.1)
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    except PermissionError:
        pass


def test_successful_analysis(sample_data_file):
    """Тест успешного анализа данных"""
    result = analyze_cashback_categories(sample_data_file, 2021, 12)
    data = json.loads(result)

    assert isinstance(data, dict)
    assert len(data) == 2
    assert "Супермаркеты" in data
    assert data["Супермаркеты"] == 100
    assert data["АЗС"] == 50


def test_no_data_for_period(sample_data_file):
    """Тест случая, когда нет данных за указанный период"""
    result = analyze_cashback_categories(sample_data_file, 2022, 1)
    data = json.loads(result)

    assert data == {}


def test_invalid_dates_handling(sample_data_file):
    """Тест обработки некорректных дат"""
    result = analyze_cashback_categories(sample_data_file, 2021, 12)
    data = json.loads(result)

    assert len(data) == 2


def test_empty_file(empty_data_file):
    """Тест обработки пустого файла"""
    result = analyze_cashback_categories(empty_data_file, 2021, 12)
    data = json.loads(result)

    assert "error" in data
    assert "Отсутствуют обязательные столбцы" in data["error"]


def test_missing_columns():
    """Тест обработки отсутствия обязательных столбцов"""

    temp_path = os.path.join(
        os.getenv("TEMP", os.path.dirname(__file__)), f"missing_cols_{os.getpid()}.xlsx"
    )
    pd.DataFrame({"Column1": [1, 2], "Column2": [3, 4]}).to_excel(temp_path)

    result = analyze_cashback_categories(temp_path, 2021, 12)

    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    except PermissionError:
        pass

    data = json.loads(result)
    assert "error" in data
    assert "Отсутствуют обязательные столбцы" in data["error"]


def test_file_not_found():
    """Тест обработки случая, когда файл не существует"""
    result = analyze_cashback_categories("nonexistent_file.xlsx", 2021, 12)
    data = json.loads(result)

    assert "error" in data
    assert "не найден" in data["error"]


def test_invalid_cashback_values(sample_data_file):
    """Тест обработки некорректных значений кэшбэка"""
    result = analyze_cashback_categories(sample_data_file, 2021, 12)
    data = json.loads(result)

    assert "Такси" not in data
