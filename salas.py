import secrets
import string
from datetime import datetime, timezone

import streamlit as st
from firebase_admin import auth
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from detalhes_sala import formatar_data_brasilia, obter_numero_rodada

def _ir_para_tela(tela: str) -> None:
    st.session_state.tela = tela

def _ir_para_sala(tela: str, sala_id: str) -> None:
    st.session_state.tela = tela
    st.session_state.sala_id = sala_id
    
def _gerar_codigo():
    letras = string.ascii_uppercase
    return ''.join(secrets.choice(letras) for _ in range(4))


def _sala_disponivel(dados, agora, codigo=None):
    fecha_em = dados.get("fechaEm")
    visibilidade = str(dados.get("visibilidade", "")).strip().casefold()
    acesso_permitido = (
        visibilidade in {"pública", "publica"} if codigo is None else dados.get("codigo") == codigo
    )
    return (
        acesso_permitido
        and isinstance(fecha_em, datetime)
        and fecha_em.tzinfo is not None
        and fecha_em > agora
    )


def _listar_salas(db, uid):
    minhas_salas = {}
    salas_disponiveis = []
    agora = datetime.now(timezone.utc)
    for sala in db.collection("salas").stream():
        dados = sala.to_dict()
        participantes = sala.reference.collection("participantes")
        if _sala_disponivel(dados, agora):
            jogadores = list(participantes.stream())
            if not any(jogador.id == uid for jogador in jogadores):
                salas_disponiveis.append((sala, dados, len(jogadores)))
                continue
        elif not participantes.document(uid).get().exists:
            continue

        minhas_salas[sala.id] = dados["nome"]

    return minhas_salas, salas_disponiveis


def _registrar_participante(transacao, sala_ref, uid, nome_usuario, codigo=None):
    dados = sala_ref.get(transaction=transacao).to_dict() or {}
    if not _sala_disponivel(dados, datetime.now(timezone.utc), codigo):
        return "Esta sala não está disponível para entrada."

    participantes = sala_ref.collection("participantes")
    jogadores = list(participantes.stream(transaction=transacao))
    if any(jogador.id == uid for jogador in jogadores):
        return None
    if len(jogadores) >= dados.get("maxJogadores", 0):
        return "Esta sala está lotada."

    transacao.create(participantes.document(uid), {
        "nome": nome_usuario,
        "uid": uid,
        "entrouEm": firestore.SERVER_TIMESTAMP,
        "pontos": 0,
    })
    transacao.update(sala_ref, {"totalParticipantes": len(jogadores) + 1})
    return None


def _entrar_na_sala(db, sala_ref, uid, nome_usuario, codigo=None):
    try:
        entrar = firestore.transactional(_registrar_participante)
        erro = entrar(db.transaction(), sala_ref, uid, nome_usuario, codigo)
    except (GoogleAPICallError, ValueError):
        erro = "Não foi possível entrar na sala. Tente novamente."

    if erro:
        st.warning(erro)
    else:
        _ir_para_sala("detalhes_sala", sala_ref.id)
        st.rerun()


def salas(db, uid):
    
    user = auth.get_user(uid)
    nome_usuario = user.display_name
    
    st.title("Salas")
    st.write("Crie uma sala ou entre em uma sala existente.")

    salas_player, salas_disponiveis = _listar_salas(db, uid)
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("Criar sala")
        
        nome_sala = st.text_input("Nome da sala", key="nome_sala")
        
        max_jogadores = st.number_input(
            "Número máximo de jogadores", 
            min_value=1, 
            max_value=8, 
            value=8, 
            step=1,
            key="max_jogadores"
        )
        
        consulta_rodadas = db.collection("rodadas").where(filter=FieldFilter("aberta", "==", "sim"))
        rodadas_abertas = {doc.id: doc.to_dict()["numero"] for doc in consulta_rodadas.stream()}

        rodada_id = st.selectbox(
            "Rodada do campeonato",
            options=sorted(rodadas_abertas, key=rodadas_abertas.__getitem__),
            format_func=lambda id_rodada: f"Rodada {rodadas_abertas[id_rodada]}",
            key="rodada_campeonato",
            placeholder="Não há rodadas abertas" if not rodadas_abertas else None,
        )

        inicio_primeiro_jogo = None
        if rodada_id is not None:
            jogos = db.collection("rodadas").document(rodada_id).collection("jogos")
            primeiro = next(jogos.order_by("inicioEm").limit(1).stream(), None)
            if primeiro is not None:
                inicio_primeiro_jogo = primeiro.to_dict().get("inicioEm")
            if inicio_primeiro_jogo is None:
                st.warning("Não foi possível identificar o horário do primeiro jogo desta rodada.")

        visibilidade = st.radio(
            "Visibilidade da sala",
            options=["Pública", "Privada"],
            key="visibilidade"
        )

        criar_sala = st.button(
            "Criar sala", type="primary", width="stretch", disabled=inicio_primeiro_jogo is None
        )
        if criar_sala and inicio_primeiro_jogo is not None:
            if (nome_sala.strip()) :

                # Gera um ID automático para a sala. A gravação acontece no commit.
                sala_ref = db.collection("salas").document()
                dono_ref = sala_ref.collection("participantes").document(uid)

                lote = db.batch()

                lote.create(sala_ref, { #cria saala
                    "nome": nome_sala.strip(),
                    "codigo": _gerar_codigo(),
                    "rodadaId": rodada_id,
                    "donoUid": uid,
                    "visibilidade": visibilidade,
                    "maxJogadores": max_jogadores,
                    "totalParticipantes": max_jogadores,
                    "fechaEm": inicio_primeiro_jogo,
                    "criadoEm": firestore.SERVER_TIMESTAMP,
                })

                lote.create(dono_ref, {
                    "nome": nome_usuario,
                    "uid": uid,
                    "entrouEm": firestore.SERVER_TIMESTAMP,
                    "pontos": 0,
                })

                lote.commit()
                salas_player[sala_ref.id] = nome_sala.strip()
                st.success(f"Sala criada! ID: {sala_ref.id}")
            else:
                st.error("Por favor, complete todos os campos.")

        st.button("Voltar", use_container_width=True, on_click=_ir_para_tela, args=("menu",))

    with col2:
        
        with st.container(border=True, width=600, height=500):
            st.subheader("Entrar em uma sala")
            if not salas_disponiveis:
                st.caption("Nenhuma sala pública disponível.")

            numeros_rodadas = {}
            for sala, dados, total in salas_disponiveis:
                rodada_id_sala = dados.get("rodadaId")
                if rodada_id_sala not in numeros_rodadas:
                    numeros_rodadas[rodada_id_sala] = obter_numero_rodada(db, rodada_id_sala)
                numero = numeros_rodadas[rodada_id_sala]
                limite = dados.get("maxJogadores", 0)
                lotada = total >= limite

                with st.container(border=True):
                    st.subheader(dados["nome"])
                    st.markdown(f"**Jogadores:** {total}/{limite}")
                    st.markdown(f"**Rodada:** {numero if numero is not None else 'Não informada'}")
                    st.markdown(f"**Fecha em:** {formatar_data_brasilia(dados['fechaEm'])}")
                    if st.button(
                        "Sala lotada" if lotada else "Entrar",
                        key=f"entrar_publica_{sala.id}",
                        width="stretch",
                        disabled=lotada,
                    ):
                        _entrar_na_sala(db, sala.reference, uid, nome_usuario)

            codigo_sala = st.text_input("Código da sala", key="codigo_sala")

            if st.button("Entrar com código", type="primary", width="stretch"):
                codigo = codigo_sala.strip().upper()
                if len(codigo) != 4:
                    st.error("Digite um código de 4 caracteres.")
                else:
                    consulta = db.collection("salas").where(filter=FieldFilter("codigo", "==", codigo))
                    correspondencias = consulta.limit(2).get()
                    if len(correspondencias) == 1:
                        _entrar_na_sala(db, correspondencias[0].reference, uid, nome_usuario, codigo)
                    else:
                        st.error("Código de sala inválido.")
                
    st.write("Suas salas:")
    if salas_player:
        container = st.container(border=True, width=600, height="stretch")
        for sala in salas_player:
            container.button(f"{salas_player[sala]}", on_click=_ir_para_sala, args=("detalhes_sala", sala,))
    else:
        st.write("Você não participa de nenhuma sala.")
