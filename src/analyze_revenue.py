from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_DIR / "data" / "processed" / "x5_operating_results_long.csv"
IMAGE_DIR = PROJECT_DIR / "images"

data = pd.read_csv(DATA_FILE)

chains = ["Пятёрочка (2)", "Перекрёсток", "Чижик"]
periods = ["2024 Скорр.", "2025 (2)"]

annual = data[data["Период"].isin(periods)]

# В разделе площади у Пятёрочки нет пробела перед сноской.
annual["Показатель"] = annual["Показатель"].replace(
    {"Пятёрочка(2)": "Пятёрочка (2)"}
)

revenue = annual[annual["Раздел"].eq("Чистая розничная выручка (1)")]
revenue_wide = revenue.pivot(
    index="Показатель", columns="Период", values="Значение"
)
revenue_wide = revenue_wide.loc[chains, periods]

if revenue_wide.isna().any().any():
    raise ValueError("Не найдены данные по всем сетям и выбранным периодам.")

revenue_2025 = revenue_wide[["2025 (2)"]].rename(
    columns={"2025 (2)": "Выручка 2025, млн руб."}
).sort_values("Выручка 2025, млн руб.", ascending=False)
revenue_2025["Доля, %"] = (
    revenue_2025["Выручка 2025, млн руб."]
    / revenue_2025["Выручка 2025, млн руб."].sum()
    * 100
).round(1)

print("Структура выручки трёх сетей за 2025 год:")
print(revenue_2025.to_string())

revenue_growth = revenue_wide.rename(
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
plt.savefig(IMAGE_DIR / "revenue_growth_2024_2025.svg")
plt.close()

lfl_indicators = ["Продажи", "Трафик", "Средний чек"]
lfl = annual[
    annual["Раздел"].str.startswith("LFL - ")
    & annual["Период"].eq("2025 (2)")
]
lfl_table = lfl.pivot(
    index="Раздел", columns="Показатель", values="Значение"
)
lfl_table = lfl_table.loc[[f"LFL - {chain}" for chain in chains], lfl_indicators]
lfl_table.index = chains

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
ax.set_title("LFL-продажи, трафик и средний чек: 2025 к 2024 году")
ax.set_xlabel("")
ax.set_ylabel("Изменение, %")
ax.axhline(0, color="black", linewidth=0.8)
ax.legend(title="Показатель")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(IMAGE_DIR / "lfl_sales_traffic_average_check_2025.png", dpi=150)
plt.savefig(IMAGE_DIR / "lfl_sales_traffic_average_check_2025.svg")
plt.close()

stores = annual[annual["Раздел"].eq("Количество магазинов (на конец периода)")]
store_table = stores.pivot(
    index="Показатель", columns="Период", values="Значение"
)
store_table = store_table.loc[chains, periods]
store_table = store_table.rename(
    columns={"2024 Скорр.": "Магазины 2024", "2025 (2)": "Магазины 2025"}
)
store_table["Изменение магазинов"] = (
    store_table["Магазины 2025"] - store_table["Магазины 2024"]
)
store_table["Прирост магазинов, %"] = (
    store_table["Магазины 2025"] / store_table["Магазины 2024"] - 1
) * 100

space = annual[annual["Раздел"].eq("Торговая площадь")]
space_table = space.pivot(
    index="Показатель", columns="Период", values="Значение"
)
space_table = space_table.loc[chains, periods]
space_table = space_table.rename(
    columns={
        "2024 Скорр.": "Площадь 2024, тыс. кв. м",
        "2025 (2)": "Площадь 2025, тыс. кв. м",
    }
)
space_table["Изменение площади, тыс. кв. м"] = (
    space_table["Площадь 2025, тыс. кв. м"]
    - space_table["Площадь 2024, тыс. кв. м"]
)
space_table["Прирост площади, %"] = (
    space_table["Площадь 2025, тыс. кв. м"]
    / space_table["Площадь 2024, тыс. кв. м"]
    - 1
) * 100

network_summary = pd.concat([
    store_table,
    space_table,
    revenue_growth["Темп прироста, %"],
    lfl_table["LFL-продажи, %"],
], axis=1)

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
plt.savefig(IMAGE_DIR / "revenue_lfl_store_growth_2025.svg")
plt.close()
