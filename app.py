import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(page_title="대전 중소폐가전 수거함 지도", layout="centered")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)
st.markdown("## 🗺️ 대전 중소폐가전 수거함 지도")
st.markdown("폐가전, 어디서 버려야 할지 몰랐다면? <br>이제는 쉽게 확인하고 지도에서 길찾기까지!", unsafe_allow_html=True)
st.markdown("---")

@st.cache_data
def load_data():
    df = pd.read_csv("daejeon_map.csv", encoding="utf-8-sig")
    return df.head(10)  # 샘플 10개만 사용

df = load_data()
df.columns = df.columns.str.strip()
df["자치구"] = df["수거장소(주소)"].str.extract(r"(대전\s?\w+구)")
df = df.dropna(subset=["위도", "경도"])

col1, col2 = st.columns([1, 2])
with col1:
    gu_list = df["자치구"].dropna().unique().tolist()
    gu_list.sort()
    selected_gu = st.selectbox("🏙️ 자치구 선택", gu_list)

with col2:
    search_term = st.text_input("🔍 수거함 이름 또는 주소 검색")

filtered_df = df[df["자치구"] == selected_gu]
if search_term:
    filtered_df = filtered_df[
        filtered_df["상호명"].str.contains(search_term, case=False, na=False)
        | filtered_df["수거장소(주소)"].str.contains(search_term, case=False, na=False)
    ]

st.markdown(f"🧺 총 **{len(filtered_df)}개**의 수거함이 검색되었습니다.")

if len(filtered_df) > 0:
    center_lat = filtered_df["위도"].mean()
    center_lon = filtered_df["경도"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in filtered_df.iterrows():
        kakao_url = f"https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}"
        popup_html = f"""
        <b>{row['상호명']}</b><br>
        📍 {row['수거장소(주소)']}<br>
        <a href="{kakao_url}" target="_blank">🧭 길찾기</a>
        """
        folium.Marker(
            location=[row["위도"], row["경도"]],
            popup=popup_html,
            tooltip=row["상호명"],
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(marker_cluster)

    st_data = st_folium(m, width=700, height=500)

with st.expander("📋 수거함 리스트 (클릭 시 펼치기)", expanded=True):
    for _, row in filtered_df.iterrows():
        st.markdown(
            f"""
            <div style="border:1px solid #add8e6;
                        border-radius:12px;
                        padding:15px;
                        margin:10px 0;
                        background-color:#e6f3ff;
                        box-shadow: 1px 1px 4px rgba(0,0,0,0.1);">
                <b>📌 {row['상호명']}</b><br>
                📍 {row['수거장소(주소)']}<br>
                <a href="https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}" target="_blank">🧭 길찾기 바로가기</a>
            </div>
            """,
            unsafe_allow_html=True
        )
