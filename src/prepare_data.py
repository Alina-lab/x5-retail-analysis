from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
SOURCE_FILE = PROJECT_DIR / "data" / "x5_results.xlsx"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"


def create_period_names(header_rows: pd.DataFrame) -> list[str]:
    """Создаёт понятные названия столбцов с периодами."""
    period_names = []

    for column in header_rows.columns[2:]:
        period = header_rows.loc[4, column]
        correction = header_rows.loc[5, column]

        if isinstance(period, float) and period.is_integer():
            period_name = str(int(period))
        else:
            period_name = str(period)
        if pd.notna(correction):
            period_name = f"{period_name} Скорр."

        period_names.append(period_name)

    return period_names


def parse_values(long_data: pd.DataFrame) -> pd.DataFrame:
    """Переводит числа и проценты в единый числовой формат без потери исходного текста."""
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
    long_data.loc[
        long_data["Значение исходное"].isna(), "Статус преобразования"
    ] = "исходный пропуск"

    unparsed_mask = long_data["Значение исходное"].notna() & long_data["Значение"].isna()
    long_data.loc[unparsed_mask, "Статус преобразования"] = "требует проверки"

    return long_data


def main() -> None:
    operating = pd.read_excel(
        SOURCE_FILE,
        sheet_name="Operating Results",
        header=None,
    )
    operating = operating.dropna(how="all").dropna(axis=1, how="all")

    # Строки 4–5 содержат периоды, 6–69 — операционные показатели листа X5.
    periods = create_period_names(operating.loc[4:5])
    operating_data = operating.loc[6:69]
    operating_data.columns = ["Показатель", "Единица измерения", *periods]

    # Название раздела находится в строке без значений и относится к строкам ниже.
    has_values = operating_data[periods].notna().any(axis=1)
    sections = operating_data["Показатель"].where(~has_values)
    operating_data["Раздел"] = sections.ffill()
    operating_data = operating_data.loc[has_values]

    # Строка роста относится к предыдущему показателю: уточняем её название.
    growth_rows = operating_data["Показатель"].eq("рост г-к-г,%")
    indicators = operating_data["Показатель"].where(~growth_rows).ffill()
    operating_data.loc[growth_rows, "Показатель"] = (
        indicators[growth_rows] + " — рост г-к-г,%"
    )

    operating_long = operating_data.melt(
        id_vars=["Раздел", "Показатель", "Единица измерения"],
        value_vars=periods,
        var_name="Период",
        value_name="Значение исходное",
    )

    operating_long = parse_values(operating_long)
    operating_long["Скорректированный период"] = operating_long["Период"].str.contains(
        "Скорр", na=False
    )
    operating_long["Год"] = (
        operating_long["Период"].str.extract(r"(20\d{2})")[0].astype("Int64")
    )
    operating_long["Квартал"] = (
        operating_long["Период"].str.extract(r"([1-4]) КВ")[0].astype("Int64")
    )
    operating_long["Тип периода"] = "год"
    operating_long.loc[operating_long["Квартал"].notna(), "Тип периода"] = "квартал"

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
