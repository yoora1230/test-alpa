from __future__ import annotations

import pandas as pd
import streamlit as st

from utils import apply_common_style, calculate_predictions, init_state

st.set_page_config(page_title="예상 점수", page_icon="🎯", layout="wide")
init_state()
apply_common_style()

st.title("🎯 현재 예상점수")
st.caption("최근 모의고사 성적과 오답 복습 상태를 조합한 학습 참고용 추정치입니다.")

predictions = calculate_predictions(
    st.session_state.scores,
    st.session_state.wrong_answers,
)

if predictions.empty:
    st.warning("예상점수를 계산하려면 먼저 모의고사 점수를 한 번 이상 입력하세요.")
else:
    target_score = st.slider(
        "목표 평균 점수",
        min_value=0,
        max_value=100,
        value=85,
    )

    expected_average = float(predictions["예상점수"].mean())
    latest_average = float(predictions["최근 점수"].mean())
    gap = expected_average - target_score

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "예상 평균",
        f"{expected_average:.1f}점",
        delta=f"최근 점수 평균 대비 {expected_average - latest_average:+.1f}점",
    )
    m2.metric("최근 점수 평균", f"{latest_average:.1f}점")
    m3.metric(
        "목표와의 차이",
        f"{abs(gap):.1f}점",
        delta="목표 이상" if gap >= 0 else "목표까지 남음",
        delta_color="normal" if gap >= 0 else "inverse",
    )

    st.subheader("과목별 예상점수")
    chart_data = predictions.set_index("과목")[["최근 점수", "예상점수"]]
    st.bar_chart(chart_data, y_label="점수")

    display_columns = [
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
    st.dataframe(
        predictions[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "최근 점수": st.column_config.NumberColumn(format="%.1f점"),
            "최근 가중평균": st.column_config.NumberColumn(format="%.1f점"),
            "추세 보정": st.column_config.NumberColumn(format="%+.1f점"),
            "오답 보정": st.column_config.NumberColumn(format="%+.1f점"),
            "변동성 보정": st.column_config.NumberColumn(format="%+.1f점"),
            "예상점수": st.column_config.ProgressColumn(
                "예상점수",
                min_value=0,
                max_value=100,
                format="%.1f점",
            ),
        },
    )

    st.subheader("지금 우선할 공부")
    recommendations: list[str] = []

    low_subjects = predictions.nsmallest(min(3, len(predictions)), "예상점수")
    if not low_subjects.empty:
        subject_text = ", ".join(low_subjects["과목"].astype(str).tolist())
        recommendations.append(f"예상점수가 낮은 **{subject_text}**를 우선 배치하세요.")

    unresolved = predictions[predictions["미해결 오답"] > 0].sort_values(
        "미해결 오답", ascending=False
    )
    if not unresolved.empty:
        top = unresolved.iloc[0]
        recommendations.append(
            f"**{top['과목']}**의 미해결 오답이 {int(top['미해결 오답'])}개이므로 오답 복습 시간을 확보하세요."
        )

    negative_trend = predictions[predictions["추세 보정"] < 0].sort_values("추세 보정")
    if not negative_trend.empty:
        subject_text = ", ".join(negative_trend["과목"].astype(str).tolist())
        recommendations.append(
            f"최근 하락 추세가 있는 **{subject_text}**는 다음 모의고사 전에 원인을 점검하세요."
        )

    if expected_average >= target_score:
        recommendations.append(
            "현재 추정 평균은 목표 이상입니다. 새 내용을 무리하게 늘리기보다 실수 방지와 복습 유지에 집중하세요."
        )
    else:
        recommendations.append(
            f"목표 평균까지 약 **{target_score - expected_average:.1f}점** 남았습니다. 낮은 과목의 개념 복습과 오답 재풀이를 먼저 진행하세요."
        )

    for recommendation in recommendations:
        st.write(f"- {recommendation}")

    with st.expander("예상점수 계산 방식 보기"):
        st.markdown(
            """
            과목별 예상점수는 다음 요소를 이용합니다.

            - 최근 최대 5회의 **최근 가중평균**: 최근 시험일수록 더 큰 비중을 둡니다.
            - **성적 추세 보정**: 최근 점수가 상승하면 가산하고, 하락하면 감산합니다.
            - **오답 보정**: 오답 복습 완료 비율이 높으면 가산하고, 미해결 오답이 많으면 감산합니다.
            - **변동성 보정**: 점수 변화가 클수록 불확실성이 크다고 보고 소폭 감산합니다.

            이 계산은 통계적 예측 모델이나 학교의 공식 산출 방식이 아니며, 입력된 데이터가 적을수록 실제 결과와 차이가 커질 수 있습니다.
            """
        )
