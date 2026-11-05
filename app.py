import io
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="죽전관리역 승하차인원 데이터 대시보드",
    page_icon="🚇",
    layout="wide"
)

# -----------------------------
# 디자인
# -----------------------------
st.markdown("""
<style>
.stApp {background:#F4F8FC;}
.block-container {padding-top:1.8rem; max-width:1500px;}
.dashboard-title {
    background:linear-gradient(100deg,#A9D8F5,#DCC8F2,#F5C9D8);
    padding:22px 26px; border-radius:20px; color:#34495E;
    font-size:clamp(22px,3vw,34px); font-weight:800; margin-bottom:22px;
}
section[data-testid="stSidebar"] {background:#EDF6FC;}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background:#D8ECFA; color:#315A78; border:1px solid #B8DDF4; border-radius:8px;
}
button[data-baseweb="tab"] {
    background:#EAF3FA; border-radius:10px 10px 0 0; margin-right:5px;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background:#D7EAF8; color:#315A78; font-weight:700;
}
.stDownloadButton button {
    background:#D9ECF8; color:#315A78; border:1px solid #B8DDF4; border-radius:10px;
}
div[data-testid="stMetric"] {
    background:white; border:1px solid #E5EDF5;
    padding:clamp(10px,1.5vw,22px); border-radius:18px;
    min-width:0; overflow:visible; box-shadow:0 3px 12px rgba(100,130,160,.07);
}
div[data-testid="stMetricValue"] {width:100%; min-width:0;}
div[data-testid="stMetricValue"] > div {
    font-size:clamp(16px,2.2vw,34px) !important;
    white-space:normal !important; overflow:visible !important;
    text-overflow:clip !important; word-break:keep-all;
    overflow-wrap:anywhere; line-height:1.25;
}
div[data-testid="stMetricLabel"] {
    font-size:clamp(12px,1.1vw,16px) !important; white-space:normal !important;
}
div[data-testid="stDataFrame"] {border:1px solid #E5EDF5; border-radius:12px;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="dashboard-title">🚇 죽전관리역 승하차인원 데이터 대시보드</div>',
    unsafe_allow_html=True
)
st.caption("역별·날짜별 전철 승차 및 하차 인원을 확인할 수 있는 데이터 분석 대시보드입니다.")

# -----------------------------
# CSV 불러오기 및 정확한 열 지정
# -----------------------------
DATA_PATH = "raw.csv"

@st.cache_data
def load_data(file_path):
    # raw2.csv는 UTF-16이며, 상단 리포트 정보 뒤에 헤더가 있습니다.
    raw = pd.read_csv(file_path, encoding="utf-16", skiprows=5)
    raw.columns = [str(c).strip() for c in raw.columns]

    # 실제 파일 구조:
    # 운행일자, 전철선, 운행년월, Unnamed: 3,
    # 전철역(역코드), Unnamed: 5(역명), 운행요일구분,
    # Unnamed: 7, 전철하차인원수, 전철승차인원수
    if "Unnamed: 5" not in raw.columns:
        raise ValueError(
            "역명 열인 'Unnamed: 5'를 찾지 못했습니다. "
            f"읽은 열 이름: {list(raw.columns)}"
        )

    raw = raw.rename(columns={"Unnamed: 5": "역명"})

    required = [
        "운행일자", "역명",
        "전철승차인원수", "전철하차인원수"
    ]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(
            "필수 열이 없습니다: "
            + ", ".join(missing)
            + f"\n현재 열: {list(raw.columns)}"
        )

    # 필요한 열만 선택하고 중복 제거
    clean = raw[required].drop_duplicates().copy()

    # 날짜: 20180101 -> 날짜 형식
    clean["운행일자"] = pd.to_datetime(
        clean["운행일자"].astype(str).str.strip(),
        format="%Y%m%d",
        errors="coerce"
    )

    # 숫자 데이터의 쉼표 제거 후 숫자형 변환
    for col in ["전철승차인원수", "전철하차인원수"]:
        clean[col] = pd.to_numeric(
            clean[col].astype(str).str.replace(",", "", regex=False).str.strip(),
            errors="coerce"
        )

    # 역명은 Unnamed: 5 열에서 가져옴
    clean["역명"] = clean["역명"].astype(str).str.strip()

    # 날짜·역명·승하차 값이 유효한 행만 유지
    clean = clean.dropna(subset=[
        "운행일자", "전철승차인원수", "전철하차인원수"
    ])
    clean = clean[
        clean["역명"].notna()
        & (clean["역명"] != "")
        & (clean["역명"].str.lower() != "nan")
    ].copy()

    clean["운행일자"] = clean["운행일자"].dt.normalize()

    # 잘못된 역명 매핑이 다시 생기지 않도록 날짜 문자열/월 문자열 제외
    clean = clean[
        ~clean["역명"].str.match(r"^\d{4}([./-]\d{1,2})?$", na=False)
    ].copy()

    if clean.empty:
        raise ValueError("전처리 후 분석할 데이터가 없습니다.")

    return clean


try:
    df = load_data(DATA_PATH)
except FileNotFoundError:
    st.error("raw2.csv 파일을 찾을 수 없습니다. app.py와 같은 폴더에 넣어 주세요.")
    st.stop()
except Exception as e:
    st.error(f"데이터를 불러오는 중 문제가 발생했습니다: {e}")
    st.stop()

# -----------------------------
# 사이드바 필터
# -----------------------------
st.sidebar.markdown("## 🔎 데이터 조회 조건")
st.sidebar.caption("조회할 역과 기간을 선택하세요.")

station_list = sorted(df["역명"].unique().tolist())
selected_stations = st.sidebar.multiselect(
    "🏢 역명 선택",
    options=station_list,
    default=station_list,
    placeholder="조회할 역을 선택하세요"
)

min_date = df["운행일자"].min().date()
max_date = df["운행일자"].max().date()

selected_dates = st.sidebar.date_input(
    "📅 운행일자 선택",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(selected_dates, (tuple, list)):
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date, end_date = min_date, max_date
else:
    start_date = end_date = selected_dates

if not selected_stations:
    st.warning("사이드바에서 역명을 한 개 이상 선택해 주세요.")
    st.stop()

filtered = df[
    df["역명"].isin(selected_stations)
    & (df["운행일자"].dt.date >= start_date)
    & (df["운행일자"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# -----------------------------
# 주요 통계
# -----------------------------
st.markdown("### 📌 주요 승하차 통계")
c1, c2, c3, c4 = st.columns(4, gap="small")
c1.metric("🩵 총 승차 인원", f"{filtered['전철승차인원수'].sum():,.0f}명")
c2.metric("🌸 총 하차 인원", f"{filtered['전철하차인원수'].sum():,.0f}명")
c3.metric("🏢 분석 역 개수", f"{filtered['역명'].nunique():,}개")
c4.metric("📅 운행일수", f"{filtered['운행일자'].nunique():,}일")
st.divider()

# -----------------------------
# 집계
# -----------------------------
daily = (
    filtered.groupby("운행일자", as_index=False)[
        ["전철승차인원수", "전철하차인원수"]
    ].sum().sort_values("운행일자")
)

station = (
    filtered.groupby("역명", as_index=False)[
        ["전철승차인원수", "전철하차인원수"]
    ].sum().sort_values("전철승차인원수", ascending=False)
)

grouped = (
    filtered.groupby(["역명", "운행일자"], as_index=False)[
        ["전철승차인원수", "전철하차인원수"]
    ].sum().sort_values(["역명", "운행일자"])
)

BLUE = "#9BCFF0"
PINK = "#F2B6CC"
COLOR_MAP = {"승차인원수": BLUE, "하차인원수": PINK}

def make_long(data, index_col):
    result = data.melt(
        id_vars=[index_col],
        value_vars=["전철승차인원수", "전철하차인원수"],
        var_name="구분",
        value_name="인원수"
    )
    result["구분"] = result["구분"].map({
        "전철승차인원수": "승차인원수",
        "전철하차인원수": "하차인원수"
    })
    return result

def make_excel(data, sheet_name):
    output = io.BytesIO()
    export = data.copy()
    if "운행일자" in export.columns:
        export["운행일자"] = pd.to_datetime(
            export["운행일자"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()

# -----------------------------
# 탭 1~4
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 날짜별 승하차 인원 추이",
    "🏢 역별 승하차 인원 비교",
    "📅 일별 승하차 인원 분석",
    "📋 역명 및 운행일자별 데이터"
])

with tab1:
    st.subheader("날짜별 승하차 인원 추이")
    daily_long = make_long(daily, "운행일자")
    fig = px.line(
        daily_long, x="운행일자", y="인원수", color="구분",
        markers=True, color_discrete_map=COLOR_MAP,
        labels={"운행일자":"운행일자", "인원수":"인원수(명)", "구분":"구분"}
    )
    fig.update_layout(
        hovermode="x unified", plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)", legend_title_text=""
    )
    st.plotly_chart(fig, use_container_width=True)
    st.download_button(
        "📥 날짜별 승하차 통계 Excel 다운로드",
        data=make_excel(daily, "날짜별 통계"),
        file_name="날짜별_승하차_통계.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_daily"
    )

with tab2:
    st.subheader("역별 승하차 인원 비교")
    station_long = make_long(station, "역명")
    fig = px.bar(
        station_long, x="역명", y="인원수", color="구분",
        barmode="group", color_discrete_map=COLOR_MAP,
        labels={"역명":"역명", "인원수":"인원수(명)", "구분":"구분"}
    )
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend_title_text="", xaxis_tickangle=-35
    )
    st.plotly_chart(fig, use_container_width=True)
    st.download_button(
        "📥 역별 승하차 통계 Excel 다운로드",
        data=make_excel(station, "역별 통계"),
        file_name="역별_승하차_통계.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_station"
    )

with tab3:
    st.subheader("일별 승하차 인원 분석")
    st.caption("선택한 역 전체의 날짜별 승차 및 하차 인원을 합산합니다.")
    fig = px.bar(
        daily_long, x="운행일자", y="인원수", color="구분",
        barmode="group", color_discrete_map=COLOR_MAP,
        labels={"운행일자":"운행일자", "인원수":"인원수(명)", "구분":"구분"}
    )
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend_title_text="", xaxis_tickangle=-35
    )
    st.plotly_chart(fig, use_container_width=True)
    st.download_button(
        "📥 일별 승하차 분석 Excel 다운로드",
        data=make_excel(daily, "일별 분석"),
        file_name="일별_승하차_분석.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_daily_analysis"
    )

with tab4:
    st.subheader("역명 및 운행일자별 승하차 데이터")
    display = grouped.copy()
    display["운행일자"] = display["운행일자"].dt.strftime("%Y-%m-%d")
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 역명 및 운행일자별 데이터 Excel 다운로드",
        data=make_excel(grouped, "역명_운행일자별"),
        file_name="역명_운행일자별_승하차_데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_grouped"
    )

# -----------------------------
# 원본 데이터 미리보기
# -----------------------------
with st.expander("원본 데이터 미리보기"):
    st.write(f"필터링된 데이터 행 수: {len(filtered):,}행")
    preview_num = st.slider(
        "표시할 행 수",
        min_value=5,
        max_value=min(100, max(5, len(filtered))),
        value=min(10, max(5, len(filtered))),
        step=5
    )
    st.dataframe(
        filtered.head(preview_num),
        use_container_width=True,
        hide_index=True
    )
    st.download_button(
        "📥 필터링된 원본 데이터 Excel 다운로드",
        data=make_excel(filtered, "필터링 원본"),
        file_name="필터링된_승하차_원본데이터.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_filtered"
    )

st.caption("※ 분석 결과는 선택한 역명과 운행일자 조건을 기준으로 집계됩니다.")
