import streamlit as st

st.markdown(
    """
    <style>
        div.stButton > button {
            background-color: #4CAF50;
            color: white;
            border-radius: 10px;
            border: none;
            padding: 0.5rem 1.2rem;
            font-size: 16px;
            width: 200px;
            transition: background-color 0.2s ease, transform 0.2s ease;
        }

        div.stButton > button:hover {
            background-color: #2d792f;
            transform: translateY(-1px);
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(page_title="DashChamp", page_icon="⚽", layout="centered")
with st.container(border=True, width=400, horizontal_alignment="center"):
    st.title(":blue[Dash]:green[Champ]", text_alignment="center")
    st.text_input("Usuário", placeholder="Digite seu usuário")
    st.text_input("Senha", placeholder="Digite sua senha", type="password")
    st.button("Não possui conta?", width=200)
    st.button("Esqueceu sua senha?", width=200) 