import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="월별 유저 지표 대시보드", layout="wide")

# 데이터 로드
@st.cache_data
def load_data():
    main = pd.read_csv('events_main.csv')
    userinfo = pd.read_csv('events_userinfo.csv')
    users = pd.read_csv('users_preprocessed.csv', parse_dates=['created_at'])
    return main, userinfo, users

main, userinfo, users = load_data()

# event_time 컬럼 확보 (created_at 또는 event_time 중 존재하는 것으로)
if 'event_time' in main.columns:
    main['event_time'] = pd.to_datetime(main['event_time'])
elif 'created_at' in main.columns:
    main['event_time'] = pd.to_datetime(main['created_at'])
else:
    raise ValueError('이벤트 시간 컬럼이 없습니다 (event_time 또는 created_at)')

# id 기준으로 조인하여 user_id, event_time 모두 확보
events = main.merge(userinfo[['id', 'user_id']], on='id', how='left')

events['year_month'] = events['event_time'].dt.to_period('M')
monthly_active_users = events.groupby('year_month')['user_id'].nunique()

# 신규 유저 집계 (users_preprocessed.csv의 created_at 기준)
users['first_month'] = users['created_at'].dt.to_period('M')
monthly_new_users = users.groupby('first_month')['id'].nunique()

# 월 목록 (공통 기준)
months = sorted(set(monthly_new_users.index) | set(monthly_active_users.index))

# 월별 이탈률 (이번 달에만 활동하고 다음 달에는 없는 유저 비율)
churn_rates = []
for i, month in enumerate(months[:-1]):
    this_month_users = set(events[events['year_month'] == month]['user_id'])
    next_month = months[i+1]
    next_month_users = set(events[events['year_month'] == next_month]['user_id'])
    churned = this_month_users - next_month_users
    churn_rate = len(churned) / len(this_month_users) * 100 if len(this_month_users) > 0 else 0
    churn_rates.append(churn_rate)
churn_rates.append(float('nan'))  # 마지막 달은 계산 불가

# Carrying Capacity 계산 (신규 유저수 / 이탈률)
carrying_capacity = [nu / cr if cr > 0 else float('nan')
                     for nu, cr in zip(monthly_new_users.reindex(months, fill_value=0), churn_rates)]

# 데이터프레임 정리
dashboard_df = pd.DataFrame({
    '월': [str(m) for m in months],
    '신규 유저수': monthly_new_users.reindex(months, fill_value=0).values,
    'MAU': monthly_active_users.reindex(months, fill_value=0).values,
    '이탈률(%)': churn_rates,
    'Carrying Capacity': carrying_capacity
})

# 1. Carrying Capacity & MAU 복합 그래프
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(
    go.Bar(x=dashboard_df['월'], y=dashboard_df['MAU'], name="MAU", marker_color='rgb(158,202,225)'),
    secondary_y=False,
)
fig1.add_trace(
    go.Scatter(x=dashboard_df['월'], y=dashboard_df['Carrying Capacity'], name="Carrying Capacity",
               line=dict(color='rgb(255,127,14)', width=3), mode='lines'),
    secondary_y=True,
)
fig1.update_layout(title="월별 Carrying Capacity & MAU", xaxis_title="월", barmode='group', height=400, hovermode='x unified')
fig1.update_yaxes(title_text="MAU", secondary_y=False)
fig1.update_yaxes(title_text="Carrying Capacity", secondary_y=True)

# 2. 월별 신규 유저 수 bar 그래프
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=dashboard_df['월'], y=dashboard_df['신규 유저수'], name="신규 유저수", marker_color='rgb(100,200,100)'))
fig2.update_layout(title="월별 신규 유저 수", xaxis_title="월", yaxis_title="신규 유저수", height=300)

# 3. 월별 이탈률 line 그래프
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=dashboard_df['월'], y=dashboard_df['이탈률(%)'], name="이탈률(%)",
                         line=dict(color='rgb(255,99,132)', width=3), mode='lines+markers'))
fig3.update_layout(title="월별 이탈률", xaxis_title="월", yaxis_title="이탈률(%)", height=300)

# Streamlit 레이아웃
st.title("월별 유저 지표 대시보드")
st.plotly_chart(fig1, use_container_width=True)
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig2, use_container_width=True)
with col2:
    st.plotly_chart(fig3, use_container_width=True)

# 상세 데이터 테이블
st.subheader("월별 상세 지표")
st.dataframe(
    dashboard_df.style.format({
        '신규 유저수': '{:,.0f}',
        'MAU': '{:,.0f}',
        '이탈률(%)': '{:.2f}',
        'Carrying Capacity': '{:,.0f}'
    })
)
