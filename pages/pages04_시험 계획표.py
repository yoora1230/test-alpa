import pandas as pd
import streamlit as st

from common import SUBJECTS, current_expected_scores, init_state

st.set_page_config(page_title="현재 예상점수", page_icon="🎯", layout="wide")
init_state()

st.title("🎯 현재 나의 예상점수")
st.caption("최근 최대 3회의 모의고사 성적, 최근 추세, 미해결 오답 수를 바탕으로 계산한 참고용 점수입니다.")

expected_df = current_expected_scores(
    st.session_state.mock_scores,
    st.session_state.wrong_questions,
)

metric_cols = st.columns(len(SUBJECTS))
for idx, row in expected_df.iterrows():
    metric_cols[idx].metric(
        row["과목"],
        f"{row['현재 예상점수']:.1f}점",
        f"미해결 {int(row['미해결 오답'])}개",
        delta_color="off",
    )

st.subheader("예상점수 비교")
chart_df = expected_df.set_index("과목")[["최근 3회 평균", "현재 예상점수"]]
st.bar_chart(chart_df)

st.subheader("계산 결과")
st.dataframe(expected_df, hide_index=True, use_container_width=True)

weakest = expected_df.sort_values(["현재 예상점수", "미해결 오답"], ascending=[True, False]).iloc[0]
strongest = expected_df.sort_values("현재 예상점수", ascending=False).iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.warning(
        f"우선 보완 과목: **{weakest['과목']}** · 예상 {weakest['현재 예상점수']:.1f}점 · "
        f"미해결 오답 {int(weakest['미해결 오답'])}개"
    )
with col2:
    st.success(f"현재 강점 과목: **{strongest['과목']}** · 예상 {strongest['현재 예상점수']:.1f}점")

st.info(
    "계산식: 최근 3회 평균 + 최근 점수 변화의 35% − 미해결 오답 1개당 0.8점(최대 12점). "
    "실제 시험 점수를 보장하는 예측 모델이 아니라 학습 우선순위를 정하기 위한 참고 지표입니다."
)

if st.session_state.mock_scores.empty:
    st.warning("모의고사 성적이 없어 과목별 기본값 70점을 사용했습니다. 먼저 성적을 입력하면 더 알맞게 계산됩니다.")
