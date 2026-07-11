from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils import (
    PLAN_COLUMNS,
    SUBJECTS,
    WEEKDAY_KO,
    apply_common_style,
    init_state,
    weekday_ko,
)

st.set_page_config(page_title="날짜별 계획표", page_icon="📅", layout="wide")
init_state()
apply_common_style()

st.title("📅 날짜별 시험 계획표")
st.caption("시험일까지의 계획을 자동으로 만들고, 표에서 직접 수정할 수 있습니다.")

auto_tab, edit_tab, status_tab = st.tabs(["자동 계획 생성", "계획 수정", "진행 현황"])

with auto_tab:
    with st.form("auto_plan_form"):
        top1, top2, top3 = st.columns(3)
        start_date = top1.date_input("계획 시작일", value=date.today())
        exam_date = top2.date_input(
            "시험일",
            value=date.today() + timedelta(days=30),
        )
        daily_minutes = top3.slider(
            "하루 총 공부 시간(분)",
            min_value=30,
            max_value=600,
            value=180,
            step=30,
        )

        selected_weekdays = st.multiselect(
            "공부할 요일",
            options=list(range(7)),
            default=[0, 1, 2, 3, 4, 5],
            format_func=lambda value: WEEKDAY_KO[value],
        )

        selected_subjects = st.multiselect(
            "계획에 넣을 과목",
            SUBJECTS,
            default=["국어", "수학", "영어"],
        )

        tasks_per_day = st.slider(
            "하루 계획 항목 수",
            min_value=1,
            max_value=4,
            value=2,
        )

        subject_settings: dict[str, dict[str, object]] = {}
        if selected_subjects:
            st.markdown("#### 과목별 설정")
            for subject in selected_subjects:
                setting_col1, setting_col2 = st.columns([1, 3])
                priority = setting_col1.slider(
                    f"{subject} 중요도",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"priority_{subject}",
                )
                goals_text = setting_col2.text_area(
                    f"{subject} 학습 내용",
                    value="개념 복습\n문제 풀이\n오답 정리",
                    help="한 줄에 하나씩 입력하세요.",
                    key=f"goals_{subject}",
                )
                goals = [line.strip() for line in goals_text.splitlines() if line.strip()]
                subject_settings[subject] = {
                    "priority": priority,
                    "goals": goals or ["학습하기"],
                }

        replace_existing = st.checkbox(
            "기존 계획을 지우고 새 계획으로 교체",
            value=False,
        )
        submitted = st.form_submit_button("계획표 자동 생성", width="stretch")

    if submitted:
        if exam_date < start_date:
            st.error("시험일은 계획 시작일보다 빠를 수 없습니다.")
        elif not selected_weekdays:
            st.error("공부할 요일을 한 개 이상 선택하세요.")
        elif not selected_subjects:
            st.error("과목을 한 개 이상 선택하세요.")
        else:
            study_dates = []
            current = start_date
            while current < exam_date:
                if current.weekday() in selected_weekdays:
                    study_dates.append(current)
                current += timedelta(days=1)

            if not study_dates:
                st.error("선택한 기간과 요일에 해당하는 공부 날짜가 없습니다.")
            else:
                weighted_subjects: list[str] = []
                for subject in selected_subjects:
                    weighted_subjects.extend(
                        [subject] * int(subject_settings[subject]["priority"])
                    )

                goal_indexes = {subject: 0 for subject in selected_subjects}
                rows = []
                subject_index = 0
                minutes_per_task = max(10, daily_minutes // tasks_per_day)

                for study_date in study_dates:
                    used_today: set[str] = set()
                    for _ in range(tasks_per_day):
                        attempts = 0
                        while attempts < len(weighted_subjects):
                            subject = weighted_subjects[
                                subject_index % len(weighted_subjects)
                            ]
                            subject_index += 1
                            attempts += 1
                            if len(selected_subjects) < tasks_per_day or subject not in used_today:
                                break
                        used_today.add(subject)

                        goals = subject_settings[subject]["goals"]
                        goal_index = goal_indexes[subject]
                        goal = goals[goal_index % len(goals)]
                        goal_indexes[subject] += 1

                        rows.append(
                            {
                                "날짜": study_date.isoformat(),
                                "요일": WEEKDAY_KO[study_date.weekday()],
                                "과목": subject,
                                "학습 내용": goal,
                                "목표 시간(분)": minutes_per_task,
                                "완료": False,
                                "메모": "",
                            }
                        )

                generated = pd.DataFrame(rows, columns=PLAN_COLUMNS)
                if replace_existing or st.session_state.plans.empty:
                    st.session_state.plans = generated
                else:
                    st.session_state.plans = pd.concat(
                        [st.session_state.plans, generated],
                        ignore_index=True,
                    )
                    st.session_state.plans = st.session_state.plans.drop_duplicates(
                        subset=["날짜", "과목", "학습 내용"],
                        keep="last",
                    )

                st.success(f"{len(study_dates)}일, {len(generated)}개 계획을 만들었습니다.")

    if not st.session_state.plans.empty:
        preview = st.session_state.plans.copy().sort_values(["날짜", "과목"])
        st.dataframe(preview.head(20), width="stretch", hide_index=True)

with edit_tab:
    st.write("셀을 수정하거나 행을 추가·삭제한 뒤 **변경사항 저장**을 누르세요.")

    if st.session_state.plans.empty:
        st.info("아직 계획이 없습니다. 자동 계획 생성 탭에서 계획을 만들거나 아래 표에 직접 추가하세요.")

    editable = st.session_state.plans.copy()
    for column in PLAN_COLUMNS:
        if column not in editable.columns:
            editable[column] = None
    editable = editable[PLAN_COLUMNS]

    edited = st.data_editor(
        editable,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "과목": st.column_config.SelectboxColumn("과목", options=SUBJECTS),
            "목표 시간(분)": st.column_config.NumberColumn(
                "목표 시간(분)", min_value=0, step=10, format="%d분"
            ),
            "완료": st.column_config.CheckboxColumn("완료"),
        },
        key="plan_editor",
    )

    save_col, clear_col = st.columns([3, 1])
    if save_col.button("변경사항 저장", type="primary", width="stretch"):
        saved = edited.copy()
        saved["날짜"] = saved["날짜"].astype(str)
        saved["요일"] = saved["날짜"].apply(weekday_ko)
        saved["목표 시간(분)"] = pd.to_numeric(
            saved["목표 시간(분)"], errors="coerce"
        ).fillna(0).astype(int)
        saved["완료"] = saved["완료"].fillna(False).astype(bool)
        saved = saved.sort_values(["날짜", "과목"], na_position="last")
        st.session_state.plans = saved.reset_index(drop=True)
        st.success("계획표를 저장했습니다.")
        st.rerun()

    if clear_col.button("계획 전체 삭제", width="stretch"):
        st.session_state.plans = pd.DataFrame(columns=PLAN_COLUMNS)
        st.success("계획을 모두 삭제했습니다.")
        st.rerun()

with status_tab:
    plans = st.session_state.plans.copy()
    if plans.empty:
        st.info("계획을 입력하면 진행 현황이 표시됩니다.")
    else:
        plans["완료"] = plans["완료"].fillna(False).astype(bool)
        plans["목표 시간(분)"] = pd.to_numeric(
            plans["목표 시간(분)"], errors="coerce"
        ).fillna(0)

        total = len(plans)
        completed = int(plans["완료"].sum())
        total_minutes = int(plans["목표 시간(분)"].sum())
        completed_minutes = int(plans.loc[plans["완료"], "목표 시간(분)"].sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("전체 계획", f"{total}개")
        m2.metric("완료 계획", f"{completed}개")
        m3.metric("전체 목표 시간", f"{total_minutes}분")
        m4.metric("완료한 시간", f"{completed_minutes}분")

        completion_rate = completed / total if total else 0
        st.progress(completion_rate)
        st.write(f"전체 완료율: **{completion_rate * 100:.1f}%**")

        subject_summary = (
            plans.groupby("과목", dropna=False)
            .agg(
                전체=("완료", "size"),
                완료=("완료", "sum"),
                목표시간=("목표 시간(분)", "sum"),
            )
            .reset_index()
        )
        subject_summary["완료율(%)"] = (
            subject_summary["완료"] / subject_summary["전체"] * 100
        ).round(1)
        st.subheader("과목별 진행 현황")
        st.dataframe(subject_summary, width="stretch", hide_index=True)
