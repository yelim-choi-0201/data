
%%writefile app.py

import pandas as pd
import streamlit as st
import plotly.express as px

# -----------------------------------
# 1. 페이지 설정
# -----------------------------------
st.set_page_config(
    page_title="지하철 승하차 분석",
    page_icon="🚇",
    layout="wide"
)

# -----------------------------------
# 2. 데이터 읽기 및 정제
# -----------------------------------
data_path = 'raw.csv'

@st.cache_data
def load_data():

    # UTF-16 인코딩, 보고서 상단 5줄 제외
    raw = pd.read_csv(
        data_path,
        encoding='utf-16',
        skiprows=5
    )

    # 역명 컬럼명 변경
    if '역명' not in raw.columns and 'Unnamed: 5' in raw.columns:
        raw = raw.rename(columns={'Unnamed: 5': '역명'})

    # 중복 제거
    clean = raw.drop_duplicates().copy()

    # 날짜 데이터 변환
    clean['운행일자'] = pd.to_datetime(
        clean['운행일자'].astype(str),
        format='%Y%m%d',
        errors='coerce'
    )

    # 승차 및 하차 인원 숫자 변환
    clean['전철승차인원수'] = pd.to_numeric(
        clean['전철승차인원수'].astype(str).str.replace(',', '', regex=False),
        errors='coerce'
    )

    clean['전철하차인원수'] = pd.to_numeric(
        clean['전철하차인원수'].astype(str).str.replace(',', '', regex=False),
        errors='coerce'
    )

    clean = clean.dropna(
        subset=[
            '운행일자',
            '역명',
            '전철승차인원수',
            '전철하차인원수'
        ]
    )

    return clean


try:
    clean = load_data()
except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.info("raw.csv 파일이 app.py와 같은 폴더에 있는지 확인하세요.")
    st.stop()


# -----------------------------------
# 3. 제목과 설명
# -----------------------------------
st.title('🚇 철도데이터 분석 대시보드')

st.write(
    '역명과 운행일자별 전철 승차 및 하차 인원을 분석합니다.'
)

st.write('전체 데이터 행 수:', len(clean))


# -----------------------------------
# 4. 사이드바 필터
# -----------------------------------
st.sidebar.header('분석 조건 설정')

station_list = sorted(clean['역명'].unique())

selected_station = st.sidebar.multiselect(
    '역명 선택',
    station_list,
    default=station_list
)

start_date = clean['운행일자'].min().date()
end_date = clean['운행일자'].max().date()

selected_date = st.sidebar.date_input(
    '운행일자 선택',
    value=(start_date, end_date)
)

if len(selected_date) == 2:
    date_start, date_end = selected_date
else:
    date_start = date_end = selected_date[0]


# 데이터 필터링
filtered = clean[
    (clean['역명'].isin(selected_station)) &
    (clean['운행일자'].dt.date >= date_start) &
    (clean['운행일자'].dt.date <= date_end)
].copy()

if filtered.empty:
    st.warning('선택한 조건에 해당하는 데이터가 없습니다.')
    st.stop()


# -----------------------------------
# 5. 주요 통계
# -----------------------------------
st.subheader('📌 주요 승하차 통계')

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    '총 승차 인원',
    f"{filtered['전철승차인원수'].sum():,.0f}명"
)

col2.metric(
    '총 하차 인원',
    f"{filtered['전철하차인원수'].sum():,.0f}명"
)

col3.metric(
    '역 개수',
    f"{filtered['역명'].nunique()}개"
)

col4.metric(
    '운행일수',
    f"{filtered['운행일자'].nunique()}일"
)


# -----------------------------------
# 6. 역명, 운행일자별 집계
# -----------------------------------
grouped = filtered.groupby(
    ['역명', '운행일자']
).agg(
    승차인원수=('전철승차인원수', 'sum'),
    하차인원수=('전철하차인원수', 'sum')
).reset_index()


# -----------------------------------
# 7. 날짜별 승차 및 하차 그래프
# -----------------------------------
st.divider()

st.subheader('📈 날짜별 승하차 인원 추이')

daily = grouped.groupby(
    '운행일자'
)[['승차인원수', '하차인원수']].sum().reset_index()

daily_long = daily.melt(
    id_vars='운행일자',
    var_name='구분',
    value_name='인원수'
)

fig1 = px.line(
    daily_long,
    x='운행일자',
    y='인원수',
    color='구분',
    markers=True,
    title='일별 전철 승차 및 하차 인원'
)

fig1.update_layout(
    xaxis_title='운행일자',
    yaxis_title='인원수',
    hovermode='x unified'
)

st.plotly_chart(fig1, use_container_width=True)


# -----------------------------------
# 8. 역별 승하차 인원 비교
# -----------------------------------
st.subheader('📊 역별 승하차 인원 비교')

station_summary = grouped.groupby(
    '역명'
)[['승차인원수', '하차인원수']].sum().reset_index()

station_long = station_summary.melt(
    id_vars='역명',
    var_name='구분',
    value_name='인원수'
)

fig2 = px.bar(
    station_long,
    x='역명',
    y='인원수',
    color='구분',
    barmode='group',
    title='역별 승차 및 하차 인원 비교'
)

fig2.update_layout(
    xaxis_title='역명',
    yaxis_title='인원수'
)

st.plotly_chart(fig2, use_container_width=True)


# -----------------------------------
# 9. 일별 승하차 인원 분석
#    역명 선택 없이 선택된 역 전체 합산
# -----------------------------------
st.subheader('🔍 일별 승하차 인원 분석')

detail = filtered.groupby(
    '운행일자'
)[['전철승차인원수', '전철하차인원수']].sum().reset_index()

detail = detail.rename(columns={
    '전철승차인원수': '승차인원수',
    '전철하차인원수': '하차인원수'
})

detail_long = detail.melt(
    id_vars='운행일자',
    var_name='구분',
    value_name='인원수'
)

fig3 = px.line(
    detail_long,
    x='운행일자',
    y='인원수',
    color='구분',
    markers=True,
    title='일별 승차 및 하차 인원'
)

fig3.update_layout(
    xaxis_title='운행일자',
    yaxis_title='인원수',
    hovermode='x unified'
)

st.plotly_chart(fig3, use_container_width=True)


# -----------------------------------
# 10. 데이터 표
# -----------------------------------
st.divider()

st.subheader('📋 역명 및 운행일자별 데이터')

st.dataframe(
    grouped,
    use_container_width=True
)

# CSV 다운로드
st.download_button(
    '📥 분석 데이터 다운로드',
    data=grouped.to_csv(
        index=False,
        encoding='utf-8-sig'
    ),
    file_name='승하차인원_분석.csv',
    mime='text/csv'
)

st.success('지하철 승하차 데이터 분석 완료!')
