from html import escape

import streamlit as st
from requests import RequestException

from noticias import obter_noticias


def _mover_carrossel(direcao: int, quantidade: int) -> None:
    indice_atual = st.session_state.get("noticia_atual", 0)
    st.session_state.noticia_atual = (indice_atual + direcao) % quantidade


def _ir_para_tela(tela: str) -> None:
    st.session_state.tela = tela


def _html_card_noticia(noticia: dict, indice: int, quantidade: int) -> str:
    """Monta um cartão compacto para a notícia caber no painel de 600 px."""
    titulo = escape(str(noticia.get("titulo", "Notícia sem título")))
    resumo = escape(str(noticia.get("resumo", "")))
    imagem = str(noticia.get("imagem") or "").strip()
    categoria = escape(str(noticia.get("categoria", "Apostas e sociedade")))

    data = noticia.get("publicada_em")
    data_formatada = data.strftime("%d/%m/%Y às %H:%M") if data else "Data não identificada"
    data_formatada = escape(data_formatada)

    imagem_html = ""
    if imagem.startswith("https://"):
        imagem_html = (
            f'<img class="dash-noticia-imagem" src="{escape(imagem, quote=True)}" '
            f'alt="Imagem da notícia" loading="lazy">'
        )

    return f"""
    <style>
      .st-key-container2 h1.titulo {{
        color: #111111 !important;
        margin-top: 0.1rem !important;
        margin-bottom: 0.35rem !important;
      }}
      .st-key-container2 .st-key-inside-container {{
        background: #ffffff !important;
        padding: 9px !important;
        border-radius: 12px !important;
      }}
      .dash-noticia-card {{
        color: #111111 !important;
        background: #ffffff;
        margin: 0;
        padding: 0;
        font-family: 'Poppins', sans-serif;
        overflow: hidden;
      }}
      .dash-noticia-card * {{ box-sizing: border-box; }}
      .dash-noticia-titulo {{
        color: #111111 !important;
        font-size: 17px;
        font-weight: 700;
        line-height: 1.28;
        margin: 0 0 7px 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        overflow-wrap: anywhere;
      }}
      .dash-noticia-imagem {{
        width: 100%;
        height: 250px;
        display: block;
        object-fit: cover;
        object-position: center;
        border-radius: 8px;
        margin: 0 0 7px 0;
      }}
      .dash-noticia-resumo {{
        color: #111111 !important;
        font-size: 12px;
        line-height: 1.42;
        margin: 0 0 6px 0;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        overflow-wrap: anywhere;
      }}
      .dash-noticia-meta {{
        color: #333333 !important;
        font-size: 10px;
        line-height: 1.3;
        margin: 0;
      }}
    </style>
    <div class="dash-noticia-card">
      <div class="dash-noticia-titulo">{titulo}</div>
      {imagem_html}
      <div class="dash-noticia-resumo">{resumo}</div>
      <div class="dash-noticia-meta">{data_formatada} · {categoria} · Notícia {indice + 1} de {quantidade} · Agência Brasil</div>
    </div>
    """


def mostrar_menu():
    col1, col2, col3 = st.columns([1, 2, 1], gap="xlarge")

    with col1:
        with st.container(key="container1", height=600):
            st.markdown('<h1 class="titulo">Placar</h1>', text_alignment="center", unsafe_allow_html=True)
            for i in range(1, 11):
                st.markdown(
                    f'<h5 class="texto-menor">{i}- Jogador -- x pontos</h5>',
                    text_alignment="left",
                    unsafe_allow_html=True,
                )
            st.markdown(
                '<h5 class="texto-menor">11- Usuário -- x pontos</h5>',
                text_alignment="left",
                unsafe_allow_html=True,
            )

        esquerda, centro, direita = st.columns([1, 4, 1])
        with centro:
            st.button("Perfil", key="perfil_button", wrap=True, on_click=_ir_para_tela, args=("perfil",))

    with col2:
        with st.container(key="container2", height=600):
            st.markdown('<h1 class="titulo">Notícias</h1>', text_alignment="center", unsafe_allow_html=True)

            with st.container(key="inside-container"):
                try:
                    noticias = obter_noticias()
                except (RequestException, ValueError) as erro:
                    st.warning(
                        "Não foi possível carregar as notícias da Agência Brasil. "
                        f"Detalhes: {erro}"
                    )
                else:
                    if not noticias:
                        st.info("Nenhuma notícia relevante sobre apostas foi encontrada nas pesquisas.")
                    else:
                        quantidade = len(noticias)
                        indice = st.session_state.get("noticia_atual", 0) % quantidade
                        st.session_state.noticia_atual = indice
                        noticia = noticias[indice]

                        st.markdown(
                            _html_card_noticia(noticia, indice, quantidade),
                            unsafe_allow_html=True,
                        )
                        st.link_button(
                            "Ler notícia na Agência Brasil",
                            noticia["url"],
                            width="stretch",
                        )

                        with st.container(horizontal=True, horizontal_alignment="distribute"):
                            st.button(
                                "Anterior",
                                key="noticia_anterior",
                                on_click=_mover_carrossel,
                                args=(-1, quantidade),
                                disabled=quantidade < 2,
                            )
                            st.button(
                                "Próxima",
                                key="noticia_proxima",
                                on_click=_mover_carrossel,
                                args=(1, quantidade),
                                disabled=quantidade < 2,
                            )

        esquerda, centro, direita = st.columns([1, 1, 1])
        with centro:
            st.button("Salas", key="sala_button", wrap=True, on_click=_ir_para_tela, args=("salas",))

    with col3:
        with st.container(key="container3", height=600):
            st.markdown('<h1 class="titulo">Jogos</h1>', text_alignment="center", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">FLA x FLU</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">VAS x BOT</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">GRE x PAL</h3>', text_alignment="left", unsafe_allow_html=True)
            st.markdown('<h3 class="texto">mais jogos aq</h3>', text_alignment="left", unsafe_allow_html=True)

        esquerda, centro, direita = st.columns([1, 3, 1])
        with centro:
            st.button("Sobre", key="sobre_button", on_click=_ir_para_tela, args=("sobre",))
