import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# -----------------------
# 📌 데이터 불러오기
# -----------------------
orders = pd.read_csv("orders_preprocessed.csv", parse_dates=["created_at", "returned_at", "shipped_at", "delivered_at"])
order_items = pd.read_csv("order_items_preprocessed.csv", parse_dates=["created_at", "shipped_at", "delivered_at", "returned_at"])
inventory = pd.read_csv("inventory_items_sold.csv")
inventory['sold_at'] = pd.to_datetime(inventory['sold_at'], errors='coerce')

# -----------------------
# 📌 연도 목록 고정
# -----------------------
fixed_years = [2019, 2020, 2021, 2022, 2023, 2024]
selected_years = []
# -----------------------
# 📌 레이아웃 전체 너비 확장
# -----------------------
st.markdown("""
    <style>
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------
# 📌 상단: 제목 + 체크박스 (반응형)
# -----------------------
top_cols = st.columns([2.5, 1.5])  # 왼쪽 넓게, 오른쪽 체크박스

with top_cols[0]:
    st.markdown("### Looker Ecommerce Dashboard")

with top_cols[1]:
    # 줄바꿈 방지 + 크기 축소
    st.markdown("""
        <style>
        .stCheckbox > div {
            font-size: 0.8rem !important;
            transform: scale(0.85);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-bottom: -4px;
        }
        </style>
    """, unsafe_allow_html=True)

    cb_cols = st.columns(3)  # 3열 배치
    for i, year in enumerate(fixed_years):
        with cb_cols[i % 3]:
            if st.checkbox(str(year), value=True, key=f"year_{year}"):
                selected_years.append(year)

# -----------------------
# 📌 데이터 필터링
# -----------------------
order_items['year'] = order_items['delivered_at'].dt.year
filtered_order_items = order_items[order_items['year'].isin(selected_years)]
filtered_orders = orders[orders['delivered_at'].dt.year.isin(selected_years)]
filtered_inventory = inventory[inventory['sold_at'].dt.year.isin(selected_years)]

# -----------------------
# 📌 KPI 계산
# -----------------------
total_sales = filtered_inventory["product_retail_price"].sum()
valid_orders = filtered_orders[filtered_orders["status"] == "Complete"]
num_orders = valid_orders.shape[0]
avg_order_value = total_sales / num_orders if num_orders else 0
returned_orders = filtered_orders[filtered_orders["returned_at"].notnull()]
return_rate = len(returned_orders) / len(filtered_orders) * 100 if len(filtered_orders) > 0 else 0
delivered_orders = filtered_orders[filtered_orders["delivered_at"].notnull() & filtered_orders["shipped_at"].notnull()]
delivery_time = (delivered_orders["delivered_at"] - delivered_orders["shipped_at"]).dt.days
avg_delivery_days = delivery_time.mean()

def format_k(value):
    if value >= 1e6:
        return f"{value/1e6:.1f}M"
    elif value >= 1e3:
        return f"{value/1e3:.1f}K"
    else:
        return f"{value:,.0f}"

# -----------------------
# 📌 KPI 시각화 (반응형 균등)
# -----------------------
kpi_cols = st.columns(5)
with kpi_cols[0]:
    st.metric("총 매출", f"${format_k(total_sales)}")
with kpi_cols[1]:
    st.metric("주문 수", f"{num_orders:,}")
with kpi_cols[2]:
    st.metric("평균 주문 금액", f"${format_k(avg_order_value)}")
with kpi_cols[3]:
    st.metric("반품률", f"{return_rate:.1f}%")
with kpi_cols[4]:
    st.metric("평균 배송 소요시간", f"{avg_delivery_days:.1f}일")

# -----------------------
# 📌 월별 매출 시계열 그래프 (반응형)
# -----------------------
filtered_order_items['month'] = filtered_order_items['delivered_at'].dt.month
monthly_sales = filtered_order_items.groupby(['year', 'month'])['sale_price'].sum().reset_index()

fig, ax = plt.subplots(figsize=(8, 5))
for year in selected_years:
    sales = monthly_sales[monthly_sales['year'] == year]
    ax.plot(sales['month'], sales['sale_price'], marker='o', label=str(year))

ax.set_xlabel("월")
ax.set_ylabel("매출")
ax.set_xticks(range(1, 13))

legend = ax.legend(title="연도", loc="upper left")
legend.get_frame().set_alpha(0.2)


plt.tight_layout()
st.pyplot(fig, use_container_width=True)
