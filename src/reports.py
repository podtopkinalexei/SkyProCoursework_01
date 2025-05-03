import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


def setup_logging():
    """Настройка логирования в терминал и файл"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "reports.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


logger = setup_logging()

load_dotenv(override=True)

default_filename = "../reports/report.json"
last_days = 90  # последние три месяца


def report_to_file(default_filename):
    """Декоратор для сохранения отчетов в файл"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(
                f"Вызов функции {func.__name__} с аргументами: {args}, {kwargs}"
            )

            try:
                # Вызываем оригинальную функцию
                result = func(*args, **kwargs)

                # Определяем имя файла
                output_filename = kwargs.get("filename", default_filename)
                if "{timestamp}" in output_filename:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = output_filename.format(timestamp=timestamp)

                # Сохраняем результат в файл
                with open(output_filename, "w", encoding="utf-8") as f:
                    if isinstance(result, (dict, list)):
                        json.dump(result, f, ensure_ascii=False, indent=4)
                    else:
                        f.write(str(result))

                logger.info(f"Отчет сохранен в файл: {output_filename}")
                logger.debug(
                    f"Результат отчета:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )
                return result

            except Exception as e:
                logger.error(
                    f"Ошибка в функции {func.__name__}: {str(e)}", exc_info=True
                )
                raise

        return wrapper

    return decorator


@report_to_file(default_filename)
def get_spending_by_category(
    transactions: pd.DataFrame,
    category: str,
    target_date: str = None,
) -> dict:
    """Анализирует траты по указанной категории за последние 3 месяца"""
    try:
        logger.info(f"Начало обработки категории: {category}")

        # Преобразуем target_date в datetime
        target_date = (
            datetime.now()
            if target_date is None
            else datetime.strptime(target_date, "%Y-%m-%d")
        )
        logger.debug(f"Целевая дата: {target_date}")

        # Проверяем необходимые колонки
        required_cols = ["Дата операции", "Категория", "Сумма операции"]
        if not all(col in transactions.columns for col in required_cols):
            missing = [col for col in required_cols if col not in transactions.columns]
            error_msg = f"Отсутствуют обязательные колонки: {', '.join(missing)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        df = transactions.copy()
        logger.debug(f"Получено {len(df)} транзакций для анализа")

        # Преобразуем даты
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"], dayfirst=True, errors="coerce"
        )
        df = df[df["Дата операции"].notna()]
        logger.debug(f"После фильтрации по дате осталось {len(df)} транзакций")

        # Фильтруем только расходы (отрицательные суммы)
        df = df[df["Сумма операции"] < 0].copy()
        df["Сумма операции"] = df["Сумма операции"].abs()
        logger.debug(f"Найдено {len(df)} расходных операций")

        # Нормализуем названия категорий
        df["Категория"] = df["Категория"].str.strip().str.lower()
        search_category = category.strip().lower()
        logger.debug(f"Поиск категории: '{search_category}'")

        # Фильтруем по категории
        category_transactions = df[df["Категория"] == search_category].copy()
        logger.debug(f"Найдено {len(category_transactions)} операций по категории")

        if category_transactions.empty:
            msg = f"Нет транзакций по категории '{category}'"
            logger.warning(msg)
            return {"message": msg}

        # Рассчитываем диапазон дат
        start_date = target_date - timedelta(days=last_days)
        logger.debug(f"Анализируем период с {start_date} по {target_date}")

        # Фильтруем по дате
        filtered = category_transactions[
            (category_transactions["Дата операции"] >= start_date)
            & (category_transactions["Дата операции"] <= target_date)
        ].copy()
        logger.debug(f"После фильтрации по дате осталось {len(filtered)} операций")

        if filtered.empty:
            msg = f"Нет транзакций по категории '{category}' за последние 3 месяца"
            logger.warning(msg)
            return {"message": msg}

        # Группируем по месяцам и суммируем
        filtered.loc[:, "Месяц"] = filtered["Дата операции"].dt.to_period("M")
        result = filtered.groupby("Месяц")["Сумма операции"].sum().to_dict()
        result = {str(k): round(v, 2) for k, v in result.items()}

        logger.info(f"Успешно сформирован отчет по категории '{category}'")
        logger.debug(f"Результат:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

        return result

    except Exception as e:
        logger.error(
            f"Ошибка при обработке категории '{category}': {str(e)}", exc_info=True
        )
        return {"error": str(e)}


if __name__ == "__main__":
    try:
        logger.info("Запуск анализа расходов")

        # Загрузка данных из файла
        path_file = "../data/operations.xlsx"
        logger.info(f"Загрузка данных из файла: {path_file}")

        df = pd.read_excel(path_file, sheet_name="Отчет по операциям")
        df = df[df["Статус"] == "OK"]
        logger.info(f"Загружено {len(df)} успешных операций")

        print("Отчет по категории 'Переводы':")
        result1 = get_spending_by_category(df, "Переводы")
        print(result1)

        print("\nОтчет по категории 'Каршеринг':")
        result2 = get_spending_by_category(
            df, "Каршеринг", "2021-12-31", filename="custom_transport_report.json"
        )
        print(result2)

        logger.info("Анализ завершен успешно")
    except Exception as e:
        logger.critical(
            f"Критическая ошибка при выполнении программы: {str(e)}", exc_info=True
        )
