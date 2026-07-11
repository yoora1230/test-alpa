from datetime import date

import pandas as pd
import streamlit as st

from common import MOCK_COLUMNS, SUBJECTS, init_state

st.set_page_config(page_title="모의고사 성적", page_icon="📈", layout="wide")
init_state()

st.title("📈 모의고사 성적 확인")
st.caption("시험별 점수를 입력하면 과목별 변화와 평균을 확인할 수 있습니다.")

with st.form("score_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        exam_date = st.date_input("시험 날짜", value=date.today())
        exam_name = st.text_input("시험 이름", placeholder="예: 7월 전국연합")
    with col2:
        score_inputs = {}
        score_cols = st.columns(len(SUBJECTS))
        for idx, subject in enumerate(SUBJECTS):
            with score_cols[idx]:
                score_inputs[subject] = st.number_input(
                    subject,
                    min_value=0,
                    max_value=100,
                    value=70,
                    step=1,
                    key=f"score_{subject}",
                )

    add_score = st.form_submit_button("성적 추가", type="primary", use_container_width=True)

if add_score:
    clean_name = exam_name.strip() or f"{exam_date.isoformat()} 모의고사"
    new_row = {"날짜": exam_date.isoformat(), "시험명": clean_name, **score_inputs}
    st.session_state.mock_scores = pd.concat(
        [st.session_state.mock_scores, pd.DataFrame([new_row], columns=MOCK_COLUMNS)],
        ignore_index=True,
    )
    st.success("성적을 추가했습니다.")

score_df = st.session_state.mock_scores.copy()

if score_df.empty:
    st.info("아직 입력한 모의고사 성적이 없습니다.")
else:
    for subject in SUBJECTS:
        score_df[subject] = pd.to_numeric(score_df[subject], errors="coerce")
    score_df["평균"] = score_df[SUBJECTS].mean(axis=1).round(1)
    score_df = score_df.sort_values("날짜").reset_index(drop=True)

    latest = score_df.iloc[-1]
    metric_cols = st.columns(len(SUBJECTS) + 1)
    for idx, subject in enumerate(SUBJECTS):
        previous = score_df.iloc[-2][subject] if len(score_df) >= 2 else None
        delta = None if previous is None else f"{latest[subject] - previous:+.0f}점"
        metric_cols[idx].metric(subject, f"{latest[subject]:.0f}점", delta)
    metric_cols[-1].metric("평균", f"{latest['평균']:.1f}점")

    st.subheader("성적 변화")
    chart_df = score_df[["날짜", *SUBJECTS]].copy()
    chart_df["날짜"] = pd.to_datetime(chart_df["날짜"], errors="coerce")
    chart_df = chart_df.dropna(subset=["날짜"])
    if not chart_df.empty:
        st.line_chart(chart_df, x="날짜", y=SUBJECTS)

    st.subheader("전체 기록")
    st.dataframe(score_df, hide_index=True, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "성적 CSV 다운로드",
            data=score_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="모의고사_성적.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        if st.button("가장 최근 기록 삭제", use_container_width=True):
            st.session_state.mock_scores = st.session_state.mock_scores.iloc[:-1].reset_index(drop=True)
            st.rerun()
