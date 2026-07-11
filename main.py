import pandas as pd
import streamlit as st

st.set_page_config(page_title="시험 계획표", page_icon="📚", layout="wide")

SUBJECTS = ["국어", "수학", "영어", "과학", "사회"]
SCORE_COLUMNS = ["날짜", "시험명", *SUBJECTS]
WRONG_COLUMNS = ["날짜", "과목", "시험/교재", "문항", "오답유형", "메모", "해결"]
PLAN_COLUMNS = ["날짜", "요일", "과목", "학습1", "학습2", "학습3", "학습4", "학습5"]


def ensure_state() -> None:
    if "mock_scores" not in st.session_state or not isinstance(st.session_state.mock_scores, pd.DataFrame):
        st.session_state.mock_scores = pd.DataFrame(columns=SCORE_COLUMNS)
    else:
        st.session_state.mock_scores = st.session_state.mock_scores.reindex(columns=SCORE_COLUMNS)

    if "wrong_questions" not in st.session_state or not isinstance(st.session_state.wrong_questions, pd.DataFrame):
        st.session_state.wrong_questions = pd.DataFrame(columns=WRONG_COLUMNS)
    else:
        st.session_state.wrong_questions = st.session_state.wrong_questions.reindex(columns=WRONG_COLUMNS)

    if "study_plan" not in st.session_state or not isinstance(st.session_state.study_plan, pd.DataFrame):
        st.session_state.study_plan = pd.DataFrame(columns=PLAN_COLUMNS)
    else:
        st.session_state.study_plan = st.session_state.study_plan.reindex(columns=PLAN_COLUMNS)


def unresolved_counts(wrong_df: pd.DataFrame) -> dict[str, int]:
    result = {subject: 0 for subject in SUBJECTS}
    if wrong_df.empty:
        return result

    copied = wrong_df.copy()
    copied["해결"] = copied["해결"].fillna(False).astype(bool)
    counts = copied.loc[~copied["해결"], "과목"].value_counts()
    for subject in SUBJECTS:
        result[subject] = int(counts.get(subject, 0))
    return result


def expected_scores(score_df: pd.DataFrame, wrong_df: pd.DataFrame) -> pd.DataFrame:
    wrongs = unresolved_counts(wrong_df)
    rows = []

    for subject in SUBJECTS:
        recent = pd.Series(dtype=float)
        if not score_df.empty:
            copied = score_df.copy()
            copied["날짜"] = pd.to_datetime(copied["날짜"], errors="coerce")
            copied = copied.sort_values("날짜")
            recent = pd.to_numeric(copied[subject], errors="coerce").dropna().tail(3)

        average = float(recent.mean()) if not recent.empty else 70.0
        trend = float(recent.iloc[-1] - recent.iloc[-2]) if len(recent) >= 2 else 0.0
        prediction = max(0.0, min(100.0, average + trend * 0.35 - min(12.0, wrongs[subject] * 0.8)))
        rows.append({"과목": subject, "현재 예상점수": round(prediction, 1), "미해결 오답": wrongs[subject]})

    return pd.DataFrame(rows)


ensure_state()
score_df = st.session_state.mock_scores
wrong_df = st.session_state.wrong_questions
prediction_df = expected_scores(score_df, wrong_df)

st.title("📚 나만의 시험 계획표")
st.caption("모의고사 성적과 오답을 기록하고, 취약 과목을 반영한 연속 학습 계획을 만드세요.")

unsolved_total = 0
if not wrong_df.empty:
    solved_series = wrong_df["해결"].fillna(False).astype(bool)
    unsolved_total = int((~solved_series).sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("모의고사 기록", f"{len(score_df)}회")
col2.metric("전체 오답", f"{len(wrong_df)}문제")
col3.metric("미해결 오답", f"{unsolved_total}문제")
col4.metric("평균 예상점수", f"{prediction_df['현재 예상점수'].mean():.1f}점")

st.divider()
st.subheader("사용 순서")
st.markdown(
    """
1. **모의고사 성적**에서 시험별 점수를 입력합니다.  
2. **오답 기록**에서 틀린 문제와 해결 여부를 저장합니다.  
3. **날짜별 계획표**에서 시험 기간과 연속 학습 일수를 선택합니다.  
4. **현재 예상점수**에서 성적과 오답을 반영한 참고 점수를 확인합니다.
"""
)

st.subheader("과목별 현재 예상점수")
st.dataframe(prediction_df, hide_index=True, width="stretch")
st.info("입력 내용은 같은 브라우저 세션의 여러 페이지에서 공유됩니다. 세션이 완전히 종료되면 초기화될 수 있습니다.")
