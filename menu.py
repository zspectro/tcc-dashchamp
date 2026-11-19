from html import escape
from jogos import obter_jogos_por_dia

import streamlit as st
from requests import RequestException

from noticias import obter_noticias_por_tema


def _mover_carrossel(chave: str, direcao: int, quantidade: int) -> None:
    indice_atual = st.session_state.get(chave, 0)
    st.session_state[chave] = (indice_atual + direcao) % quantidade


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
    
def _html_jogo(jogo: dict) -> str:
    """Uma linha: Mandante x Visitante  horário (tudo em uma linha só)."""
    mandante = escape(jogo["mandante"])
    visitante = escape(jogo["visitante"])
    horario = escape(jogo["horario"])
    return f'<h3 class="texto">{mandante} x {visitante} <small>{horario}</small></h3>'


def _mostrar_carrossel_do_tema(noticias: list[dict], numero_aba: int) -> None:
    """Mostra o carrossel (cartão + botões) de UM tema, com posição própria."""
    if not noticias:
        st.info("Nenhuma notícia recente encontrada para este tema.")
        return

    chave = f"noticia_atual_{numero_aba}"   # cada aba lembra a própria posição
    quantidade = len(noticias)
    indice = st.session_state.get(chave, 0) % quantidade
    st.session_state[chave] = indice
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
            key=f"noticia_anterior_{numero_aba}",
            on_click=_mover_carrossel,
            args=(chave, -1, quantidade),
            disabled=quantidade < 2,
        )
        st.button(
            "Próxima",
            key=f"noticia_proxima_{numero_aba}",
            on_click=_mover_carrossel,
            args=(chave, 1, quantidade),
            disabled=quantidade < 2,
        )


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
                    temas = obter_noticias_por_tema()
                except RequestException as erro:
                    st.warning(
                        "Não foi possível carregar as notícias da Agência Brasil. "
                        f"Detalhes: {erro}"
                    )
                else:
                    # abas sempre verdes (selecionada, não selecionada e hover)
                    st.markdown(
                        """
                        <style>
                          /* texto das abas sempre verde */
                          .st-key-container2 [data-testid="stTab"],
                          .st-key-container2 [data-testid="stTab"] *,
                          .st-key-container2 [role="tab"],
                          .st-key-container2 [role="tab"] * {
                            color: #1B8A3A !important;
                          }
                          .st-key-container2 [data-testid="stTab"] p {
                            font-size: 13px;
                          }
                          /* linha da aba selecionada: qualquer elemento da lista
                             de abas que NÃO seja uma aba */
                          .st-key-container2 [role="tablist"] > :not([role="tab"]) {
                            background-color: #1B8A3A !important;
                          }
                          .st-key-container2 [data-testid="stTab"][aria-selected="true"]::after {
                            background-color: #1B8A3A !important;
                          }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    abas = st.tabs(list(temas))
                    for numero, (aba, noticias) in enumerate(zip(abas, temas.values())):
                        with aba:
                            _mostrar_carrossel_do_tema(noticias, numero)

        esquerda, centro, direita = st.columns([1, 1, 1])
        with centro:
            st.button("Salas", key="sala_button", wrap=True, on_click=_ir_para_tela, args=("salas",))

    with col3:
        with st.container(key="container3", height=600):
            st.markdown('<h1 class="titulo">Jogos</h1>', text_alignment="center", unsafe_allow_html=True)

            try:
                with st.spinner("Carregando jogos..."):
                    dias = obter_jogos_por_dia()
            except Exception as erro:
                st.warning(f"Não foi possível carregar os jogos. Detalhes: {erro}")
            else:
                for rotulo, jogos in dias:
                    st.markdown(
                        f'<h3 class="texto-menor-jogos"><strong style="font-weight:800">{escape(rotulo)}</strong></h3>',
                        text_alignment="left",
                        unsafe_allow_html=True,
                    )
                    for jogo in jogos:
                        st.markdown(_html_jogo(jogo), text_alignment="left", unsafe_allow_html=True)

        esquerda, centro, direita = st.columns([1, 3, 1])
        with centro:
            st.button("Sobre", key="sobre_button", on_click=_ir_para_tela, args=("sobre",))