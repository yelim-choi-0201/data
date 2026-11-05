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
