import calendar
import html
from datetime import date, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="날짜별 계획표", page_icon="🗓️", layout="wide")

SUBJECTS = ["국어", "수학", "영어", "과학", "사회"]
SCORE_COLUMNS = ["날짜", "시험명", *SUBJECTS]
WRONG_COLUMNS = ["날짜", "과목", "시험/교재", "문항", "오답유형", "메모", "해결"]
PLAN_COLUMNS = ["날짜", "요일", "과목", "학습1", "학습2", "학습3", "학습4", "학습5"]
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

TASK_BANK = {
    "국어": {
        "기초": ["교과 개념·작품 정리", "핵심 어휘·문법 복습", "기본 문제 풀이", "근거 문장 표시", "틀린 선지 고치기"],
        "유형": ["문학·독서 유형 문제", "시간을 재고 지문 풀이", "문법 취약 유형 집중", "선지 판단 근거 쓰기", "오답 노트 정리"],
        "실전": ["실전 세트 풀이", "시간 배분 점검", "채점 후 오답 분석", "취약 작품·문법 재복습", "시험 직전 암기 확인"],
    },
    "수학": {
        "기초": ["개념과 공식 정리", "대표 예제 풀이", "기본 계산 연습", "풀이 과정을 설명", "개념 오답 다시 풀기"],
        "유형": ["빈출 유형 문제", "중난도 문제 집중", "시간을 재고 문제 풀이", "오답 원인 분류", "유사 문제 재도전"],
        "실전": ["실전 모의 세트", "고난도 문항 도전", "검산 습관 점검", "오답만 다시 풀기", "공식·주의점 최종 확인"],
    },
    "영어": {
        "기초": ["본문·단어 암기", "핵심 문법 정리", "문장 구조 분석", "기본 독해 문제", "틀린 단어 재암기"],
        "유형": ["빈칸·순서·삽입 유형", "시간을 재고 독해", "서술형 문장 연습", "문법 오답 분석", "단어 누적 복습"],
        "실전": ["실전 독해 세트", "듣기·독해 시간 점검", "오답 근거 찾기", "서술형 최종 연습", "본문·단어 최종 확인"],
    },
    "과학": {
        "기초": ["개념과 용어 정리", "교과서 그림·표 해석", "기본 문제 풀이", "원리 설명 연습", "개념 오답 복습"],
        "유형": ["자료 해석 문제", "계산·추론 문제", "단원 통합 문제", "오답 원인 분류", "유사 문제 재풀이"],
        "실전": ["실전 모의 세트", "시간 배분 점검", "그래프·표 집중 훈련", "오답만 다시 풀기", "핵심 개념 최종 점검"],
    },
    "사회": {
        "기초": ["핵심 개념 정리", "용어·사례 암기", "지도·그래프 확인", "기본 문제 풀이", "틀린 개념 다시 정리"],
        "유형": ["자료 분석 문제", "개념 비교 문제", "서술형 근거 쓰기", "오답 원인 분류", "유사 문제 재풀이"],
        "실전": ["실전 모의 세트", "시간 배분 점검", "자료·선지 근거 확인", "오답만 다시 풀기", "핵심 사례 최종 암기"],
    },
}


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


def latest_scores(score_df: pd.DataFrame) -> dict[str, float]:
    result = {subject: 70.0 for subject in SUBJECTS}
    if score_df.empty:
        return result

    copied = score_df.copy()
    copied["날짜"] = pd.to_datetime(copied["날짜"], errors="coerce")
    copied = copied.sort_values("날짜")
    for subject in SUBJECTS:
        values = pd.to_numeric(copied[subject], errors="coerce").dropna()
        if not values.empty:
            result[subject] = float(values.iloc[-1])
    return result


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


def subject_order(selected_subjects: list[str], score_df: pd.DataFrame, wrong_df: pd.DataFrame):
    scores = latest_scores(score_df)
    wrongs = unresolved_counts(wrong_df)
    weights = {
        subject: max(1.0, (100.0 - scores[subject]) + wrongs[subject] * 4.0)
        for subject in selected_subjects
        if subject in SUBJECTS
    }
    ordered = sorted(weights, key=lambda subject: (-weights[subject], SUBJECTS.index(subject)))
    return ordered, weights


def weighted_cycle(ordered: list[str], weights: dict[str, float]) -> list[str]:
    if not ordered:
        return []
    values = [weights[subject] for subject in ordered]
    low, high = min(values), max(values)
    repeats = {}
    for subject in ordered:
        if high == low:
            repeats[subject] = 1
        else:
            normalized = (weights[subject] - low) / (high - low)
            repeats[subject] = 1 + round(normalized * 2)

    cycle = []
    for level in range(1, max(repeats.values()) + 1):
        for subject in ordered:
            if repeats[subject] >= level:
                cycle.append(subject)
    return cycle


def study_stage(index: int, total: int) -> str:
    progress = (index + 1) / max(total, 1)
    if progress <= 0.4:
        return "기초"
    if progress <= 0.75:
        return "유형"
    return "실전"


def build_plan(start_date, end_date, selected_subjects, sessions_per_day, consecutive_days, include_weekends):
    if end_date < start_date or not selected_subjects:
        return pd.DataFrame(columns=PLAN_COLUMNS)

    study_dates = []
    current = start_date
    while current <= end_date:
        if include_weekends or current.weekday() < 5:
            study_dates.append(current)
        current += timedelta(days=1)

    ordered, weights = subject_order(
        selected_subjects,
        st.session_state.mock_scores,
        st.session_state.wrong_questions,
    )
    cycle = weighted_cycle(ordered, weights)
    if not study_dates or not cycle:
        return pd.DataFrame(columns=PLAN_COLUMNS)

    rows = []
    cycle_index = 0
    block_day = 0

    for index, study_date in enumerate(study_dates):
        subject = cycle[cycle_index]
        stage = study_stage(index, len(study_dates))
        tasks = TASK_BANK[subject][stage]
        row = {
            "날짜": study_date.isoformat(),
            "요일": WEEKDAY_KO[study_date.weekday()],
            "과목": subject,
        }
        for number in range(1, 6):
            row[f"학습{number}"] = tasks[number - 1] if number <= sessions_per_day else ""
        rows.append(row)

        block_day += 1
        if block_day >= consecutive_days:
            block_day = 0
            cycle_index = (cycle_index + 1) % len(cycle)

    return pd.DataFrame(rows, columns=PLAN_COLUMNS)


def render_calendar(plan_df: pd.DataFrame) -> None:
    if plan_df.empty:
        st.info("아직 생성된 계획표가 없습니다.")
        return

    copied = plan_df.copy()
    copied["날짜_dt"] = pd.to_datetime(copied["날짜"], errors="coerce")
    copied = copied.dropna(subset=["날짜_dt"])
    if copied.empty:
        st.warning("표시할 수 있는 날짜가 없습니다.")
        return

    plan_by_date = {}
    for _, row in copied.iterrows():
        day = row["날짜_dt"].date()
        tasks = []
        for number in range(1, 6):
            task = str(row.get(f"학습{number}", "")).strip()
            if task:
                tasks.append(task)
        plan_by_date[day] = {"subject": str(row["과목"]), "tasks": tasks}

    first = copied["날짜_dt"].min().date()
    last = copied["날짜_dt"].max().date()
    months = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append((year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

    st.markdown(
        """
<style>
.calendar-wrap {overflow-x:auto; margin:0.5rem 0 2rem 0;}
.month-title {font-size:2rem; font-weight:800; text-align:center; margin:0.7rem 0;}
table.study-calendar {width:100%; border-collapse:collapse; table-layout:fixed; min-width:900px;}
.study-calendar th {background:#555c58; color:white; padding:0.55rem; border:1px solid #d6dbd8;}
.study-calendar th.sun {background:#c7443d;}
.study-calendar th.sat {background:#39799f;}
.study-calendar td {height:150px; vertical-align:top; border:2px solid #43b9c2; padding:0.4rem; background:white;}
.study-calendar td.outside {background:#f2f3f2; border:1px solid #e1e4e2;}
.day-number {font-size:1.05rem; font-weight:800; margin-bottom:0.2rem;}
.day-number.sun {color:#c83b33;}
.day-number.sat {color:#2f7097;}
.subject-label {font-size:0.82rem; font-weight:800; color:#087b84; margin-bottom:0.15rem;}
.task-line {font-size:0.78rem; line-height:1.35; word-break:keep-all;}
</style>
""",
        unsafe_allow_html=True,
    )

    cal = calendar.Calendar(firstweekday=6)
    headers = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    for year, month in months:
        parts = [f'<div class="month-title">{year}년 {month}월</div>']
        parts.append('<div class="calendar-wrap"><table class="study-calendar"><thead><tr>')
        for index, header in enumerate(headers):
            css_class = "sun" if index == 0 else "sat" if index == 6 else ""
            parts.append(f'<th class="{css_class}">{header}</th>')
        parts.append("</tr></thead><tbody>")

        for week in cal.monthdatescalendar(year, month):
            parts.append("<tr>")
            for index, day in enumerate(week):
                if day.month != month:
                    parts.append('<td class="outside"></td>')
                    continue

                day_class = "sun" if index == 0 else "sat" if index == 6 else ""
                parts.append("<td>")
                parts.append(f'<div class="day-number {day_class}">{day.day}</div>')
                entry = plan_by_date.get(day)
                if entry:
                    parts.append(f'<div class="subject-label">{html.escape(entry["subject"])}</div>')
                    for number, task in enumerate(entry["tasks"], start=1):
                        parts.append(f'<div class="task-line">{number}. {html.escape(task)}</div>')
                parts.append("</td>")
            parts.append("</tr>")

        parts.append("</tbody></table></div>")
        st.markdown("".join(parts), unsafe_allow_html=True)


ensure_state()
st.title("🗓️ 날짜별 시험 계획표")
st.caption("한 과목을 선택한 일수만큼 연속해서 공부하도록 자동 배정합니다.")

with st.form("plan_form"):
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("계획 시작일", value=date.today())
        end_date = st.date_input("계획 종료일", value=date.today() + timedelta(days=20))
        selected_subjects = st.multiselect("공부할 과목", SUBJECTS, default=SUBJECTS)
    with col2:
        sessions_per_day = st.slider("하루 학습 칸 수", 1, 5, 3)
        consecutive_days = st.slider("한 과목 연속 학습 일수", 1, 7, 2)
        include_weekends = st.checkbox("주말도 계획에 포함", value=True)

    submitted = st.form_submit_button("계획표 만들기", type="primary", width="stretch")

if submitted:
    if end_date < start_date:
        st.error("종료일은 시작일보다 빠를 수 없습니다.")
    elif not selected_subjects:
        st.error("공부할 과목을 한 개 이상 선택해 주세요.")
    else:
        st.session_state.study_plan = build_plan(
            start_date,
            end_date,
            selected_subjects,
            sessions_per_day,
            consecutive_days,
            include_weekends,
        )
        st.success("계획표를 만들었습니다.")

selected_for_priority = selected_subjects if "selected_subjects" in locals() else SUBJECTS
ordered, weights = subject_order(
    selected_for_priority,
    st.session_state.mock_scores,
    st.session_state.wrong_questions,
)
if ordered:
    priority_text = " → ".join(f"{subject}({weights[subject]:.0f})" for subject in ordered)
    st.caption(f"학습 우선순위: {priority_text} · 점수가 낮거나 미해결 오답이 많을수록 우선 배정됩니다.")

plan_df = st.session_state.study_plan.copy()
render_calendar(plan_df)

if not plan_df.empty:
    with st.expander("표 형태로 자세히 보기"):
        visible = ["날짜", "요일", "과목"]
        for column in ["학습1", "학습2", "학습3", "학습4", "학습5"]:
            if column in plan_df.columns and plan_df[column].fillna("").astype(str).ne("").any():
                visible.append(column)
        st.dataframe(plan_df[visible].reset_index(drop=True), hide_index=True, width="stretch")

    st.download_button(
        "계획표 CSV 다운로드",
        data=plan_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="시험_계획표.csv",
        mime="text/csv",
        width="stretch",
    )
