"""Облачный калькулятор для ВК."""

from decimal import Decimal, ROUND_CEILING
import streamlit as st
from sqlalchemy import text
from cloud_database import get_cloud_engine

st.set_page_config(page_title="Калькулятор 3D-печати", page_icon="💰", layout="centered")

# Скрытые константы (пользователь их не видит)
DEFAULT_PRINTER_RATE = Decimal("55")
LABOR_RATE = Decimal("55")
POSTPROCESS_H = Decimal("0.2")
MARGIN = Decimal("40")
WASTE_FACTOR = Decimal("1.05")
VK_DISCOUNT = Decimal("10")


def load_filaments():
    """Загружает список филаментов из облака."""
    engine = get_cloud_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, material, color, price_per_gram FROM filament_spools ORDER BY id"
        )).fetchall()
    return [{"id": r[0], "label": f"{r[1]} {r[2]} ({float(r[3])}₽/г)", "price": r[3]} for r in rows]


def get_raw_price(weight, print_time, price_per_gram):
    """Считает цену без скидки и без округления."""
    material_cost = weight * price_per_gram * WASTE_FACTOR
    machine_cost = print_time * DEFAULT_PRINTER_RATE
    labor_cost = POSTPROCESS_H * LABOR_RATE
    cost = material_cost + machine_cost + labor_cost
    return cost * (Decimal("1") + MARGIN / Decimal("100"))


def format_price(price_decimal):
    """Округляет до 10₽ вверх для красивого вывода."""
    rounded = (price_decimal / Decimal("10")).to_integral_value(rounding=ROUND_CEILING) * Decimal("10")
    return rounded.quantize(Decimal("0.01"))


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
    weight = c1.number_input("Вес изделия, г", min_value=1.0, value=50.0, step=1.0)
    print_time = c2.number_input("Время печати, ч", min_value=0.1, value=3.0, step=0.1)

    # 2. Материал
    st.subheader("2. Материал")

    # Инициализируем session_state, если его еще нет
    if "selected_filament_id" not in st.session_state:
        st.session_state.selected_filament_id = filaments[0]["id"]

    # Создаем словарь ID -> Название
    options_dict = {f["id"]: f["label"] for f in filaments}

    # Находим индекс текущего выбранного ID
    current_index = list(options_dict.keys()).index(st.session_state.selected_filament_id)

    # Виджет выбора
    selected_id = st.selectbox(
        "Выберите тип филамента",
        options=list(options_dict.keys()),
        index=current_index,
        format_func=lambda x: options_dict[x],
        key="filament_widget"
    )

    # Если выбор изменился — обновляем session_state и принудительно перезапускаем страницу
    if selected_id != st.session_state.selected_filament_id:
        st.session_state.selected_filament_id = selected_id
        st.rerun()

    # Берем цену по ID из session_state
    price_per_gram = Decimal(
        str(next(f["price"] for f in filaments if f["id"] == st.session_state.selected_filament_id)))

    # 3. Скидка
    st.subheader("3. Скидка")
    has_vk = st.checkbox("🎁 Я подписчик группы ВКонтакте (скидка 10%)", value=False)

    st.divider()

    # Считаем цены
    raw_price_normal = get_raw_price(Decimal(str(weight)), Decimal(str(print_time)), price_per_gram)

    # Скидка считается от "сырой" цены
    discount_amount = raw_price_normal * (VK_DISCOUNT / Decimal("100"))
    raw_price_discount = raw_price_normal - discount_amount

    # Вывод результата
    if has_vk:
        st.markdown(
            f"### Итоговая стоимость: **{format_price(raw_price_discount)} ₽**\n"
            f"~~Обычная цена: {format_price(raw_price_normal)} ₽~~ &nbsp; 🎁 Скидка ВК: 10%"
        )
    else:
        st.markdown(f"### Итоговая стоимость: **{format_price(raw_price_normal)} ₽**")

    # Дисклеймер
    st.divider()
    st.warning(
        "⚠️ **Важно:** Указанная стоимость носит **ознакомительный характер** "
        "и **не является публичной офертой** (ст. 437 ГК РФ).\n\n"
        "Предварительный расчёт не учитывает сложность модели, поддержки, постобработку и срочность."
    )


if __name__ == "__main__":
    main()