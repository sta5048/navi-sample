import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# ✅ 페이지 설정
st.set_page_config(page_title="E-Cycle Navi", layout="centered")

# ✅ 스타일 커스터마이징 (hover 효과 포함)
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
            background-color: #f6f8fa;
        }

        .stButton>button {
            background-color: #1e88e5;
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 0.5em 1em;
        }

        .stButton>button:hover {
            background-color: #1565c0;
        }

        footer {visibility: hidden;}

        /* ✅ 카드 스타일 & 호버 효과 */
        .card-container {
            background-color: #e3f2fd;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.25s ease;
            cursor: pointer;
        }

        .card-container:hover {
            background-color: #d0e7fb;
            transform: scale(1.015);
            box-shadow: 0 6px 16px rgba(0,0,0,0.12);
        }

        .card-container:hover .card-title {
            color: #0d47a1;
        }

        .card-title {
            font-weight: 700;
            font-size: 16px;
            color: #1565c0;
            transition: color 0.2s;
        }

        .card-text {
            font-size: 14px;
            color: #444;
        }

        .card-link {
            font-size: 13px;
            color: #1e88e5;
            text-decoration: none;
        }

        .card-link:hover {
            text-decoration: underline;
        }
    </style>
""", unsafe_allow_html=True)
# ✅ 상단 고정 배너 (크기 시원하게 키운 버전)
st.markdown("""
<div style="position:sticky;top:0; background:white; padding:1rem; z-index:999; border-bottom:1px solid #ddd; text-align:center; margin-bottom: 1rem;">
    <h1 style="margin:0; font-size: 40px;">📦 E-Cycle Navi</h1>
    <p style="color:#555; margin:4px 0 0; font-size: 18px;">대전 중소폐가전 수거함 지도</p>
</div>
""", unsafe_allow_html=True)

# ✅ 사이드바
with st.sidebar:
    st.header("📦 수거 가이드")
    st.markdown("**노트북**: ✅ 수거함 가능 / 🔋 배터리는 분리 배출")
    st.markdown("**TV**: ❌ 대형 폐기물 스티커 부착 후 배출")
    st.markdown("**전자레인지**: ✅ 수거함 가능")
    st.markdown("**밥솥**: ⚠️ 내솥 분리 (내솥은 일반쓰레기일 수 있음)")
    st.markdown("**가습기**: ❌ 생활폐기물")

# ✅ 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_csv("daejeon_map.csv", encoding="utf-8-sig")
    return df

df = load_data()
df.columns = df.columns.str.strip()
df["수거장소(주소)"] = df["수거장소(주소)"].str.replace("대전광역시", "대전", regex=False)
df["자치구"] = df["수거장소(주소)"].str.extract(r"(대전\s?\S+구)")
df = df.dropna(subset=["위도", "경도", "자치구"])

# ✅ 필터 UI
col1, col2 = st.columns([1, 2])
with col1:
    gu_list = sorted(df["자치구"].dropna().unique())
selected_gu = st.radio("🏙️ 자치구 선택", gu_list, horizontal=True)

with col2:
    search_term = st.text_input("🔍 수거함 이름 또는 주소 검색")

filtered_df = df[df["자치구"] == selected_gu]
if search_term:
    filtered_df = filtered_df[
        filtered_df["상호명"].str.contains(search_term, case=False, na=False)
        | filtered_df["수거장소(주소)"].str.contains(search_term, case=False, na=False)
    ]

st.markdown(f"🧺 총 **{len(filtered_df)}개**의 수거함이 검색되었습니다.")


# ✅ 지도 출력
if len(filtered_df) > 0:
    center_lat = filtered_df["위도"].mean()
    center_lon = filtered_df["경도"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in filtered_df.iterrows():
        kakao_url = f"https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}"
        popup_html = folium.Popup(
            html=f"""
                <div style="font-size:13px;">
                    <b>{row['상호명']}</b><br>
                    <a href="{kakao_url}" target="_blank">🧭 길찾기</a>
                </div>
            """,
            max_width=180
        )

        folium.Marker(
            location=[row["위도"], row["경도"]],
	    popup=popup_html,
  	    tooltip=row["상호명"],
 	    icon=folium.Icon(color="cadetblue", icon="info-sign"),
).add_to(marker_cluster)


    st_folium(m, width=900, height=600)

# ✅ 수거함 리스트 (2개씩 정렬)
with st.expander("📋 수거함 리스트 (클릭 시 펼치기)", expanded=True):
    for i in range(0, len(filtered_df), 2):
        col1, col2 = st.columns(2)

        for idx, col in enumerate([col1, col2]):
            if i + idx < len(filtered_df):
                row = filtered_df.iloc[i + idx]
                with col:
                    kakao_url = f"https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}"
                    st.markdown(f"""
                        <div class="card-container">
    <div class="card-title">📌 {row['상호명']}</div>
    <div class="card-text">📍 {row['수거장소(주소)']}</div>
    <a class="card-link" href="{kakao_url}" target="_blank">🧭 길찾기 바로가기</a>
</div>

                    """, unsafe_allow_html=True)
