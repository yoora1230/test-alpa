from datetime import date, timedelta

import streamlit as st

from common import SUBJECTS, build_study_plan, init_state, render_calendar, subject_priority

st.set_page_config(page_title="날짜별 계획표", page_icon="🗓️", layout="wide")
init_state()

st.title("🗓️ 날짜별 시험 계획표")
st.caption("선택한 과목을 여러 날 연속으로 배정하고, 취약 과목은 더 자주 돌아오도록 계획합니다.")

with st.form("plan_form"):
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("계획 시작일", value=date.today())
        end_date = st.date_input("계획 종료일", value=date.today() + timedelta(days=27))
        selected_subjects = st.multiselect("공부할 과목", SUBJECTS, default=SUBJECTS)
    with col2:
        sessions_per_day = st.slider("하루 학습 칸 수", min_value=1, max_value=5, value=3)
        consecutive_days = st.slider("한 과목 연속 학습 일수", min_value=1, max_value=7, value=2)
        include_weekends = st.checkbox("토요일·일요일도 계획에 포함", value=True)

    submitted = st.form_submit_button("계획표 만들기", type="primary", use_container_width=True)

if submitted:
    if end_date < start_date:
        st.error("종료일은 시작일보다 빠를 수 없습니다.")
    elif not selected_subjects:
        st.error("공부할 과목을 한 개 이상 선택해 주세요.")
    else:
        plan = build_study_plan(
            start_date=start_date,
            end_date=end_date,
            selected_subjects=selected_subjects,
            sessions_per_day=sessions_per_day,
            consecutive_days=consecutive_days,
            include_weekends=include_weekends,
            score_df=st.session_state.mock_scores,
            wrong_df=st.session_state.wrong_questions,
        )
        st.session_state.study_plan = plan
        st.success("계획표를 만들었습니다.")

ordered, weights = subject_priority(
    selected_subjects if "selected_subjects" in locals() else SUBJECTS,
    st.session_state.mock_scores,
    st.session_state.wrong_questions,
)
if ordered:
    priority_text = " → ".join(f"{subject}({weights[subject]:.0f})" for subject in ordered)
    st.caption(f"현재 학습 우선순위: {priority_text} · 숫자가 클수록 우선 배정됩니다.")

plan_df = st.session_state.study_plan
render_calendar(plan_df)

if not plan_df.empty:
    with st.expander("표 형태로 자세히 보기"):
        visible_columns = ["날짜", "요일", "과목"] + [
            column for column in ["학습1", "학습2", "학습3", "학습4", "학습5"]
            if column in plan_df.columns and (plan_df[column] != "").any()
        ]
        st.dataframe(plan_df[visible_columns], hide_index=True, use_container_width=True)

    st.download_button(
        "계획표 CSV 다운로드",
        data=plan_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="시험_계획표.csv",
        mime="text/csv",
        use_container_width=True,
    )
