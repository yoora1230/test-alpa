from __future__ import annotations

import calendar
import html
from datetime import date, timedelta
from typing import Iterable

import pandas as pd
import streamlit as st

SUBJECTS = ["국어", "수학", "영어", "과학", "사회"]
MOCK_COLUMNS = ["날짜", "시험명", *SUBJECTS]
WRONG_COLUMNS = ["날짜", "과목", "시험/교재", "문항", "오답유형", "메모", "해결"]
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def init_state() -> None:
    """모든 페이지에서 함께 사용할 Session State를 초기화합니다."""
    if "mock_scores" not in st.session_state:
        st.session_state.mock_scores = pd.DataFrame(columns=MOCK_COLUMNS)

    if "wrong_questions" not in st.session_state:
        st.session_state.wrong_questions = pd.DataFrame(columns=WRONG_COLUMNS)

    if "study_plan" not in st.session_state:
        st.session_state.study_plan = pd.DataFrame(
            columns=["날짜", "요일", "과목", "학습1", "학습2", "학습3", "학습4", "학습5"]
        )

    if "wrong_editor_version" not in st.session_state:
        st.session_state.wrong_editor_version = 0


def latest_scores(score_df: pd.DataFrame) -> dict[str, float]:
    """과목별 최신 점수를 반환합니다. 기록이 없으면 70점을 사용합니다."""
    result = {subject: 70.0 for subject in SUBJECTS}
    if score_df.empty:
        return result

    ordered = score_df.copy()
    ordered["날짜"] = pd.to_datetime(ordered["날짜"], errors="coerce")
    ordered = ordered.sort_values("날짜")

    for subject in SUBJECTS:
        numeric = pd.to_numeric(ordered[subject], errors="coerce").dropna()
        if not numeric.empty:
            result[subject] = float(numeric.iloc[-1])
    return result


def unresolved_wrong_counts(wrong_df: pd.DataFrame) -> dict[str, int]:
    result = {subject: 0 for subject in SUBJECTS}
    if wrong_df.empty:
        return result

    copied = wrong_df.copy()
    copied["해결"] = copied["해결"].fillna(False).astype(bool)
    unsolved = copied[~copied["해결"]]

    counts = unsolved["과목"].value_counts()
    for subject in SUBJECTS:
        result[subject] = int(counts.get(subject, 0))
    return result


def subject_priority(
    selected_subjects: Iterable[str],
    score_df: pd.DataFrame,
    wrong_df: pd.DataFrame,
) -> tuple[list[str], dict[str, float]]:
    """낮은 점수와 미해결 오답 수를 반영해 우선순위를 계산합니다."""
    scores = latest_scores(score_df)
    wrongs = unresolved_wrong_counts(wrong_df)
    selected = [subject for subject in selected_subjects if subject in SUBJECTS]

    weights = {
        subject: max(1.0, (100.0 - scores[subject]) + wrongs[subject] * 4.0)
        for subject in selected
    }
    ordered = sorted(selected, key=lambda subject: (-weights[subject], SUBJECTS.index(subject)))
    return ordered, weights


def _interleaved_weighted_cycle(ordered: list[str], weights: dict[str, float]) -> list[str]:
    """취약 과목이 더 자주 등장하되 같은 과목만 몰리지 않게 순환 목록을 만듭니다."""
    if not ordered:
        return []

    values = [weights[s] for s in ordered]
    minimum = min(values)
    maximum = max(values)

    repeats: dict[str, int] = {}
    for subject in ordered:
        if maximum == minimum:
            repeats[subject] = 1
        else:
            normalized = (weights[subject] - minimum) / (maximum - minimum)
            repeats[subject] = 1 + round(normalized * 2)  # 1~3회

    cycle: list[str] = []
    for level in range(1, max(repeats.values()) + 1):
        for subject in ordered:
            if repeats[subject] >= level:
                cycle.append(subject)
    return cycle


TASK_BANK: dict[str, dict[str, list[str]]] = {
    "국어": {
        "기초": ["교과 개념과 작품 정리", "핵심 어휘·문법 복습", "기본 문제 풀이", "근거 문장 표시", "틀린 선지 고치기"],
        "유형": ["문학·독서 유형 문제", "시간을 재고 지문 풀이", "문법 취약 유형 집중", "선지 판단 근거 쓰기", "오답 노트 정리"],
        "실전": ["실전 세트 풀이", "시간 배분 점검", "채점 후 오답 분석", "취약 작품·문법 재복습", "시험 직전 암기 확인"],
    },
    "수학": {
        "기초": ["개념과 공식 정리", "대표 예제 풀이", "기본 계산 연습", "풀이 과정을 말로 설명", "개념 오답 다시 풀기"],
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


def _study_stage(index: int, total: int) -> str:
    progress = (index + 1) / max(total, 1)
    if progress <= 0.4:
        return "기초"
    if progress <= 0.75:
        return "유형"
    return "실전"


def build_study_plan(
    start_date: date,
    end_date: date,
    selected_subjects: list[str],
    sessions_per_day: int,
    consecutive_days: int,
    include_weekends: bool,
    score_df: pd.DataFrame,
    wrong_df: pd.DataFrame,
) -> pd.DataFrame:
    """한 과목을 지정한 일수만큼 연속 배정하여 학습 계획을 생성합니다."""
    if end_date < start_date or not selected_subjects:
        return pd.DataFrame()

    all_dates: list[date] = []
    current = start_date
    while current <= end_date:
        if include_weekends or current.weekday() < 5:
            all_dates.append(current)
        current += timedelta(days=1)

    if not all_dates:
        return pd.DataFrame()

    ordered, weights = subject_priority(selected_subjects, score_df, wrong_df)
    cycle = _interleaved_weighted_cycle(ordered, weights)
    if not cycle:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    cycle_index = 0
    days_in_current_block = 0

    for index, study_date in enumerate(all_dates):
        subject = cycle[cycle_index]
        stage = _study_stage(index, len(all_dates))
        tasks = TASK_BANK[subject][stage]

        row: dict[str, object] = {
            "날짜": study_date.isoformat(),
            "요일": WEEKDAY_KO[study_date.weekday()],
            "과목": subject,
        }
        for session in range(1, 6):
            row[f"학습{session}"] = tasks[(session - 1) % len(tasks)] if session <= sessions_per_day else ""
        rows.append(row)

        days_in_current_block += 1
        if days_in_current_block >= consecutive_days:
            days_in_current_block = 0
            cycle_index = (cycle_index + 1) % len(cycle)

    return pd.DataFrame(rows)


def current_expected_scores(score_df: pd.DataFrame, wrong_df: pd.DataFrame) -> pd.DataFrame:
    """최근 성적, 추세, 미해결 오답을 이용한 단순 예상점수를 계산합니다."""
    wrong_counts = unresolved_wrong_counts(wrong_df)
    rows: list[dict[str, object]] = []

    for subject in SUBJECTS:
        if score_df.empty:
            recent = pd.Series(dtype=float)
        else:
            ordered = score_df.copy()
            ordered["날짜"] = pd.to_datetime(ordered["날짜"], errors="coerce")
            ordered = ordered.sort_values("날짜")
            recent = pd.to_numeric(ordered[subject], errors="coerce").dropna().tail(3)

        if recent.empty:
            recent_average = 70.0
            trend = 0.0
        else:
            recent_average = float(recent.mean())
            trend = float(recent.iloc[-1] - recent.iloc[-2]) if len(recent) >= 2 else 0.0

        penalty = min(12.0, wrong_counts[subject] * 0.8)
        predicted = recent_average + trend * 0.35 - penalty
        predicted = max(0.0, min(100.0, predicted))

        rows.append(
            {
                "과목": subject,
                "최근 3회 평균": round(recent_average, 1),
                "최근 추세": round(trend, 1),
                "미해결 오답": wrong_counts[subject],
                "현재 예상점수": round(predicted, 1),
            }
        )

    return pd.DataFrame(rows)


def render_calendar(plan_df: pd.DataFrame) -> None:
    """이미지와 비슷한 월간 달력형 표를 HTML로 표시합니다."""
    if plan_df.empty:
        st.info("먼저 계획을 생성해 주세요.")
        return

    copied = plan_df.copy()
    copied["날짜_dt"] = pd.to_datetime(copied["날짜"], errors="coerce")
    copied = copied.dropna(subset=["날짜_dt"])
    if copied.empty:
        st.warning("표시할 수 있는 날짜가 없습니다.")
        return

    plan_by_date: dict[date, list[dict[str, str]]] = {}
    for _, row in copied.iterrows():
        day = row["날짜_dt"].date()
        tasks = [
            str(row.get(f"학습{i}", "")).strip()
            for i in range(1, 6)
            if str(row.get(f"학습{i}", "")).strip()
        ]
        plan_by_date[day] = [{"subject": str(row["과목"]), "task": task} for task in tasks]

    first = copied["날짜_dt"].min().date()
    last = copied["날짜_dt"].max().date()
    months: list[tuple[int, int]] = []
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
        .calendar-wrap {overflow-x:auto; margin: 0.5rem 0 2rem 0;}
        .month-title {font-size:2rem; font-weight:800; text-align:center; margin:0.5rem 0;}
        table.study-calendar {width:100%; border-collapse:collapse; table-layout:fixed; min-width:900px;}
        .study-calendar th {background:#4f5753; color:white; padding:0.55rem; border:1px solid #d8ddd9;}
        .study-calendar th.sun {background:#c93f37;}
        .study-calendar th.sat {background:#39779d;}
        .study-calendar td {height:145px; vertical-align:top; border:2px solid #52bec7; padding:0.4rem; background:white;}
        .study-calendar td.outside {background:#f4f5f4; border:1px solid #e3e6e4;}
        .day-number {font-size:1.05rem; font-weight:800; margin-bottom:0.25rem;}
        .day-number.sun {color:#c83a32;}
        .day-number.sat {color:#2e6f98;}
        .subject-label {display:inline-block; font-size:0.78rem; font-weight:800; color:#087d87; margin-bottom:0.2rem;}
        .task-line {font-size:0.78rem; line-height:1.35; padding:0.08rem 0; word-break:keep-all;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    headers = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    for year, month in months:
        parts = [f'<div class="month-title">{year}년 {month}월</div>']
        parts.append('<div class="calendar-wrap"><table class="study-calendar"><thead><tr>')
        for idx, header in enumerate(headers):
            cls = "sun" if idx == 0 else "sat" if idx == 6 else ""
            parts.append(f'<th class="{cls}">{header}</th>')
        parts.append("</tr></thead><tbody>")

        for week in cal.monthdatescalendar(year, month):
            parts.append("<tr>")
            for idx, day in enumerate(week):
                if day.month != month:
                    parts.append('<td class="outside"></td>')
                    continue

                day_cls = "sun" if idx == 0 else "sat" if idx == 6 else ""
                parts.append("<td>")
                parts.append(f'<div class="day-number {day_cls}">{day.day}</div>')
                entries = plan_by_date.get(day, [])
                if entries:
                    subject = html.escape(entries[0]["subject"])
                    parts.append(f'<div class="subject-label">{subject}</div>')
                    for number, entry in enumerate(entries, start=1):
                        task = html.escape(entry["task"])
                        parts.append(f'<div class="task-line">{number}. {task}</div>')
                parts.append("</td>")
            parts.append("</tr>")

        parts.append("</tbody></table></div>")
        st.markdown("".join(parts), unsafe_allow_html=True)
