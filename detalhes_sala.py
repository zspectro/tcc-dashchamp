import streamlit as st
import firebase_admin
from firebase_admin import auth
import datetime
import zoneinfo
from google.cloud.firestore_v1.base_query import FieldFilter

from apostas_db import em_prazo, obter_rodada

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def obter_numero_rodada(db, rodada_id):
    rodada = obter_rodada(db, rodada_id)
    return rodada.to_dict().get("numero") if rodada is not None else None


def formatar_data_brasilia(data):
    data_brasilia = data.astimezone(zoneinfo.ZoneInfo("America/Sao_Paulo"))
    mes = MESES[data_brasilia.month - 1]
    return f"{data_brasilia.day} de {mes} às {data_brasilia:%H:%M}"


def _ir_para_tela(tela: str) -> None:
    st.session_state.tela = tela
    
def detalhes_sala(db, uid, sala_id):
    st.title("Detalhes da Sala")
    sala_ref = db.collection("salas").document(sala_id)
    sala_doc = sala_ref.get()
    
    if sala_doc.exists:
        col1, col2, col3 = st.columns(3, gap="large")
        sala_data = sala_doc.to_dict()
        numero_rodada = obter_numero_rodada(db, sala_data.get("rodadaId"))
        participantes = {
            doc.id: doc.to_dict() for doc in sala_ref.collection("participantes").stream()
        }
        consulta = sala_ref.collection("participantes").where(
            filter=FieldFilter("uid", "==", sala_data['donoUid'])
        )
        dono_doc = consulta.stream()
        dono = next(dono_doc).to_dict()['nome']

        with col1:
            container = st.container(border=True, width=600, height="stretch")
            container.markdown(f'<h2 class="titulo-branco">Informações da Sala:</h2>', unsafe_allow_html=True)
            container.markdown(f"<strong>Criador da Sala:</strong> {dono}", unsafe_allow_html=True)
            container.markdown(f"<strong>Nome da Sala:</strong> {sala_data['nome']}", unsafe_allow_html=True)
            container.markdown(f"<strong>Número Máximo de Jogadores:</strong> {sala_data['maxJogadores']}", unsafe_allow_html=True)
            container.markdown(f"**Rodada do Campeonato:** {numero_rodada if numero_rodada is not None else 'Não informada'}")
            container.markdown(f"<strong>Código da Sala:</strong> {sala_data['codigo']}", unsafe_allow_html=True)
            container.markdown(f"**Jogos começam:** {formatar_data_brasilia(sala_data['fechaEm'])}")
            container.markdown(f"<strong>Visibilidade:</strong> {sala_data['visibilidade']}", unsafe_allow_html=True)
        

        
        with col2:
            container2 = st.container(border=True, width=600, height="stretch")
            container2.markdown('<h2 class="titulo-branco">Participantes:</h2>', unsafe_allow_html=True, text_alignment="center")
            cabecalho = container2.container(horizontal=True, horizontal_alignment="distribute")
            cabecalho.markdown("Nickname", width="content")
            cabecalho.markdown("Pontos", width="content")
            for jogador in participantes.values():
                foto = jogador.get("fotoUrl")

                container3 = container2.container(horizontal=True, vertical_alignment="center")
                if foto:
                    container3.image(foto, width=32)
                else:
                    container3.markdown(":material/account_circle:", width="content")

                if jogador["nome"] == dono:
                    container3.markdown(f"👑 {jogador['nome']}")
                    container3.markdown(jogador["pontos"], text_alignment="right", width="stretch")
                else:
                    container3.markdown(jogador["nome"])
                    container3.markdown(jogador["pontos"], text_alignment="right", width="stretch")
            
                    
                
        with col3:
            fechada = not em_prazo(sala_data.get("fechaEm"), datetime.datetime.now(datetime.timezone.utc))
            confirmou = bool(participantes.get(uid, {}).get("apostasConfirmadasEm"))
            with st.container(border=True, width=600, height="stretch"):
                st.markdown('<h2 class="titulo-branco">Realizar apostas da sala</h2>', unsafe_allow_html=True, text_alignment="center")
                st.space(24)
                with st.container(horizontal=True, horizontal_alignment="center"):
                    st.button(
                        "Ver apostas" if confirmou else "Apostar",
                        width="content",
                        key="apostar_button",
                        disabled=uid not in participantes or (fechada and not confirmou),
                        help="O prazo para apostar nesta sala terminou." if fechada and not confirmou else None,
                        on_click=_ir_para_tela,
                        args=("apostas",),
                    )
        st.button("Voltar", key="voltar_button", on_click=_ir_para_tela, args=("salas",))
    else:
        st.error("Sala não encontrada.")
        st.button("Voltar", key="voltar_button", on_click=_ir_para_tela, args=("salas",))
