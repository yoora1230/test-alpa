from __future__ import annotations

import streamlit as st

from utils import (
    apply_common_style,
    export_backup_json,
    import_backup_json,
    init_state,
)

st.set_page_config(
    page_title="시험 플래너",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_state()
apply_common_style()

st.title("📚 나만의 시험 플래너")
st.caption("계획표 → 모의고사 성적 → 오답 분석 → 예상점수를 한 사이트에서 관리하세요.")

plan_count = len(st.session_state.plans)
completed_count = (
    int(st.session_state.plans["완료"].fillna(False).astype(bool).sum())
    if not st.session_state.plans.empty
    else 0
)
score_count = len(st.session_state.scores)
wrong_count = len(st.session_state.wrong_answers)

col1, col2, col3, col4 = st.columns(4)
col1.metric("계획 항목", f"{plan_count}개")
col2.metric("완료한 계획", f"{completed_count}개")
col3.metric("성적 기록", f"{score_count}개")
col4.metric("오답 기록", f"{wrong_count}개")

st.divider()

left, right = st.columns([1.4, 1])

with left:
    st.subheader("사이트 사용 순서")
    st.markdown(
        """
        1. **날짜별 계획표**에서 시험일까지의 공부 계획을 자동 생성하거나 직접 입력합니다.
        2. **모의고사 점수**에서 과목별 성적을 기록하고 변화 그래프를 확인합니다.
        3. **오답 노트**에서 틀린 문제의 원인과 복습 상태를 관리합니다.
        4. **예상 점수**에서 최근 성적과 오답 복습 결과를 바탕으로 계산된 추정치를 확인합니다.
        """
    )

    st.info(
        "왼쪽 사이드바에 표시되는 페이지 이름을 눌러 이동하세요. "
        "예상점수는 실제 성적을 보장하지 않는 학습 참고용 추정치입니다."
    )

with right:
    st.subheader("현재 진행률")
    progress = completed_count / plan_count if plan_count else 0.0
    st.progress(progress)
    st.write(f"계획 완료율: **{progress * 100:.1f}%**")

    if wrong_count:
        completed_wrong = int(
            st.session_state.wrong_answers["복습 상태"]
            .astype(str)
            .isin(["복습 완료", "완전히 이해"])
            .sum()
        )
        wrong_progress = completed_wrong / wrong_count
        st.progress(wrong_progress)
        st.write(f"오답 복습률: **{wrong_progress * 100:.1f}%**")
    else:
        st.write("오답을 등록하면 복습률이 표시됩니다.")

st.divider()

st.subheader("💾 데이터 백업과 복원")
st.write(
    "Streamlit의 세션이 끝나면 입력 데이터가 초기화될 수 있으므로, 중요한 데이터는 JSON 파일로 백업하세요."
)

backup_col, restore_col = st.columns(2)

with backup_col:
    st.download_button(
        label="백업 파일 다운로드",
        data=export_backup_json(),
        file_name="exam_planner_backup.json",
        mime="application/json",
        width="stretch",
    )

with restore_col:
    uploaded_file = st.file_uploader(
        "백업 파일 선택",
        type=["json"],
        label_visibility="collapsed",
    )
    if st.button(
        "선택한 백업 복원",
        disabled=uploaded_file is None,
        width="stretch",
    ):
        success, message = import_backup_json(uploaded_file.getvalue())
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

with st.expander("모든 데이터 초기화"):
    confirm_reset = st.checkbox("입력한 계획, 성적, 오답을 모두 삭제하는 것에 동의합니다.")
    if st.button("전체 초기화", type="primary", disabled=not confirm_reset):
        for key in ["plans", "scores", "wrong_answers"]:
            if key in st.session_state:
                del st.session_state[key]
        init_state()
        st.success("모든 데이터가 초기화되었습니다.")
        st.rerun()
