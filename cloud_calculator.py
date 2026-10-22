"""Облачный калькулятор для ВК."""

from decimal import Decimal, ROUND_CEILING
import streamlit as st
from sqlalchemy import text
from cloud_database import get_cloud_engine

st.set_page_config(page_title="Калькулятор 3D-печати", page_icon="💰", layout="centered")

# ============================================================
# ВНУТРЕННИЕ КОНСТАНТЫ (СКРЫТЫ ОТ КЛИЕНТА)
# ============================================================
DEFAULT_PRINTER_RATE = Decimal("55")
LABOR_RATE = Decimal("55")
POSTPROCESS_H = Decimal("0.2")
MARGIN = Decimal("40")
WASTE_FACTOR = Decimal("1.05")
VK_DISCOUNT = Decimal("10")
MIN_PRICE = Decimal("50")  # Минимальная стоимость


# ============================================================
# ЗАГРУЗКА ДАННЫХ
# ============================================================
def load_filaments():
    """Загружает список филаментов из облака."""
    engine = get_cloud_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, material, color, price_per_gram FROM filament_spools ORDER BY id"
        )).fetchall()
    return [{"id": r[0], "label": f"{r[1]} {r[2]}", "price": r[3]} for r in rows]


# ============================================================
# РАСЧЕТ (ЕДИНАЯ ФУНКЦИЯ)
# ============================================================
def calculate_final_price(weight, print_time, price_per_gram, is_vk_discount):
    """
    Считает итоговую цену с учетом скидки, минимальной стоимости и округления.
    """
    # 1. Себестоимость
    material_cost = weight * price_per_gram * WASTE_FACTOR
    machine_cost = print_time * DEFAULT_PRINTER_RATE
    labor_cost = POSTPROCESS_H * LABOR_RATE
    cost = material_cost + machine_cost + labor_cost

    # 2. Наценка
    price = cost * (Decimal("1") + MARGIN / Decimal("100"))

    # 3. Скидка
    if is_vk_discount:
        price = price * (Decimal("1") - VK_DISCOUNT / Decimal("100"))

    # 4. Минимальная цена (50₽)
    if price < MIN_PRICE:
        price = MIN_PRICE

    # 5. Округление до 10₽ вверх
    price = (price / Decimal("10")).to_integral_value(rounding=ROUND_CEILING) * Decimal("10")

    return price.quantize(Decimal("0.01"))


# ============================================================
# ИНТЕРФЕЙС
# ============================================================
def main():
    st.title("💰 Калькулятор 3D-печати")
    st.caption("Рассчитайте примерную стоимость печати вашей модели")

    try:
        filaments = load_filaments()
    except Exception as e:
        st.error(f"Ошибка БД: {e}")
        st.stop()

    if not filaments:
        st.warning("Нет данных о филаменте.")
        st.stop()

    # 1. Параметры модели
    st.subheader("1. Параметры модели")
    c1, c2 = st.columns(2)
    # Добавляем key, чтобы Streamlit точно отслеживал изменения
    weight = c1.number_input("Вес изделия, г", min_value=1.0, value=50.0, step=1.0, key="calc_weight")
    print_time = c2.number_input("Время печати, ч", min_value=0.1, value=3.0, step=0.1, key="calc_time")

    # 2. Материал
    st.subheader("2. Материал")

    # Просто список строк. Без ID и session_state.
    # Streamlit отлично запоминает выбранную строку.
    labels = [f["label"] for f in filaments]
    selected_label = st.selectbox("Выберите тип филамента", options=labels, key="calc_filament")

    # Находим цену по выбранному названию
    selected_filament = next(f for f in filaments if f["label"] == selected_label)
    price_per_gram = Decimal(str(selected_filament["price"]))

    # 3. Скидка
    st.subheader("3. Скидка")
    has_vk = st.checkbox("🎁 Я подписчик группы ВКонтакте (скидка 10%)", value=False, key="calc_vk")

    st.divider()

    # Расчет
    price_normal = calculate_final_price(
        Decimal(str(weight)), Decimal(str(print_time)), price_per_gram, False
    )
    price_discount = calculate_final_price(
        Decimal(str(weight)), Decimal(str(print_time)), price_per_gram, True
    )

    # Вывод
    if has_vk:
        st.markdown(
            f"### Итоговая стоимость: **{price_discount} ₽**\n"
            f"~~Обычная цена: {price_normal} ₽~~ &nbsp; 🎁 Скидка ВК: 10%"
        )
    else:
        st.markdown(f"### Итоговая стоимость: **{price_normal} ₽**")

    # Дисклеймер
    st.divider()
    st.warning(
        "⚠️ **Важно:** Указанная стоимость носит **ознакомительный характер** "
        "и **не является публичной офертой** (ст. 437 ГК РФ).\n\n"
        "Предварительный расчёт не учитывает сложность модели, поддержки, постобработку и срочность."
    )


if __name__ == "__main__":
    main()
