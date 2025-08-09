import os
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from openai import OpenAI

# ===============================
# ⚙️ OpenAI 클라이언트 설정 (최신 SDK)
# - Streamlit Secrets에 openai_api_key 가 있어야 함
# - 없으면 안내 메시지 출력
# ===============================
API_KEY = st.secrets.get("openai_api_key")
client = OpenAI(api_key=API_KEY) if API_KEY else None

# ===============================
# 🤖 수리 상담 함수
# - 최신 openai>=1.0.0 방식 사용
# - 키가 없거나 예외 발생 시 한국어 안내 반환
# ===============================

def get_repair_advice(query: str) -> str:
    if client is None:
        return "❗ OpenAI API 키가 설정되지 않았습니다. 관리자에게 문의해 주세요. (Secrets: openai_api_key)"

    system_prompt = (
        "You are an expert electronic device repair advisor. Please respond politely and professionally.\n\n"
        "Role and Response Rules:\n"
        "1. Assess repairability of electronic devices and provide solutions\n"
        "2. If repairable: Provide step-by-step repair instructions\n"
        "3. If unrepairable: Provide proper disposal procedures according to local regulations (likely South Korea)\n"
        "4. Even for highly repairable devices, offer to explain disposal procedures\n"
        "5. For off-topic queries: Explain your purpose and request appropriate questions\n"
        "6. End all responses with an offer to help with future queries\n\n"
        "Response Format:\n- Start with a list of possible solutions\n- Include disposal procedures if needed\n- End with offer for additional assistance"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"죄송합니다. 서비스 처리 중 오류가 발생했습니다: {e}\n다시 시도해 주시기 바랍니다."

# ===============================
# 🧭 Streamlit 페이지 설정 & 글로벌 스타일
# ===============================

st.set_page_config(page_title="E-Cycle Navi", layout="centered")

st.markdown(
    """
    <style>
        html, body, [class*="css"] { font-family: 'Pretendard', sans-serif; background-color: #f6f8fa; }
        .stButton>button { background-color: #1e88e5; color: white; font-weight: bold; border-radius: 8px; padding: 0.5em 1em; }
        .stButton>button:hover { background-color: #1565c0; }
        footer { visibility: hidden; }

        /* 카드 스타일 */
        .card-container { background-color: #e3f2fd; border-radius: 10px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); height: 130px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.25s ease; cursor: pointer; }
        .card-container:hover { background-color: #d0e7fb; transform: scale(1.015); box-shadow: 0 6px 16px rgba(0,0,0,0.12); }
        .card-container:hover .card-title { color: #0d47a1; }
        .card-title { font-weight: 700; font-size: 16px; color: #1565c0; transition: color 0.2s; }
        .card-text { font-size: 14px; color: #444; }
        .card-link { font-size: 13px; color: #1e88e5; text-decoration: none; }
        .card-link:hover { text-decoration: underline; }

        /* 플로팅 상담 버튼 */
        .floating-button { position: fixed; bottom: 25px; right: 25px; background-color: #1e88e5; color: white; border: none; border-radius: 25px; padding: 10px 20px; font-size: 15px; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.3); z-index: 1000; cursor: pointer; transition: background-color 0.3s; }
        .floating-button:hover { background-color: #1565c0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 상단 고정 배너
st.markdown(
    """
    <div style="position:sticky;top:0; background:white; padding:1rem; z-index:999; border-bottom:1px solid #ddd; text-align:center; margin-bottom: 1rem;">
        <h1 style="margin:0; font-size: 40px;">📦 E-Cycle Navi</h1>
        <p style="color:#555; margin:4px 0 0; font-size: 18px;">대전 중소폐가전 수거함 지도</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 플로팅 버튼 (챗봇 섹션으로 이동)
st.markdown(
    """
    <a href="#repair-chatbot"><button class="floating-button">🛠️ 수리 상담</button></a>
    """,
    unsafe_allow_html=True,
)

# 사이드바 가이드
with st.sidebar:
    st.header("📦 수거 가이드")
    st.markdown("**노트북**: ✅ 수거함 가능 / 🔋 배터리는 분리 배출")
    st.markdown("**TV**: ❌ 대형 폐기물 스티커 부착 후 배출")
    st.markdown("**전자레인지**: ✅ 수거함 가능")
    st.markdown("**밥솥**: ⚠️ 내솥 분리 (내솥은 일반쓰레기일 수 있음)")
    st.markdown("**가습기**: ❌ 생활폐기물")

# ===============================
# 📥 데이터 불러오기 (파일 변경 자동 반영 캐시)
# - 파일이 바뀌면 mtime이 달라져 캐시 무효화
# - 기본 전처리(공백 제거, 주소 통일, 자치구 추출, 결측 제거, 중복 제거)
# ===============================

@st.cache_data
def _load_data_cached(csv_path: str, file_mtime: float) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 컬럼 트림 & 주요 문자열 컬럼 공백 제거
    df.columns = df.columns.str.strip()
    for col in ["상호명", "수거장소(주소)"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # 주소 표준화 및 자치구 추출
    if "수거장소(주소)" in df.columns:
        df["수거장소(주소)"] = df["수거장소(주소)"].str.replace("대전광역시", "대전", regex=False)
        df["자치구"] = df["수거장소(주소)"].str.extract(r"(대전\s?\S+구)")

    # 결측 제거
    need_cols = [c for c in ["위도", "경도", "자치구"] if c in df.columns]
    df = df.dropna(subset=need_cols)

    # 중복 제거 (같은 장소 중복 표시 방지)
    subset_cols = [c for c in ["상호명", "수거장소(주소)", "위도", "경도"] if c in df.columns]
    if subset_cols:
        df = df.drop_duplicates(subset=subset_cols).reset_index(drop=True)

    return df

# 래퍼: 파일 존재/변경 체크 후 캐시 호출
def load_data(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        st.error(f"데이터 파일을 찾을 수 없습니다: {csv_path}")
        st.stop()
    mtime = os.path.getmtime(csv_path)
    return _load_data_cached(csv_path, mtime)

# 실제 로드
CSV_PATH = "daejeon_map.csv"
df = load_data(CSV_PATH)

# ===============================
# 🔎 필터 UI
# ===============================

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
    mask = (
        filtered_df["상호명"].str.contains(search_term, case=False, na=False)
        | filtered_df["수거장소(주소)"].str.contains(search_term, case=False, na=False)
    )
    filtered_df = filtered_df[mask]

st.markdown(f"🧺 총 **{len(filtered_df)}개**의 수거함이 검색되었습니다.")

# ===============================
# 🗺️ 지도 출력 (마커 클러스터)
# ===============================

if len(filtered_df) > 0:
    center_lat = filtered_df["위도"].mean()
    center_lon = filtered_df["경도"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in filtered_df.iterrows():
        kakao_url = f"https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}"
        popup_html = folium.Popup(
            html=f"""
                <div style=\"font-size:13px;\">
                    <b>{row['상호명']}</b><br>
                    <a href=\"{kakao_url}\" target=\"_blank\">🧭 길찾기</a>
                </div>
            """,
            max_width=180,
        )
        folium.Marker(
            location=[row["위도"], row["경도"]],
            popup=popup_html,
            tooltip=row["상호명"],
            icon=folium.Icon(color="cadetblue", icon="info-sign"),
        ).add_to(marker_cluster)

    st_folium(m, width=900, height=600)
else:
    st.info("조건에 맞는 수거함이 없습니다. 다른 검색어/자치구를 선택해 보세요.")

# ===============================
# 🗒️ 수거함 리스트 (2열 카드, 접힘 기본)
# ===============================

with st.expander("📋 수거함 리스트 (클릭 시 펼치기)", expanded=False):
    for i in range(0, len(filtered_df), 2):
        col1, col2 = st.columns(2)
        for idx, col in enumerate([col1, col2]):
            if i + idx < len(filtered_df):
                row = filtered_df.iloc[i + idx]
                kakao_url = f"https://map.kakao.com/link/map/{row['상호명']},{row['위도']},{row['경도']}"
                col.markdown(
                    f"""
                    <div class=\"card-container\">
                        <div class=\"card-title\">📌 {row['상호명']}</div>
                        <div class=\"card-text\">📍 {row['수거장소(주소)']}</div>
                        <a class=\"card-link\" href=\"{kakao_url}\" target=\"_blank\">🧭 길찾기 바로가기</a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ===============================
# 💬 챗봇 섹션 (플로팅 버튼이 이동하는 앵커)
# ===============================

st.markdown('<div id="repair-chatbot"></div>', unsafe_allow_html=True)

st.markdown("## 🤖 수리 챗봇 / Repair Chatbot")
if client is None:
    st.warning("OpenAI API 키가 설정되지 않아 챗봇을 사용할 수 없습니다. 관리자에게 문의해 주세요.")

st.markdown("전자기기 문제를 입력하면 수리가 가능한지 상담해드립니다.")
with st.form("repair_query_form", clear_on_submit=False):
    user_query = st.text_area(
        "전자기기 문제를 자세히 설명해 주세요 / Describe your electronic device problem:",
        placeholder="예: 스마트폰이 충전되지 않습니다 / Example: My smartphone won't charge",
        height=100,
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
