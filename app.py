import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import openai
from openai import OpenAI

# ✅ OpenAI API 설정 (환경에 따라 설정 방식 변경 가능)
openai.api_key = st.secrets["openai_api_key"] if "openai_api_key" in st.secrets else "sk-YourAPIKeyHere"

# ✅ 수리 상담 함수 정의
def get_repair_advice(query):
    try:
        system_prompt = """You are an expert electronic device repair advisor. Please respond politely and professionally.

Role and Response Rules:
1. Assess repairability of electronic devices and provide solutions
2. If repairable: Provide step-by-step repair instructions
3. If unrepairable: Provide proper disposal procedures according to local regulations (likely South Korea)
4. Even for highly repairable devices, offer to explain disposal procedures
5. For off-topic queries: Explain your purpose and request appropriate questions
6. End all responses with an offer to help with future queries

Response Format:
- Start with a list of possible solutions
- Include disposal procedures if needed
- End with offer for additional assistance"""

        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"죄송합니다. 서비스 처리 중 오류가 발생했습니다: {str(e)}\n다시 시도해 주시기 바랍니다."

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

        /* ▼▼▼ 추가된: 플로팅 상담 버튼 스타일 ▼▼▼ */
        .floating-button {
            position: fixed;
            bottom: 25px;
            right: 25px;
            background-color: #1e88e5;
            color: white;
            border: none;
            border-radius: 25px;
            padding: 10px 20px;
            font-size: 15px;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            z-index: 1000;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .floating-button:hover {
            background-color: #1565c0;
        }
        /* ▲▲▲ 추가된 부분 끝 ▲▲▲ */
    </style>
""", unsafe_allow_html=True)

# ✅ 상단 고정 배너 (크기 시원하게 키운 버전)
st.markdown("""
<div style="position:sticky;top:0; background:white; padding:1rem; z-index:999; border-bottom:1px solid #ddd; text-align:center; margin-bottom: 1rem;">
    <h1 style="margin:0; font-size: 40px;">📦 E-Cycle Navi</h1>
    <p style="color:#555; margin:4px 0 0; font-size: 18px;">대전 중소폐가전 수거함 지도</p>
</div>
""", unsafe_allow_html=True)

# ✅ 플로팅 버튼 추가 (하단 고정 상담 이동 버튼)
st.markdown("""
<a href="#repair-chatbot">
    <button class="floating-button">🛠️ 수리 상담</button>
</a>
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
def load_data():
    df = pd.read_csv("daejeon_map.csv", encoding="utf-8-sig")
    return df

df = load_data()
df.columns = df.columns.str.strip()
df["수거장소(주소)"] = df["수거장소(주소)"].str.replace("대전광역시", "대전", regex=False)
df["자치구"] = df["수거장소(주소)"].str.extract(r"(대전\s?\S+구)")
df = df.dropna(subset=["위도", "경도", "자치구"])

# ✅ 필터 UI
st.markdown('<h4 style="margin-bottom: px;">🏙️ 자치구 선택</h4>', unsafe_allow_html=True)

gu_list = ["전체"] + sorted(df["자치구"].dropna().unique().tolist())
selected_gu = st.radio("", gu_list, horizontal=True)

st.markdown('<p style="font-size: 15px; margin-top: 20px;">🔍 수거함 이름 또는 주소 검색</p>', unsafe_allow_html=True)
search_term = st.text_input("", label_visibility="collapsed")

if selected_gu == "전체":
    filtered_df = df.copy()
else:
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
                    <a href=\"{kakao_url}\" target=\"_blank\">🧭 길찾기</a>
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
with st.expander("📋 수거함 리스트 (클릭 시 펼치기)", expanded=False):
    for i in range(0, len(filtered_df), 2):
        col1, col2 = st.columns(2)

        for idx, col in enumerate([col1, col2]):
            if i + idx < len(filtered_df):
                row = filtered_df.iloc[i + idx]
                with col:
                    kakao_url = f"https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}"
                    st.markdown(f"""
                        <div class=\"card-container\">
                            <div class=\"card-title\">📌 {row['상호명']}</div>
                            <div class=\"card-text\">📍 {row['수거장소(주소)']}</div>
                            <a class=\"card-link\" href=\"{kakao_url}\" target=\"_blank\">🧭 길찾기 바로가기</a>
                        </div>
                    """, unsafe_allow_html=True)

# ✅ 아래 챗봇 구역 이동용 ID 태그 추가
st.markdown('<div id="repair-chatbot"></div>', unsafe_allow_html=True)

# ✅ 챗봇 입력 폼
st.markdown("## 🤖 수리 챗봇 / Repair Chatbot")
st.markdown("전자기기 문제를 입력하면 수리가 가능한지 상담해드립니다.")

with st.form("repair_query_form", clear_on_submit=False):
    user_query = st.text_area(
        "전자기기 문제를 자세히 설명해 주세요 / Describe your electronic device problem:",
        placeholder="예: 스마트폰이 충전되지 않습니다 / Example: My smartphone won't charge",
        height=100
    )
    submitted = st.form_submit_button("▶ 상담받기 / Get Advice", use_container_width=True)

if submitted:
    if user_query.strip():
        with st.spinner("답변을 생성하고 있습니다... / Generating response..."):
            advice = get_repair_advice(user_query)

        st.markdown("### 📋 수리 상담 결과 / Repair Consultation Result")
        st.markdown(advice)
        st.divider()
        st.markdown("#### 💬 이 답변이 도움이 되셨나요? / Was this answer helpful?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 도움됨 / Helpful", use_container_width=True):
                st.success("피드백 감사합니다! / Thank you for your feedback!")
        with col2:
            if st.button("👎 개선필요 / Needs improvement", use_container_width=True):
                st.info("더 나은 서비스를 위해 노력하겠습니다! / We'll work to improve our service!")
    else:
        st.warning("질문을 입력해 주세요. / Please enter your question.")
