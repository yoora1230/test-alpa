from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="모의고사 성적", page_icon="📈", layout="wide")

SUBJECTS = ["국어", "수학", "영어", "과학", "사회"]
SCORE_COLUMNS = ["날짜", "시험명", *SUBJECTS]


def ensure_state() -> None:
    if "mock_scores" not in st.session_state or not isinstance(st.session_state.mock_scores, pd.DataFrame):
        st.session_state.mock_scores = pd.DataFrame(columns=SCORE_COLUMNS)
    else:
        st.session_state.mock_scores = st.session_state.mock_scores.reindex(columns=SCORE_COLUMNS)


def append_score(row: dict) -> None:
    new_df = pd.DataFrame([row], columns=SCORE_COLUMNS)
    if st.session_state.mock_scores.empty:
        st.session_state.mock_scores = new_df
    else:
        st.session_state.mock_scores = pd.concat(
            [st.session_state.mock_scores, new_df],
            ignore_index=True,
        )


ensure_state()
st.title("📈 모의고사 성적 확인")
st.caption("시험별 점수를 입력하면 과목별 변화와 평균을 확인할 수 있습니다.")

with st.form("score_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        exam_date = st.date_input("시험 날짜", value=date.today())
        exam_name = st.text_input("시험 이름", placeholder="예: 7월 전국연합")
    with col2:
        score_inputs = {}
        score_columns = st.columns(len(SUBJECTS))
        for index, subject in enumerate(SUBJECTS):
            with score_columns[index]:
                score_inputs[subject] = st.number_input(
                    subject,
                    min_value=0,
                    max_value=100,
                    value=70,
                    step=1,
                    key=f"score_{subject}",
                )

    submitted = st.form_submit_button("성적 추가", type="primary", width="stretch")

if submitted:
    clean_name = exam_name.strip() or f"{exam_date.isoformat()} 모의고사"
    append_score({"날짜": exam_date.isoformat(), "시험명": clean_name, **score_inputs})
    st.success("성적을 추가했습니다.")

score_df = st.session_state.mock_scores.copy().reset_index(drop=True)

if score_df.empty:
    st.info("아직 입력한 모의고사 성적이 없습니다.")
else:
    for subject in SUBJECTS:
        score_df[subject] = pd.to_numeric(score_df[subject], errors="coerce")
    score_df["평균"] = score_df[SUBJECTS].mean(axis=1).round(1)
    score_df["날짜_dt"] = pd.to_datetime(score_df["날짜"], errors="coerce")
    score_df = score_df.sort_values(["날짜_dt", "시험명"], na_position="last").reset_index(drop=True)

    latest = score_df.iloc[-1]
    metric_columns = st.columns(len(SUBJECTS) + 1)
    for index, subject in enumerate(SUBJECTS):
        delta = None
        if len(score_df) >= 2 and pd.notna(score_df.iloc[-2][subject]) and pd.notna(latest[subject]):
            delta = f"{latest[subject] - score_df.iloc[-2][subject]:+.0f}점"
        value = "-" if pd.isna(latest[subject]) else f"{latest[subject]:.0f}점"
        metric_columns[index].metric(subject, value, delta)
    metric_columns[-1].metric("평균", f"{latest['평균']:.1f}점")

    st.subheader("성적 변화")
    chart_df = score_df.dropna(subset=["날짜_dt"]).set_index("날짜_dt")[SUBJECTS]
    if chart_df.empty:
        st.info("그래프로 표시할 수 있는 날짜 기록이 없습니다.")
    else:
        st.line_chart(chart_df)

    st.subheader("전체 기록")
    display_df = score_df.drop(columns=["날짜_dt"]).reset_index(drop=True)
    st.dataframe(display_df, hide_index=True, width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "성적 CSV 다운로드",
            data=display_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="모의고사_성적.csv",
            mime="text/csv",
            width="stretch",
        )
    with col2:
        if st.button("가장 최근 입력 기록 삭제", width="stretch"):
            st.session_state.mock_scores = st.session_state.mock_scores.iloc[:-1].reset_index(drop=True)
            st.rerun()
