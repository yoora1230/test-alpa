from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from utils import SCORE_COLUMNS, SUBJECTS, apply_common_style, init_state

st.set_page_config(page_title="모의고사 점수", page_icon="📊", layout="wide")
init_state()
apply_common_style()

st.title("📊 모의고사 점수")
st.caption("과목별 점수를 기록하고 날짜에 따른 성적 변화를 확인하세요.")

with st.form("score_form"):
    col1, col2 = st.columns(2)
    exam_name = col1.text_input("시험명", placeholder="예: 6월 전국연합학력평가")
    exam_date = col2.date_input("응시일", value=date.today())

    selected_subjects = st.multiselect(
        "점수를 입력할 과목",
        SUBJECTS,
        default=["국어", "수학", "영어"],
    )

    entered_scores: dict[str, tuple[float, float]] = {}
    for subject in selected_subjects:
        score_col, max_col = st.columns(2)
        score = score_col.number_input(
            f"{subject} 점수",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=1.0,
            key=f"score_{subject}",
        )
        max_score = max_col.number_input(
            f"{subject} 만점",
            min_value=1.0,
            max_value=1000.0,
            value=100.0,
            step=1.0,
            key=f"max_{subject}",
        )
        entered_scores[subject] = (score, max_score)

    submitted = st.form_submit_button("성적 저장", width="stretch")

if submitted:
    if not exam_name.strip():
        st.error("시험명을 입력하세요.")
    elif not selected_subjects:
        st.error("과목을 한 개 이상 선택하세요.")
    else:
        rows = []
        for subject, (score, max_score) in entered_scores.items():
            if score > max_score:
                st.error(f"{subject} 점수는 만점보다 클 수 없습니다.")
                break
            rows.append(
                {
                    "시험명": exam_name.strip(),
                    "응시일": exam_date.isoformat(),
                    "과목": subject,
                    "점수": float(score),
                    "만점": float(max_score),
                    "환산점수": round(float(score) / float(max_score) * 100, 2),
                }
            )
        else:
            new_rows = pd.DataFrame(rows, columns=SCORE_COLUMNS)
            st.session_state.scores = pd.concat(
                [st.session_state.scores, new_rows],
                ignore_index=True,
            )
            st.success(f"{exam_name} 성적을 저장했습니다.")
            st.rerun()

scores = st.session_state.scores.copy()

if scores.empty:
    st.info("아직 저장된 성적이 없습니다.")
else:
    scores["환산점수"] = pd.to_numeric(scores["환산점수"], errors="coerce")
    scores["응시일_dt"] = pd.to_datetime(scores["응시일"], errors="coerce")

    filter_col1, filter_col2 = st.columns(2)
    subject_filter = filter_col1.multiselect(
        "과목 필터",
        sorted(scores["과목"].dropna().astype(str).unique()),
        default=sorted(scores["과목"].dropna().astype(str).unique()),
    )
    exam_filter = filter_col2.multiselect(
        "시험 필터",
        sorted(scores["시험명"].dropna().astype(str).unique()),
        default=sorted(scores["시험명"].dropna().astype(str).unique()),
    )

    filtered = scores[
        scores["과목"].astype(str).isin(subject_filter)
        & scores["시험명"].astype(str).isin(exam_filter)
    ].copy()

    latest_date = scores["응시일_dt"].max()
    latest_scores = scores[scores["응시일_dt"] == latest_date]
    latest_average = latest_scores["환산점수"].mean()
    overall_average = scores["환산점수"].mean()
    best_score = scores["환산점수"].max()

    m1, m2, m3 = st.columns(3)
    m1.metric("최근 시험 평균", f"{latest_average:.1f}점")
    m2.metric("전체 평균", f"{overall_average:.1f}점")
    m3.metric("최고 환산점수", f"{best_score:.1f}점")

    st.subheader("성적 변화")
    chart_data = (
        filtered.dropna(subset=["응시일_dt", "환산점수"])
        .pivot_table(
            index="응시일_dt",
            columns="과목",
            values="환산점수",
            aggfunc="mean",
        )
        .sort_index()
    )
    if chart_data.empty:
        st.info("선택한 조건에 해당하는 그래프 데이터가 없습니다.")
    else:
        st.line_chart(chart_data, y_label="환산점수", x_label="응시일")

    st.subheader("성적 기록")
    display_columns = ["시험명", "응시일", "과목", "점수", "만점", "환산점수"]
    st.dataframe(
        filtered.sort_values(["응시일_dt", "과목"], ascending=[False, True])[
            display_columns
        ],
        width="stretch",
        hide_index=True,
    )

    st.subheader("기록 삭제")
    exam_options = (
        scores[["시험명", "응시일"]]
        .drop_duplicates()
        .sort_values("응시일", ascending=False)
    )
    delete_labels = [
        f"{row['응시일']} | {row['시험명']}" for _, row in exam_options.iterrows()
    ]
    selected_delete = st.selectbox("삭제할 시험", delete_labels)
    if st.button("선택한 시험 삭제"):
        selected_date, selected_name = selected_delete.split(" | ", 1)
        keep = ~(
            (st.session_state.scores["응시일"].astype(str) == selected_date)
            & (st.session_state.scores["시험명"].astype(str) == selected_name)
        )
        st.session_state.scores = st.session_state.scores.loc[keep].reset_index(
            drop=True
        )
        st.success("선택한 시험 기록을 삭제했습니다.")
        st.rerun()
