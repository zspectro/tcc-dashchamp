import streamlit as st
import firebase_admin
from firebase_admin import auth

from jogos import obter_inicio_primeiro_jogo
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import firestore
from firebase_admin import auth

import secrets
import string



def _ir_para_tela(tela: str) -> None:
    st.session_state.tela = tela

def _ir_para_sala(tela: str, sala_id: str) -> None:
    st.session_state.tela = tela
    st.session_state.sala_id = sala_id
    
def _gerar_codigo():
    letras = string.ascii_uppercase
    return ''.join(secrets.choice(letras) for _ in range(4))
    
    


def salas(db, uid):
    
    user = auth.get_user(uid)
    nome_usuario = user.display_name
    
    def _checar_participante(id_usuario):
        salas_participadas = {}
        for salas in db.collection("salas").stream():
            salas_p = salas.to_dict()
            participantes_ref = db.collection("salas").document(salas.id).collection("participantes").stream()
            
            for participante in participantes_ref:
                if participante.id == id_usuario:
                    print(f"usuario esta na sala {salas_p['nome']}")
                    nome = salas_p['nome']
                    salas_participadas[salas.id] = nome
                    break
                else:
                    print(f"usuário não está na sala {salas_p['nome']}")
        print(salas_participadas)

        if salas_participadas:
            return salas_participadas
        else:
            print(f"O usuário {id_usuario} não participa de nenhuma sala.")
        
    
    
    st.title("Salas")
    st.write("Crie uma sala ou entre em uma sala existente.")

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
            try:
                inicio_primeiro_jogo = obter_inicio_primeiro_jogo(rodadas_abertas[rodada_id])
            except (OSError, ValueError):
                inicio_primeiro_jogo = None
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

                lote.create(sala_ref, {
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
                st.success(f"Sala criada! ID: {sala_ref.id}")
            else:
                st.error("Por favor, complete todos os campos.")

        st.button("Voltar", use_container_width=True, on_click=_ir_para_tela, args=("menu",))

    with col2:
        st.subheader("Entrar em uma sala")
        
        codigo_sala = st.text_input("Código da sala", key="codigo_sala")
        
        if st.button("Entrar", type="primary", use_container_width=True):
            if codigo_sala.strip():
                st.success(f"Entrando na sala {codigo_sala}...")
            else:
                st.error("Por favor, digite o código da sala.")
                
    st.write("Suas salas:")
    salas_player = _checar_participante(uid)
    if salas_player:
        container = st.container(border=True, width=600, height=200)
        for sala in salas_player:
            container.button(f"{salas_player[sala]}", on_click=_ir_para_sala, args=("detalhes_sala", sala,))
    else:
        st.write("Você não participa de nenhuma sala.")
