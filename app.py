

import pandas as pd
import streamlit as st
import plotly.express as px
from io import BytesIO

# -----------------------------------
# 1. 페이지 설정
# -----------------------------------
st.set_page_config(
    page_title="지하철 승하차 분석",
    page_icon="🚇",
    layout="wide"
)

# -----------------------------------
# 2. 디자인 CSS
# -----------------------------------
st.markdown("""
<style>
    .stApp {
        background-color: #f5f7fb;
    }

    .main-title {
        background: linear-gradient(120deg, #14213d, #263f68);
        padding: 28px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
    }

    .main-title h1 {
        color: white;
        font-size: 30px;
        margin-bottom: 8px;
    }

    .main-title p {
        color: #dce6f5;
        font-size: 15px;
        margin-bottom: 0;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e5eaf2;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(30, 50, 80, 0.05);
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
        font-size: 15px;
    }

    .section-caption {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 15px;
    }

    div[data-testid="stDownloadButton"] button {
        background-color: #263f68;
        color: white;
        border-radius: 8px;
        border: none;
    }

    div[data-testid="stDownloadButton"] button:hover {
        background-color: #14213d;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------
# 3. 데이터 읽기 및 정제
# -----------------------------------
data_path = "raw.csv"


@st.cache_data
def load_data():

    raw = pd.read_csv(
        data_path,
        encoding="utf-16",
        skiprows=5
    )

    # 역명 컬럼명 변경
    if '역명' not in raw.columns and 'Unnamed: 5' in raw.columns:
        raw = raw.rename(columns={'Unnamed: 5': '역명'})

    clean = raw.drop_duplicates().copy()

    # 날짜 변환
    clean['운행일자'] = pd.to_datetime(
        clean['운행일자'].astype(str),
        format='%Y%m%d',
        errors='coerce'
    )

    # 숫자 변환
    for col in ['전철승차인원수', '전철하차인원수']:
        clean[col] = pd.to_numeric(
            clean[col].astype(str).str.replace(',', '', regex=False),
            errors='coerce'
        )

    clean['역명'] = clean['역명'].astype(str).str.strip()

    clean = clean.dropna(
        subset=[
            '운행일자',
            '전철승차인원수',
            '전철하차인원수'
        ]
    )

    clean = clean[clean['역명'] != '']

    return clean


try:
    clean = load_data()

except Exception as e:
    st.error(f"데이터를 불러오지 못했습니다: {e}")
    st.info("raw2.csv 파일이 app.py와 같은 폴더에 있는지 확인하세요.")
    st.stop()


# -----------------------------------
# 4. 제목 영역
# -----------------------------------
st.markdown("""
<div class="main-title">
    <h1>🚇 철도데이터 분석 대시보드</h1>
    <p>지하철 역별 · 날짜별 승차 및 하차 인원 통합 분석</p>
</div>
""", unsafe_allow_html=True)


# -----------------------------------
# 5. 사이드바 필터
# -----------------------------------
st.sidebar.markdown("## 🔎 분석 조건 설정")
st.sidebar.caption("조회할 역과 기간을 선택하세요.")

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


filtered = clean[
    (clean['역명'].isin(selected_station)) &
    (clean['운행일자'].dt.date >= date_start) &
    (clean['운행일자'].dt.date <= date_end)
].copy()

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()


# -----------------------------------
# 6. 주요 통계
# -----------------------------------
st.markdown("### 📌 주요 승하차 통계")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "총 승차 인원",
    f"{filtered['전철승차인원수'].sum():,.0f}명"
)

col2.metric(
    "총 하차 인원",
    f"{filtered['전철하차인원수'].sum():,.0f}명"
)

col3.metric(
    "분석 역 개수",
    f"{filtered['역명'].nunique()}개"
)

col4.metric(
    "운행일수",
    f"{filtered['운행일자'].nunique()}일"
)

st.caption(
    f"조회 기간: {date_start} ~ {date_end}  |  "
    f"선택 역: {len(selected_station)}개"
)


# -----------------------------------
# 7. 데이터 집계
# -----------------------------------
grouped = filtered.groupby(
    ['역명', '운행일자']
).agg(
    승차인원수=('전철승차인원수', 'sum'),
    하차인원수=('전철하차인원수', 'sum')
).reset_index()

# 날짜순 정렬
grouped = grouped.sort_values(
    ['운행일자', '역명']
)


# 날짜별 전체 합계
daily = grouped.groupby(
    '운행일자'
)[['승차인원수', '하차인원수']].sum().reset_index()

daily_long = daily.melt(
    id_vars='운행일자',
    var_name='구분',
    value_name='인원수'
)


# 역별 합계
station_summary = grouped.groupby(
    '역명'
)[['승차인원수', '하차인원수']].sum().reset_index()

station_long = station_summary.melt(
    id_vars='역명',
    var_name='구분',
    value_name='인원수'
)


# 일별 상세 집계
detail = filtered.groupby(
    '운행일자'
)[['전철승차인원수', '전철하차인원수']].sum().reset_index()

detail = detail.rename(columns={
    '전철승차인원수': '승차인원수',
    '전철하차인원수': '하차인원수'
})


# -----------------------------------
# 8. 엑셀 다운로드 함수
# -----------------------------------
def make_excel(data, sheet_name="분석데이터"):

    output = BytesIO()

    excel_data = data.copy()

    # 엑셀 날짜 표시에서 시간 제거
    if '운행일자' in excel_data.columns:
        excel_data['운행일자'] = pd.to_datetime(
            excel_data['운행일자']
        ).dt.strftime('%Y-%m-%d')

    with pd.ExcelWriter(
        output,
        engine='openpyxl'
    ) as writer:

        excel_data.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name
        )

        worksheet = writer.sheets[sheet_name]

        # 열 너비 자동 조정
        for column_cells in worksheet.columns:
            max_length = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )

            worksheet.column_dimensions[
                column_cells[0].column_letter
            ].width = min(max_length + 4, 25)

        # 첫 행 고정 및 필터
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions

    output.seek(0)

    return output.getvalue()


# -----------------------------------
# 9. 탭 구성
# -----------------------------------
st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 날짜별 승하차 인원 추이",
    "📊 역별 승하차 인원 비교",
    "🔍 일별 승하차 인원 분석",
    "📋 역명 및 운행일자별 데이터"
])


# -----------------------------------
# TAB 1. 날짜별 승하차 인원 추이
# -----------------------------------
with tab1:

    st.subheader("📈 날짜별 승하차 인원 추이")

    st.markdown(
        '<p class="section-caption">선택한 역 전체의 날짜별 승차 및 하차 인원 변화입니다.</p>',
        unsafe_allow_html=True
    )

    fig1 = px.line(
        daily_long,
        x='운행일자',
        y='인원수',
        color='구분',
        markers=True,
        color_discrete_sequence=['#3478c8', '#f29e4c'],
        title='일별 전철 승차 및 하차 인원'
    )

    fig1.update_layout(
        xaxis_title='운행일자',
        yaxis_title='인원수',
        hovermode='x unified',
        template='plotly_white',
        legend_title='구분',
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    st.markdown("#### 📋 날짜별 집계 데이터")
    st.dataframe(
        daily.assign(
            운행일자=daily['운행일자'].dt.strftime('%Y-%m-%d')
        ),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 날짜별 데이터 엑셀 다운로드",
        data=make_excel(daily, "날짜별승하차"),
        file_name="날짜별_승하차인원.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_daily"
    )


# -----------------------------------
# TAB 2. 역별 승하차 인원 비교
# -----------------------------------
with tab2:

    st.subheader("📊 역별 승하차 인원 비교")

    st.markdown(
        '<p class="section-caption">선택한 기간 동안 각 역의 승차 및 하차 인원을 비교합니다.</p>',
        unsafe_allow_html=True
    )

    fig2 = px.bar(
        station_long,
        x='역명',
        y='인원수',
        color='구분',
        barmode='group',
        color_discrete_sequence=['#3478c8', '#f29e4c'],
        title='역별 승차 및 하차 인원 비교'
    )

    fig2.update_layout(
        xaxis_title='역명',
        yaxis_title='인원수',
        template='plotly_white',
        legend_title='구분',
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    st.markdown("#### 📋 역별 집계 데이터")
    st.dataframe(
        station_summary,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 역별 데이터 엑셀 다운로드",
        data=make_excel(station_summary, "역별승하차"),
        file_name="역별_승하차인원.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_station"
    )


# -----------------------------------
# TAB 3. 일별 승하차 인원 분석
# -----------------------------------
with tab3:

    st.subheader("🔍 일별 승하차 인원 분석")

    st.markdown(
        '<p class="section-caption">역명 선택 없이 현재 필터에서 선택된 역들의 일별 승하차 인원을 합산합니다.</p>',
        unsafe_allow_html=True
    )

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
        color_discrete_sequence=['#3478c8', '#f29e4c'],
        title='일별 승차 및 하차 인원'
    )

    fig3.update_layout(
        xaxis_title='운행일자',
        yaxis_title='인원수',
        hovermode='x unified',
        template='plotly_white',
        legend_title='구분',
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    st.markdown("#### 📋 일별 상세 데이터")

    st.dataframe(
        detail.assign(
            운행일자=detail['운행일자'].dt.strftime('%Y-%m-%d')
        ),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 일별 상세 데이터 엑셀 다운로드",
        data=make_excel(detail, "일별상세"),
        file_name="일별_승하차_상세.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_detail"
    )


# -----------------------------------
# TAB 4. 역명 및 운행일자별 데이터
# -----------------------------------
with tab4:

    st.subheader("📋 역명 및 운행일자별 데이터")

    st.markdown(
        '<p class="section-caption">역과 날짜별 승차 및 하차 집계 결과입니다.</p>',
        unsafe_allow_html=True
    )

    # 화면 표시용 날짜 형식 변경: 시간 제거
    display_grouped = grouped.copy()

    display_grouped['운행일자'] = (
        display_grouped['운행일자'].dt.strftime('%Y-%m-%d')
    )

    st.dataframe(
        display_grouped,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 역명 및 운행일자별 데이터 엑셀 다운로드",
        data=make_excel(grouped, "역명별일자별"),
        file_name="역명_운행일자별_승하차인원.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_grouped"
    )


# -----------------------------------
# 10. 하단 안내
# -----------------------------------
st.divider()

st.caption(
    "🚇 지하철 승하차 분석 대시보드 | "
    "선택한 역과 운행일자 조건에 따라 분석 결과가 갱신됩니다."
)

