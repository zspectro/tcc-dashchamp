import streamlit as st
def mostrar_sobre():
    col1, col2, col3 = st.columns([1,2,1], gap="xlarge")
    with col2:
        with st.container(key="container1", height=400):
            st.markdown('<h1 class="titulo">Sobre</h1>', text_alignment="center", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">Esse TCC foi criado pelos integrantes: Jhonathas de Oliveira, Bernardo William, Miguel Ferraz e Miguel Mathias.</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">Junto também com a ajuda da orientadora de TCC Michelle Freitas, e o coorientador Guilherme Godoy.</h3>', text_alignment="left", unsafe_allow_html=True)
        esquerda, centro, direita = st.columns([1, 1, 1])##alinha botao no meio
        with centro:
            st.button("Voltar", key="voltar_button", wrap=True, on_click=lambda: voltar_para_menu())
            def voltar_para_menu():
                st.session_state.tela = "menu"