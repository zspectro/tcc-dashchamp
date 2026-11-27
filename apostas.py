from datetime import datetime, timezone

import streamlit as st
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import firestore

from apostas_db import PALPITES, confirmar_apostas, em_prazo, obter_rodada
from detalhes_sala import formatar_data_brasilia


def _voltar():
    st.session_state.tela = "detalhes_sala"


def _opcoes(jogo):
    return {"mandante": jogo["mandante"], "empate": "Empate", "visitante": jogo["visitante"]}


def _mostrar_apostas(jogos_ref, participante_ref):
    # usa o id de cada jogo para achar o palpite na hora de mostrar a partida
    apostas = {doc.id: doc.to_dict() for doc in participante_ref.collection("apostas").stream()}
    for doc in jogos_ref.order_by("inicioEm").stream():
        jogo = doc.to_dict()
        aposta = apostas.get(doc.id, {})
        pontos = aposta.get("pontosRecebidos")
        with st.container(border=True):
            partida, situacao = st.columns([3, 2], vertical_alignment="center")
            partida.subheader(f"{jogo['mandante']} × {jogo['visitante']}")
            partida.caption(formatar_data_brasilia(jogo["inicioEm"]))
            palpite = _opcoes(jogo).get(aposta.get("palpite"), "Sem palpite")
            partida.write(f"Seu palpite: {palpite}")
            # valor vazio ainda está pendente e zero é um erro já corrigido
            if pontos is None:
                situacao.info("Aguardando apuração")
            elif pontos > 0:
                situacao.success("Acertou · +1 ponto")
            else:
                situacao.error("Errou · 0 pontos")


def mostrar_pagina_apostas(db, uid, sala_id):
    st.button("Voltar", on_click=_voltar)
    sala_ref = db.collection("salas").document(sala_id)
    sala = sala_ref.get().to_dict() or {}
    participante_ref = sala_ref.collection("participantes").document(uid)
    participante = participante_ref.get()
    if not sala or not participante.exists:
        st.warning("Entre na sala para acessar as apostas.")
        return

    st.title(f"Apostas · {sala['nome']}")
    rodada = obter_rodada(db, sala.get("rodadaId"))
    if rodada is None:
        st.warning("Rodada não encontrada.")
        return

    jogos_ref = rodada.reference.collection("jogos")
    # depois de confirmar, o jogador acompanha a situação dos palpites
    if participante.to_dict().get("apostasConfirmadasEm"):
        st.caption("Apostas confirmadas. Os pontos aparecem depois que a administração apura os jogos.")
        _mostrar_apostas(jogos_ref, participante_ref)
        return
    if not em_prazo(sala.get("fechaEm"), datetime.now(timezone.utc)):
        st.warning("O prazo para apostar nesta sala terminou.")
        return

    jogos = list(jogos_ref.order_by("inicioEm").stream())
    if not jogos:
        st.info("Ainda não há jogos cadastrados nesta rodada.")
        return

    with st.form(f"apostas_{sala_id}_{uid}"):
        palpites = {}
        for doc in jogos:
            jogo = doc.to_dict()
            with st.container(border=True):
                st.caption(formatar_data_brasilia(jogo["inicioEm"]))
                palpites[doc.id] = st.segmented_control(
                    f"Palpite para {jogo['mandante']} x {jogo['visitante']}",
                    PALPITES,
                    format_func=_opcoes(jogo).__getitem__,
                    key=f"palpite_{sala_id}_{uid}_{doc.id}",
                    label_visibility="collapsed",
                    width="stretch",
                )
        conferiu = st.checkbox("Conferi meus palpites e sei que a confirmação é definitiva.")
        confirmar = st.form_submit_button("Confirmar apostas", type="primary")

    if confirmar:
        if not conferiu or any(palpite is None for palpite in palpites.values()):
            st.warning("Escolha um palpite em cada jogo e marque a confirmação.")
            return
        try:
            gravar = firestore.transactional(confirmar_apostas)
            erro = gravar(db.transaction(), sala_ref, participante_ref, sala["rodadaId"], rodada, palpites)
        except (GoogleAPICallError, ValueError):
            erro = "Não foi possível confirmar as apostas. Atualize a página e tente novamente."
        if erro:
            st.warning(erro)
        else:
            st.rerun()
