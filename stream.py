import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Looker Ecommerce 대시보드", layout="wide")

# 카드 스타일을 Streamlit 컨테이너에 직접 강제 적용
st.markdown("""
    <style>
    /* 카드 스타일 */
    .block-container > div[data-testid="stVerticalBlock"] > div {
        background: #fff !important;
        border-radius: 18px !important;
        box-shadow: 0 2px 8px 0 rgba(0,0,0,0.08) !important;
        padding: 36px 32px 32px 32px !important;
        margin-bottom: 32px !important;
        margin-right: 24px !important;
        margin-left: 24px !important;
        min-height: 480px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    /* 부모 컨테이너의 padding을 최소화 */
    .block-container, section.main, [data-testid="stAppViewContainer"] {
        padding-left: 24px !important;
        padding-right: 24px !important;
        background-color: #e6f0fa !important;
    }
    </style>
""", unsafe_allow_html=True)

# 예시 적용 (아래처럼 모든 st.plotly_chart, st.dataframe 호출마다 적용)
# with st.container():
#     st.markdown(f'<div style="{CARD_STYLE}">', unsafe_allow_html=True)
#     st.plotly_chart(fig, use_container_width=True)
#     st.markdown('</div>', unsafe_allow_html=True)
#
# col 내부도 동일하게 적용

# (실제 적용: 모든 st.plotly_chart, st.dataframe 호출을 위 CARD_STYLE로 감싸도록 전체 파일에 적용)

# 데이터 로드
@st.cache_data
def load_data():
    main = pd.read_csv('events_main.csv')
    userinfo = pd.read_csv('events_userinfo.csv')
    users = pd.read_csv('users_preprocessed.csv', parse_dates=['created_at'])
    return main, userinfo, users

main, userinfo, users = load_data()

# event_time 컬럼 확보
if 'event_time' in main.columns:
    main['event_time'] = pd.to_datetime(main['event_time'])
elif 'created_at' in main.columns:
    main['event_time'] = pd.to_datetime(main['created_at'])
else:
    raise ValueError('이벤트 시간 컬럼이 없습니다 (event_time 또는 created_at)')

# id 기준으로 조인하여 user_id 확보
events = main.merge(userinfo[['id', 'user_id']], on='id', how='left')
events['year_month'] = events['event_time'].dt.to_period('M')

monthly_active_users = events.groupby('year_month')['user_id'].nunique()
users['first_month'] = users['created_at'].dt.to_period('M')
monthly_new_users = users.groupby('first_month')['id'].nunique()

months = sorted(set(monthly_new_users.index) | set(monthly_active_users.index))

# 이탈률 계산 (len(this_month_users) 오류 수정!)
churn_rates = []
for i, month in enumerate(months[:-1]):
    this_month_users = set(events[events['year_month'] == month]['user_id'])
    next_month = months[i+1]
    next_month_users = set(events[events['year_month'] == next_month]['user_id'])
    churned = this_month_users - next_month_users
    churn_rate = len(churned) / len(this_month_users) * 100 if len(this_month_users) > 0 else 0
    churn_rates.append(churn_rate)
churn_rates.append(float('nan'))

# Carrying Capacity 계산
carrying_capacity = [nu / cr if cr > 0 else float('nan')
                     for nu, cr in zip(monthly_new_users.reindex(months, fill_value=0), churn_rates)]

# 데이터프레임
dashboard_df = pd.DataFrame({
    '월': [str(m) for m in months],
    '신규 유저수': monthly_new_users.reindex(months, fill_value=0).values,
    'MAU': monthly_active_users.reindex(months, fill_value=0).values,
    '이탈률(%)': churn_rates,
    'Carrying Capacity': carrying_capacity
})

# ==================================
# 🖥️ 대시보드 화면 구성
# ==================================
st.title("Looker Ecommerce 대시보드")
st.markdown(f"""
- 분석 기간: **{min(months)} ~ {max(months)}**
- 데이터 소스: https://www.kaggle.com/datasets/mustafakeser4/looker-ecommerce-bigquery-dataset
- 주요 지표: MAU, 신규 유저수, 이탈률, Carrying Capacity
""")

# ================================
# 1. 월별 지표 종합 (MAU, 신규 유저수, 이탈률)
# ================================
st.header('1. 월별 지표 종합')
fig_comp = make_subplots(specs=[[{"secondary_y": True}]])
fig_comp.add_trace(
    go.Bar(x=dashboard_df['월'], y=dashboard_df['MAU'], name="MAU", marker_color='rgb(158,202,225)'),
    secondary_y=False,
)
fig_comp.add_trace(
    go.Bar(x=dashboard_df['월'], y=dashboard_df['신규 유저수'], name="신규 유저수", marker_color='rgb(100,200,100)'),
    secondary_y=False,
)
# 이탈률 색상 강조
colors = ['red' if (x or 0) > 20 else 'green' for x in dashboard_df['이탈률(%)']]
fig_comp.add_trace(
    go.Scatter(x=dashboard_df['월'], y=dashboard_df['이탈률(%)'], name="이탈률(%)",
               line=dict(color='black', width=3), mode='lines+markers',
               marker=dict(color=colors, size=10)),
    secondary_y=True,
)
fig_comp.update_layout(title="월별 MAU, 신규 유저수, 이탈률(%)", hovermode='x unified', margin=dict(l=40, r=40, t=60, b=40))
fig_comp.update_yaxes(title_text="MAU & 신규 유저수", secondary_y=False)
fig_comp.update_yaxes(title_text="이탈률(%)", secondary_y=True)
# 모든 st.plotly_chart와 st.dataframe 호출이 카드(div)로 감싼 부분에서만 한 번씩 호출되도록, 카드 밖의 중복 호출을 모두 삭제합니다.
# 카드(div)로 감싸지 않은 st.plotly_chart, st.dataframe 호출은 모두 제거합니다.

# 1. 월별 지표 종합
with st.container():
    st.plotly_chart(fig_comp, use_container_width=True)

# ================================
# 2. Carrying Capacity & MAU
# ================================
st.header('2. Carrying Capacity & MAU')
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(
    go.Bar(x=dashboard_df['월'], y=dashboard_df['MAU'], name="MAU", marker_color='rgb(158,202,225)'),
    secondary_y=False,
)
fig1.add_trace(
    go.Scatter(x=dashboard_df['월'], y=dashboard_df['Carrying Capacity'], name="Carrying Capacity",
               line=dict(color='rgb(255,127,14)', width=3, dash='dot'), mode='lines+markers'),
    secondary_y=True,
)
fig1.update_layout(title="월별 Carrying Capacity & MAU", hovermode='x unified', margin=dict(l=40, r=40, t=60, b=40))
fig1.update_yaxes(title_text="MAU", secondary_y=False)
fig1.update_yaxes(title_text="Carrying Capacity", secondary_y=True)
# 모든 st.plotly_chart와 st.dataframe 호출이 카드(div)로 감싼 부분에서만 한 번씩 호출되도록, 카드 밖의 중복 호출을 모두 삭제합니다.
# 카드(div)로 감싸지 않은 st.plotly_chart, st.dataframe 호출은 모두 제거합니다.

# 2. Carrying Capacity & MAU
with st.container():
    st.plotly_chart(fig1, use_container_width=True)

# ================================
# 4. 유입 채널/브라우저별 inflow, churn rate
# ================================
st.header('3. 유입,이탈 세부 분석')
# 데이터 로드 및 조인
main = pd.read_csv('events_main.csv')
userinfo = pd.read_csv('events_userinfo.csv')
traffic = pd.read_csv('events_traffic.csv')

main['event_time'] = pd.to_datetime(main['created_at'])
main = main.merge(userinfo[['id', 'user_id']], on='id', how='left')
main = main.merge(traffic[['id', 'traffic_source', 'browser']], on='id', how='left')
main['year_month'] = main['event_time'].dt.to_period('M')
main['user_id'] = main['user_id'].astype(str)

# ---- 유입 채널별 분석 ----
channel_stats = []
for channel in main['traffic_source'].dropna().unique():
    ch_events = main[main['traffic_source'] == channel]
    ch_events = ch_events.sort_values('event_time')
    ch_events['year_month'] = ch_events['event_time'].dt.to_period('M')
    months_ch = sorted(ch_events['year_month'].unique())
    inflow = []
    churns = []
    prev_users = set()
    for i, month in enumerate(months_ch[:-1]):
        this_month_users = set(ch_events[ch_events['year_month'] == month]['user_id'])
        new_users = this_month_users - prev_users
        inflow.append(len(new_users))
        prev_users |= new_users
        next_month_users = set(ch_events[ch_events['year_month'] == months_ch[i+1]]['user_id'])
        churned = this_month_users - next_month_users
        churn_rate = len(churned) / len(this_month_users) * 100 if len(this_month_users) > 0 else 0
        churns.append(churn_rate)
    inflow.append(float('nan'))
    churns.append(float('nan'))
    channel_stats.append({
        '채널': channel,
        '월': [str(m) for m in months_ch],
        '신규 유저수': inflow,
        '이탈률(%)': churns
    })

# ---- 브라우저별 분석 ----
browser_stats = []
for browser in main['browser'].dropna().unique():
    br_events = main[main['browser'] == browser]
    br_events = br_events.sort_values('event_time')
    br_events['year_month'] = br_events['event_time'].dt.to_period('M')
    months_br = sorted(br_events['year_month'].unique())
    inflow = []
    churns = []
    prev_users = set()
    for i, month in enumerate(months_br[:-1]):
        this_month_users = set(br_events[br_events['year_month'] == month]['user_id'])
        new_users = this_month_users - prev_users
        inflow.append(len(new_users))
        prev_users |= new_users
        next_month_users = set(br_events[br_events['year_month'] == months_br[i+1]]['user_id'])
        churned = this_month_users - next_month_users
        churn_rate = len(churned) / len(this_month_users) * 100 if len(this_month_users) > 0 else 0
        churns.append(churn_rate)
    inflow.append(float('nan'))
    churns.append(float('nan'))
    browser_stats.append({
        '브라우저': browser,
        '월': [str(m) for m in months_br],
        '신규 유저수': inflow,
        '이탈률(%)': churns
    })

# ---- 유입 채널별 평균 inflow, churn 시각화 ----
# 채널별 평균값 계산
channel_avg = []
for stat in channel_stats:
    # 마지막 달은 nan이므로 제외
    inflow_vals = np.array(stat['신규 유저수'][:-1], dtype=float)
    churn_vals = np.array(stat['이탈률(%)'][:-1], dtype=float)
    channel_avg.append({
        '채널': stat['채널'],
        '평균 신규 유저수': np.nanmean(inflow_vals),
        '평균 이탈률(%)': np.nanmean(churn_vals)
    })
channel_avg_df = pd.DataFrame(channel_avg).sort_values('평균 이탈률(%)', ascending=False)

# ---- 브라우저별 평균 inflow, churn 시각화 ----
browser_avg = []
for stat in browser_stats:
    inflow_vals = np.array(stat['신규 유저수'][:-1], dtype=float)
    churn_vals = np.array(stat['이탈률(%)'][:-1], dtype=float)
    browser_avg.append({
        '브라우저': stat['브라우저'],
        '평균 신규 유저수': np.nanmean(inflow_vals),
        '평균 이탈률(%)': np.nanmean(churn_vals)
    })
browser_avg_df = pd.DataFrame(browser_avg).sort_values('평균 이탈률(%)', ascending=False)

fig_channel = px.bar(
    channel_avg_df.melt(id_vars='채널', value_vars=['평균 신규 유저수', '평균 이탈률(%)'], var_name='지표', value_name='값'),
    x='채널', y='값', color='지표', barmode='group',
    title='채널별 평균 신규 유저수 & 평균 이탈률(%)'
)
fig_channel.update_layout(margin=dict(l=40, r=40, t=60, b=40))
# 모든 st.plotly_chart와 st.dataframe 호출이 카드(div)로 감싼 부분에서만 한 번씩 호출되도록, 카드 밖의 중복 호출을 모두 삭제합니다.
# 카드(div)로 감싸지 않은 st.plotly_chart, st.dataframe 호출은 모두 제거합니다.

# 4. 채널/브라우저별 평균 그래프
with st.container():
    st.plotly_chart(fig_channel, use_container_width=True)

# ================================
# 6. 제품/서비스 사용 패턴분석
# ================================

# 데이터 로드 및 전처리 (필수)
order_items = pd.read_csv('order_items_preprocessed.csv')
products = pd.read_csv('products_preprocessed.csv')
order_items['user_id'] = order_items['user_id'].astype(str)
order_items = order_items.merge(products[['id', 'brand', 'category']], left_on='product_id', right_on='id', how='left')

# ================================
# 브랜드/카테고리별 월별 평균 이탈률 분석

# created_at이 datetime이 아닐 경우 변환
order_items['created_at'] = pd.to_datetime(order_items['created_at'], errors='coerce')
order_items['year_month'] = order_items['created_at'].dt.to_period('M')
order_items['user_id'] = order_items['user_id'].astype(str)

brand_churn_rates = []
category_churn_rates = []

for i, month in enumerate(months[:-1]):
    this_month = order_items[order_items['year_month'] == month]
    next_month = order_items[order_items['year_month'] == months[i+1]]
    for brand in this_month['brand'].dropna().unique():
        brand_users = set(this_month[this_month['brand'] == brand]['user_id'])
        if not brand_users:
            continue
        next_month_users = set(next_month['user_id'])
        churned = brand_users - next_month_users
        churn_rate = len(churned) / len(brand_users) * 100
        brand_churn_rates.append({'월': str(month), 'brand': brand, '이탈률': churn_rate})
    for category in this_month['category'].dropna().unique():
        category_users = set(this_month[this_month['category'] == category]['user_id'])
        if not category_users:
            continue
        next_month_users = set(next_month['user_id'])
        churned = category_users - next_month_users
        churn_rate = len(churned) / len(category_users) * 100
        category_churn_rates.append({'월': str(month), 'category': category, '이탈률': churn_rate})

brand_churn_df = pd.DataFrame(brand_churn_rates)
category_churn_df = pd.DataFrame(category_churn_rates)



# 카테고리별 월별 신규 유저수 계산
category_new_users = []
for category in order_items['category'].dropna().unique():
    category_df = order_items[order_items['category'] == category].sort_values('created_at')
    category_df['first_month'] = category_df.groupby('user_id')['year_month'].transform('min')
    category_df = category_df[category_df['year_month'] == category_df['first_month']]
    monthly_new = category_df.groupby('year_month')['user_id'].nunique()
    for month, cnt in monthly_new.items():
        category_new_users.append({'category': category, 'year_month': month, '신규유저수': cnt})
category_new_users_df = pd.DataFrame(category_new_users)
category_new_users_mean = category_new_users_df.groupby('category')['신규유저수'].mean().reset_index()



# 카테고리별 평균 이탈률/신규유저수 Top 10
if not category_churn_df.empty:
    category_churn_mean = category_churn_df.groupby('category')['이탈률'].mean().reset_index()
    category_summary = pd.merge(
        category_churn_mean, category_new_users_mean, on='category', how='left'
    ).sort_values('이탈률', ascending=False).head(10)
    fig_category = px.bar(
        category_summary.melt(id_vars='category', value_vars=['신규유저수', '이탈률'], var_name='지표', value_name='값'),
        x='category', y='값', color='지표', barmode='group',
        title='카테고리별 평균 신규 유저수 & 평균 이탈률(%) Top 10'
    )
    fig_category.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    # 모든 st.plotly_chart와 st.dataframe 호출이 카드(div)로 감싼 부분에서만 한 번씩 호출되도록, 카드 밖의 중복 호출을 모두 삭제합니다.
    # 카드(div)로 감싸지 않은 st.plotly_chart, st.dataframe 호출은 모두 제거합니다.

    # 브랜드/카테고리별 평균 그래프
    with st.container():
        st.plotly_chart(fig_category, use_container_width=True)

# ================================
# 4. 고객 세그먼트 분석
# ================================
st.header('4. 고객 세그먼트 분석')

# 데이터 로드
users = pd.read_csv('users_preprocessed.csv')

# 연령대 구간 생성
bins = [0, 19, 29, 39, 49, 59, 200]
labels = ['10대 이하', '20대', '30대', '40대', '50대', '60대 이상']
users['age_group'] = pd.cut(users['age'], bins=bins, labels=labels, right=True, include_lowest=True)

# 연령대 분포
age_counts = users['age_group'].value_counts().sort_index()
# 성별 분포
gender_counts = users['gender'].value_counts()
# 국가 분포 (TOP 10)
country_counts = users['country'].value_counts().head(10)

col1, col2 = st.columns(2)
with col1:
    fig_age = px.pie(
        names=age_counts.index,
        values=age_counts.values,
        hole=0.5,
        title='고객 연령대 분포',
    )
    fig_age.update_traces(textinfo='percent+label')
    fig_age.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    st.plotly_chart(fig_age, use_container_width=True)
with col2:
    fig_gender = px.pie(
        names=gender_counts.index,
        values=gender_counts.values,
        hole=0.5,
        title='고객 성별 분포',
    )
    fig_gender.update_traces(textinfo='percent+label')
    fig_gender.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    st.plotly_chart(fig_gender, use_container_width=True)
with st.container():
    fig_country = px.bar(
        x=country_counts.index,
        y=country_counts.values,
        labels={'x': '국가', 'y': '고객 수'},
        title='고객 국가 분포 Top 10',
    )
    fig_country.update_layout(margin=dict(l=40, r=40, t=60, b=40))
    st.plotly_chart(fig_country, use_container_width=True)
