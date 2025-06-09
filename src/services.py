import json
import logging
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


def setup_logging():
    """Функция настройки логирования"""

    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "services.logs"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # вывод в консоль
            logging.FileHandler(log_file),  # запись в файл
        ],
    )
    return logging.getLogger(__name__)


logger = setup_logging()
load_dotenv(override=True)


def analyze_cashback_categories(path_file: str, year: int, month: int) -> str:
    """Анализирует категории кэшбэка за указанный месяц и год и возвращает JSON-строку с категориями и суммами кэшбэка"""
    try:
        logger.info(f"Начало анализа кэшбэка за {month}.{year}")

        # Проверка существования файла
        if not os.path.exists(path_file):
            error_msg = f"Файл {path_file} не найден"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Чтение файла: {path_file}")
        df = pd.read_excel(path_file)
        logger.debug(f"Прочитано {len(df)} строк")

        # Проверка наличия необходимых столбцов
        required_columns = ["Дата операции", "Статус", "Кэшбэк", "Категория"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = (
                f"Отсутствуют обязательные столбцы: {', '.join(missing_columns)}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Преобразование даты
        logger.info("Преобразование дат...")
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"], dayfirst=True, errors="coerce"
        )

        # Удаление строк с некорректными датами
        initial_count = len(df)
        df = df[df["Дата операции"].notna()]
        removed_count = initial_count - len(df)
        if removed_count > 0:
            logger.warning(f"Удалено {removed_count} строк с некорректными датами")

        # Обработка кэшбэка
        logger.info("Проверка данных кэшбэка...")
        df = df[df["Кэшбэк"].notna()]
        df["Кэшбэк"] = pd.to_numeric(df["Кэшбэк"], errors="coerce")
        df = df[df["Кэшбэк"].notna()]

        # Фильтрация данных
        logger.info(f"Фильтрация данных за {month}.{year}...")
        filtered_df = df[
            (df["Дата операции"].dt.year == year)
            & (df["Дата операции"].dt.month == month)
            & (df["Статус"].str.strip().str.upper() == "OK")
        ]

        if filtered_df.empty:
            logger.warning(f"Нет данных за указанный период {month}.{year}")
            return json.dumps({}, ensure_ascii=False, indent=4)

        # Анализ кэшбэка
        logger.info("Анализ кэшбэка...")
        cashback_df = filtered_df[filtered_df["Кэшбэк"] > 0]

        if cashback_df.empty:
            logger.warning("Нет операций с кэшбэком в указанный период")
            return json.dumps({}, ensure_ascii=False, indent=4)

        result = cashback_df.groupby("Категория")["Кэшбэк"].sum()
        sorted_result = result.sort_values(ascending=False).to_dict()

        logger.info(
            f"Анализ завершен. Найдено {len(sorted_result)} категорий с кэшбэком"
        )
        return json.dumps(sorted_result, ensure_ascii=False, indent=4)

    except FileNotFoundError as e:
        logger.error(str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except ValueError as e:
        logger.error(f"Ошибка в данных: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except pd.errors.EmptyDataError:
        logger.error("Файл не содержит данных")
        return json.dumps({"error": "Файл не содержит данных"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        return json.dumps({"error": "Внутренняя ошибка сервера"}, ensure_ascii=False)


if __name__ == "__main__":
    # Пример использования
    path_file = "../data/operations.xlsx"
    year = 2021
    month = 10

    logger.info(f"Запуск анализа кэшбэка за {month}.{year}")
    result = analyze_cashback_categories(path_file, year, month)
    print(result)
    logger.info("Программа завершена")
