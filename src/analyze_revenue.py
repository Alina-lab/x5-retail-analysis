import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "x5_operating_results_long.csv"
)
IMAGE_DIR = Path(__file__).resolve().parent.parent / "images"

data = pd.read_csv(DATA_FILE)

chains = ["Пятёрочка (2)", "Перекрёсток", "Чижик"]

revenue_2025 = data[
    (data["Раздел"] == "Чистая розничная выручка (1)")
    & (data["Период"] == "2025 (2)")
    & (data["Показатель"].isin(chains))
].copy()

revenue_2025 = revenue_2025.sort_values("Значение", ascending=False)

total_revenue = revenue_2025["Значение"].sum()

revenue_2025["Доля, %"] = (
    revenue_2025["Значение"] / total_revenue * 100
).round(1)

print(revenue_2025[["Показатель", "Значение", "Доля, %"]])

# Сравниваем выручку за 2024 и 2025 годы.
comparison_periods = ["2024 Скорр.", "2025 (2)"]
revenue_comparison = data[
    (data["Раздел"] == "Чистая розничная выручка (1)")
    & (data["Период"].isin(comparison_periods))
    & (data["Показатель"].isin(chains))
].copy()

revenue_growth = revenue_comparison.pivot(
    index="Показатель",
    columns="Период",
    values="Значение",
).reindex(columns=comparison_periods)

if revenue_growth.isna().any().any():
    raise ValueError("Не найдены данные по всем сетям и выбранным периодам.")

revenue_growth = revenue_growth.rename(
    columns={
        "2024 Скорр.": "Выручка 2024, млн руб.",
        "2025 (2)": "Выручка 2025, млн руб.",
    }
)
revenue_growth["Абсолютное изменение, млн руб."] = (
    revenue_growth["Выручка 2025, млн руб."]
    - revenue_growth["Выручка 2024, млн руб."]
)
revenue_growth["Темп прироста, %"] = (
    revenue_growth["Выручка 2025, млн руб."]
    / revenue_growth["Выручка 2024, млн руб."]
    - 1
) * 100
revenue_growth = revenue_growth.round(1)

print("\nСравнение чистой розничной выручки за годовые периоды:")
print(revenue_growth.to_string())

IMAGE_DIR.mkdir(exist_ok=True)
plot_data = revenue_growth.sort_values("Темп прироста, %", ascending=False)
ax = plot_data["Темп прироста, %"].plot(
    kind="bar",
    color=["#2E86AB", "#5DAE8B", "#F4A261"],
    figsize=(8, 5),
)
ax.set_title("Прирост чистой розничной выручки: 2025 к 2024 году")
ax.set_xlabel("")
ax.set_ylabel("Темп прироста, %")
ax.bar_label(ax.containers[0], fmt="%.1f%%", padding=3)
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(IMAGE_DIR / "revenue_growth_2024_2025.png", dpi=150)
plt.close()

# LFL за 2025 год показывает изменение сопоставимых продаж к 2024 году.
lfl_indicators = ["Продажи", "Трафик", "Средний чек"]
lfl_data = data[
    (data["Раздел"].isin([f"LFL - {chain}" for chain in chains]))
    & (data["Показатель"].isin(lfl_indicators))
    & (data["Период"] == "2025 (2)")
].copy()

lfl_data["Сеть"] = lfl_data["Раздел"].str.replace("LFL - ", "", regex=False)
lfl_table = lfl_data.pivot(
    index="Сеть",
    columns="Показатель",
    values="Значение",
).reindex(index=chains, columns=lfl_indicators)

if lfl_table.isna().any().any():
    raise ValueError("Не найдены все LFL-показатели для рассматриваемых сетей.")

lfl_table = (lfl_table * 100).rename(
    columns={
        "Продажи": "LFL-продажи, %",
        "Трафик": "LFL-трафик, %",
        "Средний чек": "LFL-средний чек, %",
    }
).round(1)

print("\nLFL-показатели за 2025 год к 2024 году:")
print(lfl_table.to_string())

ax = lfl_table.plot(
    kind="bar",
    figsize=(9, 5),
    color=["#2E86AB", "#5DAE8B", "#F4A261"],
)
ax.set_title("LFL-продажи и факторы изменения: 2025 к 2024 году")
ax.set_xlabel("")
ax.set_ylabel("Изменение, %")
ax.axhline(0, color="black", linewidth=0.8)
ax.legend(title="Показатель")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(IMAGE_DIR / "lfl_sales_traffic_average_check_2025.png", dpi=150)
plt.close()

# Смотрим, как менялись число магазинов и торговая площадь.
network_periods = ["2024 Скорр.", "2025 (2)"]
store_data = data[
    (data["Раздел"] == "Количество магазинов (на конец периода)")
    & (data["Показатель"].isin(chains))
    & (data["Период"].isin(network_periods))
].copy()

store_wide = store_data.pivot(
    index="Показатель",
    columns="Период",
    values="Значение",
).reindex(index=chains, columns=network_periods)

store_table = pd.DataFrame(index=chains)
store_table["Магазины 2024"] = store_wide["2024 Скорр."]
store_table["Магазины 2025"] = store_wide["2025 (2)"]
store_table["Изменение магазинов"] = (
    store_table["Магазины 2025"] - store_table["Магазины 2024"]
)
store_table["Прирост магазинов, %"] = (
    store_table["Магазины 2025"] / store_table["Магазины 2024"] - 1
) * 100

space_data = data[
    (data["Раздел"] == "Торговая площадь")
    & (data["Показатель"].isin(["Пятёрочка(2)", "Перекрёсток", "Чижик"]))
    & (data["Период"].isin(network_periods))
].copy()

annual_data = pd.concat(
    [revenue_comparison, lfl_data, store_data, space_data]
)
if not annual_data["Тип периода"].eq("год").all():
    raise ValueError("Для анализа выбраны не только годовые периоды.")

space_data["Показатель"] = space_data["Показатель"].replace(
    {"Пятёрочка(2)": "Пятёрочка (2)"}
)
space_wide = space_data.pivot(
    index="Показатель",
    columns="Период",
    values="Значение",
).reindex(index=chains, columns=network_periods)

space_table = pd.DataFrame(index=chains)
space_table["Площадь 2024, тыс. кв. м"] = space_wide["2024 Скорр."]
space_table["Площадь 2025, тыс. кв. м"] = space_wide["2025 (2)"]
space_table["Изменение площади, тыс. кв. м"] = (
    space_table["Площадь 2025, тыс. кв. м"]
    - space_table["Площадь 2024, тыс. кв. м"]
)
space_table["Прирост площади, %"] = (
    space_table["Площадь 2025, тыс. кв. м"]
    / space_table["Площадь 2024, тыс. кв. м"]
    - 1
) * 100

network_summary = store_table.join(space_table).join(
    revenue_growth["Темп прироста, %"]
).join(lfl_table["LFL-продажи, %"])

if network_summary.isna().any().any():
    raise ValueError("Не найдены все показатели для сравнения физических сетей.")

network_summary = network_summary.round(1)
print("\nРасширение физических сетей и динамика продаж:")
print(network_summary.to_string())

ax = network_summary[
    ["Темп прироста, %", "LFL-продажи, %", "Прирост магазинов, %"]
].plot(
    kind="bar",
    figsize=(9, 5),
    color=["#2E86AB", "#5DAE8B", "#F4A261"],
)
ax.set_title("Выручка, LFL-продажи и расширение сети: 2025 к 2024 году")
ax.set_xlabel("")
ax.set_ylabel("Изменение, %")
ax.axhline(0, color="black", linewidth=0.8)
ax.legend(title="Показатель")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(IMAGE_DIR / "revenue_lfl_store_growth_2025.png", dpi=150)
plt.close()