from datetime import date

import pandas as pd
import streamlit as st

from common import SUBJECTS, WRONG_COLUMNS, init_state

st.set_page_config(page_title="오답 기록", page_icon="📝", layout="wide")
init_state()

st.title("📝 지금까지 틀린 문제")
st.caption("오답을 기록하고 해결 여부를 체크하면 계획표와 예상점수에 반영됩니다.")

with st.form("wrong_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        wrong_date = st.date_input("기록 날짜", value=date.today())
        subject = st.selectbox("과목", SUBJECTS)
    with col2:
        source = st.text_input("시험/교재", placeholder="예: 6월 모의고사")
        question_no = st.text_input("문항 번호", placeholder="예: 21")
    with col3:
        wrong_type = st.selectbox(
            "오답 유형",
            ["개념 부족", "계산 실수", "문제 해석", "시간 부족", "암기 부족", "기타"],
        )
        solved = st.checkbox("이미 해결함", value=False)

    note = st.text_area("오답 메모", placeholder="왜 틀렸는지와 다음에 주의할 점을 적어 보세요.")
    add_wrong = st.form_submit_button("오답 추가", type="primary", use_container_width=True)

if add_wrong:
    new_row = {
        "날짜": wrong_date.isoformat(),
        "과목": subject,
        "시험/교재": source.strip() or "미입력",
        "문항": question_no.strip() or "-",
        "오답유형": wrong_type,
        "메모": note.strip(),
        "해결": bool(solved),
    }
    st.session_state.wrong_questions = pd.concat(
        [st.session_state.wrong_questions, pd.DataFrame([new_row], columns=WRONG_COLUMNS)],
        ignore_index=True,
    )
    st.session_state.wrong_editor_version += 1
    st.success("오답을 추가했습니다.")

wrong_df = st.session_state.wrong_questions.copy()

if wrong_df.empty:
    st.info("아직 입력한 오답이 없습니다.")
else:
    wrong_df["해결"] = wrong_df["해결"].fillna(False).astype(bool)

    total = len(wrong_df)
    solved_count = int(wrong_df["해결"].sum())
    unsolved_count = total - solved_count
    col1, col2, col3 = st.columns(3)
    col1.metric("전체 오답", f"{total}문제")
    col2.metric("해결 완료", f"{solved_count}문제")
    col3.metric("미해결", f"{unsolved_count}문제")

    selected_filter = st.multiselect("표시할 과목", SUBJECTS, default=SUBJECTS)
    filtered = wrong_df[wrong_df["과목"].isin(selected_filter)].copy()

    st.subheader("해결 여부 수정")
    editor_key = f"wrong_editor_{st.session_state.wrong_editor_version}"
    edited = st.data_editor(
        filtered,
        hide_index=True,
        use_container_width=True,
        disabled=["날짜", "과목", "시험/교재", "문항", "오답유형", "메모"],
        column_config={
            "해결": st.column_config.CheckboxColumn("해결", help="다시 풀어 해결했다면 체크하세요."),
        },
        key=editor_key,
    )

    if st.button("해결 여부 저장", type="primary", use_container_width=True):
        original = st.session_state.wrong_questions.copy()
        for index in edited.index:
            if index in original.index:
                original.at[index, "해결"] = bool(edited.at[index, "해결"])
        st.session_state.wrong_questions = original
        st.session_state.wrong_editor_version += 1
        st.success("해결 여부를 저장했습니다.")
        st.rerun()

    st.subheader("과목별 미해결 오답")
    unsolved = wrong_df[~wrong_df["해결"]]
    if unsolved.empty:
        st.success("현재 미해결 오답이 없습니다.")
    else:
        counts = unsolved["과목"].value_counts().reindex(SUBJECTS, fill_value=0)
        st.bar_chart(counts)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "오답 CSV 다운로드",
            data=wrong_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="오답_기록.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        if st.button("가장 최근 오답 삭제", use_container_width=True):
            st.session_state.wrong_questions = st.session_state.wrong_questions.iloc[:-1].reset_index(drop=True)
            st.session_state.wrong_editor_version += 1
            st.rerun()
