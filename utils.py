from __future__ import annotations

import json
import math
from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st

SUBJECTS = [
    "국어",
    "수학",
    "영어",
    "한국사",
    "통합사회",
    "통합과학",
    "물리",
    "화학",
    "생명과학",
    "지구과학",
    "사회탐구",
    "과학탐구",
    "제2외국어",
    "기타",
]

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

PLAN_COLUMNS = [
    "날짜",
    "요일",
    "과목",
    "학습 내용",
    "목표 시간(분)",
    "완료",
    "메모",
]

SCORE_COLUMNS = [
    "시험명",
    "응시일",
    "과목",
    "점수",
    "만점",
    "환산점수",
]

WRONG_COLUMNS = [
    "등록일",
    "시험명",
    "과목",
    "문제 번호",
    "문제 유형",
    "오답 원인",
    "정답/핵심",
    "복습 상태",
    "다음 복습일",
]


def empty_plan_df() -> pd.DataFrame:
    return pd.DataFrame(columns=PLAN_COLUMNS)


def empty_score_df() -> pd.DataFrame:
    return pd.DataFrame(columns=SCORE_COLUMNS)


def empty_wrong_df() -> pd.DataFrame:
    return pd.DataFrame(columns=WRONG_COLUMNS)


def init_state() -> None:
    """모든 페이지에서 공통으로 사용할 Session State를 초기화합니다."""
    if "plans" not in st.session_state:
        st.session_state.plans = empty_plan_df()
    if "scores" not in st.session_state:
        st.session_state.scores = empty_score_df()
    if "wrong_answers" not in st.session_state:
        st.session_state.wrong_answers = empty_wrong_df()


def normalize_dataframe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """누락된 열을 추가하고 지정한 열 순서로 정리합니다."""
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = None
    return result[columns]


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def export_backup_json() -> str:
    payload = {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "plans": st.session_state.plans.to_dict(orient="records"),
        "scores": st.session_state.scores.to_dict(orient="records"),
        "wrong_answers": st.session_state.wrong_answers.to_dict(orient="records"),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def import_backup_json(raw_data: bytes | str) -> tuple[bool, str]:
    try:
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")
        payload = json.loads(raw_data)

        plans = pd.DataFrame(payload.get("plans", []))
        scores = pd.DataFrame(payload.get("scores", []))
        wrong_answers = pd.DataFrame(payload.get("wrong_answers", []))

        st.session_state.plans = normalize_dataframe(plans, PLAN_COLUMNS)
        st.session_state.scores = normalize_dataframe(scores, SCORE_COLUMNS)
        st.session_state.wrong_answers = normalize_dataframe(
            wrong_answers, WRONG_COLUMNS
        )
        return True, "백업 데이터를 불러왔습니다."
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        return False, f"백업 파일을 읽지 못했습니다: {error}"


def weekday_ko(date_text: str) -> str:
    try:
        parsed = pd.to_datetime(date_text)
        return WEEKDAY_KO[int(parsed.weekday())]
    except (TypeError, ValueError):
        return ""


def calculate_predictions(
    score_df: pd.DataFrame,
    wrong_df: pd.DataFrame,
) -> pd.DataFrame:
    """최근 성적, 추세, 오답 복습률, 점수 변동성을 이용해 예상점수를 계산합니다."""
    result_columns = [
        "과목",
        "최근 점수",
        "최근 가중평균",
        "추세 보정",
        "오답 보정",
        "변동성 보정",
        "예상점수",
        "예상 범위",
        "시험 수",
        "미해결 오답",
    ]

    if score_df.empty:
        return pd.DataFrame(columns=result_columns)

    scores = score_df.copy()
    scores["환산점수"] = pd.to_numeric(scores["환산점수"], errors="coerce")
    scores["응시일_dt"] = pd.to_datetime(scores["응시일"], errors="coerce")
    scores = scores.dropna(subset=["과목", "환산점수"])

    rows: list[dict[str, Any]] = []

    for subject, subject_scores in scores.groupby("과목"):
        subject_scores = subject_scores.sort_values(
            ["응시일_dt", "시험명"], na_position="first"
        )
        recent = subject_scores.tail(5)
        values = recent["환산점수"].astype(float).tolist()
        if not values:
            continue

        n = len(values)
        weights = list(range(1, n + 1))
        weighted_average = sum(v * w for v, w in zip(values, weights)) / sum(weights)
        latest = values[-1]

        if n >= 2:
            x_mean = (n - 1) / 2
            y_mean = sum(values) / n
            denominator = sum((x - x_mean) ** 2 for x in range(n))
            slope = (
                sum((x - x_mean) * (y - y_mean) for x, y in enumerate(values))
                / denominator
                if denominator
                else 0.0
            )
            trend_adjustment = max(-5.0, min(5.0, slope))
            variance = sum((value - y_mean) ** 2 for value in values) / n
            standard_deviation = math.sqrt(variance)
        else:
            trend_adjustment = 0.0
            standard_deviation = 8.0

        if wrong_df.empty:
            total_wrong = 0
            unresolved = 0
            wrong_adjustment = 0.0
        else:
            subject_wrong = wrong_df[wrong_df["과목"].astype(str) == str(subject)]
            total_wrong = len(subject_wrong)
            completed_status = {"복습 완료", "완전히 이해"}
            completed = int(
                subject_wrong["복습 상태"].astype(str).isin(completed_status).sum()
            )
            unresolved = max(total_wrong - completed, 0)
            if total_wrong:
                mastery_ratio = completed / total_wrong
                wrong_adjustment = (mastery_ratio - 0.5) * 6
                wrong_adjustment -= min(unresolved * 0.3, 3.0)
            else:
                wrong_adjustment = 0.0

        volatility_adjustment = -min(standard_deviation * 0.12, 3.0)
        predicted = weighted_average + trend_adjustment + wrong_adjustment
        predicted += volatility_adjustment
        predicted = max(0.0, min(100.0, predicted))

        margin = standard_deviation * 0.6 + 6 / math.sqrt(max(n, 1))
        margin = max(3.0, min(12.0, margin))
        lower = max(0.0, predicted - margin)
        upper = min(100.0, predicted + margin)

        rows.append(
            {
                "과목": subject,
                "최근 점수": round(latest, 1),
                "최근 가중평균": round(weighted_average, 1),
                "추세 보정": round(trend_adjustment, 1),
                "오답 보정": round(wrong_adjustment, 1),
                "변동성 보정": round(volatility_adjustment, 1),
                "예상점수": round(predicted, 1),
                "예상 범위": f"{lower:.1f} ~ {upper:.1f}",
                "시험 수": int(len(subject_scores)),
                "미해결 오답": int(unresolved),
            }
        )

    return pd.DataFrame(rows, columns=result_columns).sort_values(
        "예상점수", ascending=False
    )


def apply_common_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stMetric"] {
            background: rgba(128, 128, 128, 0.08);
            border: 1px solid rgba(128, 128, 128, 0.18);
            padding: 0.8rem;
            border-radius: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
