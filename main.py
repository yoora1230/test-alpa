import streamlit as st

from common import SUBJECTS, current_expected_scores, init_state

st.set_page_config(
    page_title="시험 계획표",
    page_icon="📚",
    layout="wide",
)

init_state()

st.title("📚 나만의 시험 계획표")
st.caption("모의고사 성적과 오답을 기록하고, 취약 과목을 반영한 연속 학습 계획을 만들어 보세요.")

score_df = st.session_state.mock_scores
wrong_df = st.session_state.wrong_questions
expected_df = current_expected_scores(score_df, wrong_df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("모의고사 기록", f"{len(score_df)}회")
col2.metric("전체 오답 기록", f"{len(wrong_df)}문제")
col3.metric(
    "미해결 오답",
    f"{int((~wrong_df['해결'].fillna(False).astype(bool)).sum()) if not wrong_df.empty else 0}문제",
)
col4.metric("평균 예상점수", f"{expected_df['현재 예상점수'].mean():.1f}점")

st.divider()

st.subheader("사용 순서")
st.markdown(
    """
1. **모의고사 성적** 페이지에서 과목별 점수를 입력합니다.  
2. **오답 기록** 페이지에서 틀린 문제와 오답 유형을 저장합니다.  
3. **날짜별 계획표** 페이지에서 시험 기간과 연속 학습 일수를 정해 달력형 계획표를 만듭니다.  
4. **현재 예상점수** 페이지에서 최근 성적과 미해결 오답을 반영한 예상점수를 확인합니다.
"""
)

st.info(
    "이 버전은 서버 파일을 직접 수정하지 않고 Session State만 사용하므로, "
    "Streamlit Cloud에서 폴더 생성 권한 오류가 발생하지 않습니다. "
    "다만 브라우저 세션이 종료되면 입력 내용이 초기화될 수 있습니다."
)

st.subheader("과목별 현재 예상점수")
st.dataframe(
    expected_df[["과목", "현재 예상점수", "미해결 오답"]],
    hide_index=True,
    use_container_width=True,
)

st.caption("왼쪽 사이드바에서 원하는 페이지를 선택하세요.")
