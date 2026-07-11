from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils import SUBJECTS, WRONG_COLUMNS, apply_common_style, init_state

st.set_page_config(page_title="오답 노트", page_icon="📝", layout="wide")
init_state()
apply_common_style()

st.title("📝 오답 노트")
st.caption("틀린 문제의 원인을 기록하고 복습 상태를 관리하세요.")

exam_names = sorted(
    st.session_state.scores["시험명"].dropna().astype(str).unique().tolist()
) if not st.session_state.scores.empty else []

with st.form("wrong_answer_form"):
    col1, col2, col3 = st.columns(3)
    known_exam = col1.selectbox(
        "저장된 시험 선택",
        ["직접 입력"] + exam_names,
    )
    custom_exam = col2.text_input(
        "시험명 직접 입력",
        disabled=known_exam != "직접 입력",
        placeholder="예: 수학 단원평가",
    )
    subject = col3.selectbox("과목", SUBJECTS)

    col4, col5, col6 = st.columns(3)
    question_number = col4.text_input("문제 번호", placeholder="예: 18번")
    question_type = col5.text_input("문제 유형", placeholder="예: 이차함수 그래프")
    review_date = col6.date_input(
        "다음 복습일",
        value=date.today() + timedelta(days=3),
    )

    cause = st.selectbox(
        "오답 원인",
        [
            "개념 부족",
            "계산 실수",
            "문제 해석 실수",
            "시간 부족",
            "암기 부족",
            "조건 누락",
            "기타",
        ],
    )
    key_point = st.text_area(
        "정답 또는 다시 기억할 핵심",
        placeholder="정답뿐 아니라 다음에는 어떻게 풀어야 하는지도 적어보세요.",
    )
    status = st.selectbox(
        "복습 상태",
        ["미복습", "1차 복습", "복습 완료", "완전히 이해"],
    )

    submitted = st.form_submit_button("오답 저장", width="stretch")

if submitted:
    exam_name = custom_exam.strip() if known_exam == "직접 입력" else known_exam
    if not exam_name:
        st.error("시험명을 입력하세요.")
    elif not question_number.strip():
        st.error("문제 번호를 입력하세요.")
    else:
        new_row = pd.DataFrame(
            [
                {
                    "등록일": date.today().isoformat(),
                    "시험명": exam_name,
                    "과목": subject,
                    "문제 번호": question_number.strip(),
                    "문제 유형": question_type.strip(),
                    "오답 원인": cause,
                    "정답/핵심": key_point.strip(),
                    "복습 상태": status,
                    "다음 복습일": review_date.isoformat(),
                }
            ],
            columns=WRONG_COLUMNS,
        )
        st.session_state.wrong_answers = pd.concat(
            [st.session_state.wrong_answers, new_row],
            ignore_index=True,
        )
        st.success("오답을 저장했습니다.")
        st.rerun()

wrong_answers = st.session_state.wrong_answers.copy()

if wrong_answers.empty:
    st.info("아직 저장된 오답이 없습니다.")
else:
    filter1, filter2, filter3 = st.columns(3)
    subject_options = sorted(wrong_answers["과목"].dropna().astype(str).unique())
    cause_options = sorted(wrong_answers["오답 원인"].dropna().astype(str).unique())
    status_options = sorted(wrong_answers["복습 상태"].dropna().astype(str).unique())

    selected_subjects = filter1.multiselect(
        "과목 필터", subject_options, default=subject_options
    )
    selected_causes = filter2.multiselect(
        "오답 원인 필터", cause_options, default=cause_options
    )
    selected_status = filter3.multiselect(
        "복습 상태 필터", status_options, default=status_options
    )

    filtered = wrong_answers[
        wrong_answers["과목"].astype(str).isin(selected_subjects)
        & wrong_answers["오답 원인"].astype(str).isin(selected_causes)
        & wrong_answers["복습 상태"].astype(str).isin(selected_status)
    ].copy()

    total = len(wrong_answers)
    completed = int(
        wrong_answers["복습 상태"]
        .astype(str)
        .isin(["복습 완료", "완전히 이해"])
        .sum()
    )
    due_dates = pd.to_datetime(wrong_answers["다음 복습일"], errors="coerce").dt.date
    overdue = int(
        (
            (due_dates < date.today())
            & ~wrong_answers["복습 상태"].astype(str).isin(["복습 완료", "완전히 이해"])
        ).sum()
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("전체 오답", f"{total}개")
    m2.metric("복습 완료", f"{completed}개")
    m3.metric("복습일 지남", f"{overdue}개")

    st.subheader("오답 목록")
    st.dataframe(filtered, width="stretch", hide_index=True)

    st.subheader("전체 오답 수정")
    st.write("복습 상태나 다음 복습일을 수정한 뒤 저장하세요. 행 추가·삭제도 가능합니다.")
    edited = st.data_editor(
        wrong_answers,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "과목": st.column_config.SelectboxColumn("과목", options=SUBJECTS),
            "오답 원인": st.column_config.SelectboxColumn(
                "오답 원인",
                options=[
                    "개념 부족",
                    "계산 실수",
                    "문제 해석 실수",
                    "시간 부족",
                    "암기 부족",
                    "조건 누락",
                    "기타",
                ],
            ),
            "복습 상태": st.column_config.SelectboxColumn(
                "복습 상태",
                options=["미복습", "1차 복습", "복습 완료", "완전히 이해"],
            ),
        },
        key="wrong_editor",
    )

    if st.button("오답 변경사항 저장", type="primary", width="stretch"):
        saved = edited.copy()
        for column in WRONG_COLUMNS:
            if column not in saved.columns:
                saved[column] = ""
        st.session_state.wrong_answers = saved[WRONG_COLUMNS].reset_index(drop=True)
        st.success("오답 노트를 저장했습니다.")
        st.rerun()

    st.subheader("오답 원인 분석")
    cause_summary = (
        wrong_answers["오답 원인"]
        .fillna("미입력")
        .value_counts()
        .rename_axis("오답 원인")
        .to_frame("문제 수")
    )
    st.bar_chart(cause_summary)
