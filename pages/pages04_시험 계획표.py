import pandas as pd
import streamlit as st

st.set_page_config(page_title="현재 예상점수", page_icon="🎯", layout="wide")

SUBJECTS = ["국어", "수학", "영어", "과학", "사회"]
SCORE_COLUMNS = ["날짜", "시험명", *SUBJECTS]
WRONG_COLUMNS = ["날짜", "과목", "시험/교재", "문항", "오답유형", "메모", "해결"]


def ensure_state() -> None:
    if "mock_scores" not in st.session_state or not isinstance(st.session_state.mock_scores, pd.DataFrame):
        st.session_state.mock_scores = pd.DataFrame(columns=SCORE_COLUMNS)
    else:
        st.session_state.mock_scores = st.session_state.mock_scores.reindex(columns=SCORE_COLUMNS)

    if "wrong_questions" not in st.session_state or not isinstance(st.session_state.wrong_questions, pd.DataFrame):
        st.session_state.wrong_questions = pd.DataFrame(columns=WRONG_COLUMNS)
    else:
        st.session_state.wrong_questions = st.session_state.wrong_questions.reindex(columns=WRONG_COLUMNS)


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


def calculate_predictions(score_df: pd.DataFrame, wrong_df: pd.DataFrame) -> pd.DataFrame:
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
        penalty = min(12.0, wrongs[subject] * 0.8)
        predicted = max(0.0, min(100.0, average + trend * 0.35 - penalty))

        rows.append(
            {
                "과목": subject,
                "최근 3회 평균": round(average, 1),
                "최근 추세": round(trend, 1),
                "미해결 오답": wrongs[subject],
                "현재 예상점수": round(predicted, 1),
            }
        )

    return pd.DataFrame(rows)


ensure_state()
st.title("🎯 현재 나의 예상점수")
st.caption("최근 최대 3회의 모의고사 성적, 점수 추세, 미해결 오답 수를 바탕으로 계산한 참고용 점수입니다.")

expected_df = calculate_predictions(
    st.session_state.mock_scores,
    st.session_state.wrong_questions,
)

metric_columns = st.columns(len(SUBJECTS))
for index, row in expected_df.iterrows():
    metric_columns[index].metric(
        row["과목"],
        f"{row['현재 예상점수']:.1f}점",
        f"미해결 {int(row['미해결 오답'])}개",
        delta_color="off",
    )

st.subheader("예상점수 비교")
chart_df = expected_df.set_index("과목")[["최근 3회 평균", "현재 예상점수"]]
st.bar_chart(chart_df)

st.subheader("계산 결과")
st.dataframe(expected_df.reset_index(drop=True), hide_index=True, width="stretch")

weakest = expected_df.sort_values(["현재 예상점수", "미해결 오답"], ascending=[True, False]).iloc[0]
strongest = expected_df.sort_values("현재 예상점수", ascending=False).iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.warning(
        f"우선 보완 과목: **{weakest['과목']}** · 예상 {weakest['현재 예상점수']:.1f}점 · "
        f"미해결 오답 {int(weakest['미해결 오답'])}개"
    )
with col2:
    st.success(f"현재 강점 과목: **{strongest['과목']}** · 예상 {strongest['현재 예상점수']:.1f}점")

st.info(
    "계산식: 최근 3회 평균 + 최근 점수 변화의 35% − 미해결 오답 1개당 0.8점(최대 12점). "
    "실제 시험 점수를 보장하는 모델이 아니라 학습 우선순위를 정하기 위한 참고 지표입니다."
)

if st.session_state.mock_scores.empty:
    st.warning("모의고사 성적이 없어 과목별 기본값 70점을 사용했습니다. 먼저 성적을 입력하면 더 알맞게 계산됩니다.")
