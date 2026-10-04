import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SOURCE_FILE = PROJECT_DIR / "data" / "x5_results.xlsx"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

def create_period_names(header_rows: pd.DataFrame) -> list[str]:
    """Создаёт понятные названия столбцов с периодами."""
    period_names = []

    for column in header_rows.columns[2:]:
        period = header_rows.loc[4, column]
        correction = header_rows.loc[5, column]

        period_name = str(int(period)) if isinstance(period, float) and period.is_integer() else str(period)
        if pd.notna(correction):
            period_name = f"{period_name} Скорр."

        period_names.append(period_name)

    return period_names

def add_section_names(data: pd.DataFrame, period_columns: list[str]) -> pd.DataFrame:
    """Добавляет название раздела к каждому числовому показателю."""
    data = data.copy()
    data["Раздел"] = pd.NA

    current_section = pd.NA
    for index, row in data.iterrows():
        has_values = row[period_columns].notna().any()

        if not has_values:
            current_section = row["Показатель"]
        else:
            data.loc[index, "Раздел"] = current_section

    # Оставляем только реальные показатели, а не строки-заголовки разделов.
    return data[data[period_columns].notna().any(axis=1)].copy()

def make_indicator_names_unique(data: pd.DataFrame) -> pd.DataFrame:
    """Уточняет повторяющиеся строки роста названием предыдущего показателя."""
    data = data.copy()
    previous_indicator = None

    for index, indicator in data["Показатель"].items():
        if indicator == "рост г-к-г,%" and previous_indicator is not None:
            data.loc[index, "Показатель"] = f"{previous_indicator} — рост г-к-г,%"
        else:
            previous_indicator = indicator

    return data

def parse_values(long_data: pd.DataFrame) -> pd.DataFrame:
    """Переводит числа и проценты в единый числовой формат без потери исходного текста."""
    long_data = long_data.copy()
    long_data["Значение исходное"] = long_data["Значение исходное"].astype("string")

    percentage_mask = long_data["Значение исходное"].str.contains("%", na=False)
    cleaned_values = (
        long_data["Значение исходное"]
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )

    long_data["Значение"] = pd.to_numeric(cleaned_values, errors="coerce")
    long_data.loc[percentage_mask, "Значение"] = (
        long_data.loc[percentage_mask, "Значение"] / 100
    )

    long_data["Статус преобразования"] = "число"
    long_data.loc[percentage_mask, "Статус преобразования"] = "процент преобразован в долю"
    long_data.loc[long_data["Значение исходное"].isna(), "Статус преобразования"] = "исходный пропуск"

    unparsed_mask = long_data["Значение исходное"].notna() & long_data["Значение"].isna()
    long_data.loc[unparsed_mask, "Статус преобразования"] = "требует проверки"

    return long_data

def add_period_details(long_data: pd.DataFrame) -> pd.DataFrame:
    """Выделяет год, квартал и признак скорректированного периода."""
    long_data = long_data.copy()
    long_data["Скорректированный период"] = long_data["Период"].str.contains("Скорр", na=False)
    long_data["Год"] = long_data["Период"].str.extract(r"(20\d{2})")[0].astype("Int64")
    long_data["Квартал"] = long_data["Период"].str.extract(r"([1-4]) КВ")[0].astype("Int64")
    long_data["Тип периода"] = "год"
    long_data.loc[long_data["Квартал"].notna(), "Тип периода"] = "квартал"

    return long_data

def main() -> None:
    # 1. Читаем исходный лист без предположения о строке заголовков.
    operating_raw = pd.read_excel(
        SOURCE_FILE,
        sheet_name="Operating Results",
        header=None,
    )
    operating_clean = operating_raw.dropna(how="all").dropna(axis=1, how="all")

    # 2. Собираем названия столбцов и выделяем блок операционных показателей.
    header_rows = operating_clean.loc[4:5].copy()
    period_columns = create_period_names(header_rows)

    operating_data = operating_clean.loc[6:69].copy()
    operating_data.columns = ["Показатель", "Единица измерения", *period_columns]

    # 3. Убираем строки-разделители, но сохраняем их смысл в новом столбце «Раздел».
    operating_data = add_section_names(operating_data, period_columns)
    operating_data = make_indicator_names_unique(operating_data)

    # 4. Переводим широкую таблицу в длинный формат: одна строка — один показатель за период.
    operating_long = operating_data.melt(
        id_vars=["Раздел", "Показатель", "Единица измерения"],
        value_vars=period_columns,
        var_name="Период",
        value_name="Значение исходное",
    )

    # 5. Очищаем значения и добавляем признаки периода.
    operating_long = parse_values(operating_long)
    operating_long = add_period_details(operating_long)

    operating_long = operating_long[
        [
            "Раздел",
            "Показатель",
            "Единица измерения",
            "Период",
            "Тип периода",
            "Год",
            "Квартал",
            "Скорректированный период",
            "Значение исходное",
            "Значение",
            "Статус преобразования",
        ]
    ]

    # 6. Сохраняем результаты отдельно от исходного файла.
    PROCESSED_DIR.mkdir(exist_ok=True)
    operating_data.to_csv(
        PROCESSED_DIR / "x5_operating_results_wide.csv",
        index=False,
        encoding="utf-8-sig",
    )
    operating_long.to_csv(
        PROCESSED_DIR / "x5_operating_results_long.csv",
        index=False,
        encoding="utf-8-sig",
    )

    values_for_review = operating_long[
        operating_long["Статус преобразования"] == "требует проверки"
    ]
    values_for_review.to_csv(
        PROCESSED_DIR / "x5_values_for_review.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("Подготовка завершена.")
    print(f"Строк в таблице для анализа: {len(operating_long)}")
    print(f"Строк, требующих проверки: {len(values_for_review)}")
    print("Созданы файлы в папке data/processed/")

if __name__ == "__main__":
    main()