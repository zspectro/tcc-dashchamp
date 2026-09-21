import streamlit as st
def mostrar_menu():
    col1, col2, col3 = st.columns([1,2,1], gap="xlarge")
    with col1:
        with st.container(key="container1", height=600):
            st.markdown('<h1 class="titulo">Placar</h1>', text_alignment="center", unsafe_allow_html=True)
            for i in range(1,11):
                st.markdown(f'<h5 class="texto-menor">{i}- Jogador -- x pontos</h5>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h5 class="texto-menor">11- Usuário -- x pontos</h5>', text_alignment="left", unsafe_allow_html=True)
            
        esquerda, centro, direita = st.columns([1, 4, 1])##alinha botao no meio
        with centro:
            st.button("Perfil", key="perfil_button", wrap=True)
    with col2:
        with st.container(key="container2", height=600):
            st.markdown('<h1 class="titulo">Notícias</h1>', text_alignment="center", unsafe_allow_html=True)
            with st.container(key="inside-container"):##cria container dentro do outro, p conseguir ter scroll e organizar
                st.markdown('<h1 class="titulo">Título notícia</h1>', text_alignment="left", unsafe_allow_html=True)
                st.markdown('<h3 class="texto">Descrição notícia</h3>', text_alignment="left", unsafe_allow_html=True)
                st.markdown("""
                <div style="
                    width:300px;
                    height:200px;
                    background:#969696;
                    border-radius:10px;
                "></div>
                """, unsafe_allow_html=True) ##substiuir isso dps pela imagem de vdd, é só placeholder
        esquerda, centro, direita = st.columns([1, 1, 1])##alinha botao no meio
        with centro:
            st.button("Sala", key="sala_button", wrap=True)
    with col3:
        with st.container(key="container3", height=600):
            st.markdown('<h1 class="titulo">Jogos</h1>', text_alignment="center", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">FLA x FLU</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">VAS x BOT</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">GRE x PAL</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">mais jogos aq</h3>', text_alignment="left", unsafe_allow_html=True)
        esquerda, centro, direita = st.columns([1, 3, 1])##alinha botao no meio
        with centro:
            st.button("Sobre", key="sobre_button")
        