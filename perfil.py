import streamlit as st
import firebase_admin
from firebase_admin import auth
def perfil():
    user = auth.get_user(st.session_state.uid)
    nome_usuario = user.display_name
    col1, col2, col3 = st.columns([1,2,1], gap="large")
    with col2:
        with st.container(key="container1", height=500):
            st.markdown('<h1 class="titulo">Seu perfil</h1>', text_alignment="center", unsafe_allow_html=True)
            esquerda, direita = st.columns([3,1], gap="xxlarge")
            with esquerda:
                st.markdown(f'<h3 class="texto">Nome de usuário: {nome_usuario}</h3>', text_alignment="left", unsafe_allow_html=True)
                st.markdown('<h3 class="texto">Foto de perfil: </h3>', text_alignment="left", unsafe_allow_html=True)
                st.markdown('<h3 class="texto">Alterar tema: </h3>', text_alignment="left", unsafe_allow_html=True)
                st.markdown('<h3 class="texto">Histórico </h3>', text_alignment="left", unsafe_allow_html=True)
                st.markdown('<h3 class="texto">Alterar senha: </h3>', text_alignment="left", unsafe_allow_html=True)
            with direita:
                st.button("Alterar", key="alterar_nick_button")
                st.button("Alterar", key="alterar_foto_button")
                st.selectbox("Escolha o tema",("Escuro", "Claro"),key="tema",label_visibility="collapsed")
                st.button("Ver", key="ver_his_button")  
                st.button("Alterar", key="alterar_senha_button")
                
        esquerda, centro, direita = st.columns([1, 1, 1])##alinha botao no meio
        with centro:
            def voltar_para_menu():
                st.session_state.tela = "menu"
            st.button("Voltar", key="voltar_button", wrap=True, on_click=lambda: voltar_para_menu())
