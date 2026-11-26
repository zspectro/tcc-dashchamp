from datetime import datetime, timezone

from google.cloud import firestore


PALPITES = ("mandante", "empate", "visitante")


def obter_rodada(db, rodada_id):
    if rodada_id is None:
        return None

    rodada_id = str(rodada_id)
    rodadas = db.collection("rodadas")
    rodada = rodadas.document(rodada_id).get()
    if rodada_id.isdecimal() and (not rodada.exists or rodada.to_dict().get("numero") is None):
        # Salas antigas guardavam apenas o número, como 38.
        alternativa = rodadas.document(f"rodada-{rodada_id}").get()
        if alternativa.exists:
            rodada = alternativa
    return rodada if rodada.exists else None


def em_prazo(data, agora):
    return isinstance(data, datetime) and data.tzinfo is not None and data > agora


def confirmar_apostas(transacao, sala_ref, participante_ref, rodada_id_sala, rodada, palpites):
    sala = sala_ref.get(transaction=transacao).to_dict() or {}
    participante = participante_ref.get(transaction=transacao)
    if not participante.exists or sala.get("rodadaId") != rodada_id_sala:
        return "A sala ou a rodada mudou. Volte aos detalhes da sala."
    if participante.to_dict().get("apostasConfirmadasEm"):
        return "Suas apostas já foram confirmadas."

    jogos_ref = rodada.reference.collection("jogos")
    jogos = {doc.id: doc.to_dict() for doc in jogos_ref.stream(transaction=transacao)}
    if not jogos or jogos.keys() != palpites.keys() or any(p not in PALPITES for p in palpites.values()):
        return "Escolha um palpite para cada jogo da rodada."

    agora = datetime.now(timezone.utc)
    if not em_prazo(sala.get("fechaEm"), agora) or any(
        not em_prazo(jogo.get("inicioEm"), agora) or jogo.get("resultado") is not None
        for jogo in jogos.values()
    ):
        return "O prazo para apostar nesta sala terminou."

    # A confirmação e todos os palpites são gravados juntos. create impede sobrescritas.
    apostas = participante_ref.collection("apostas")
    for jogo_id, palpite in palpites.items():
        transacao.create(apostas.document(jogo_id), {
            "rodadaId": rodada.id,
            "palpite": palpite,
            "enviadaEm": firestore.SERVER_TIMESTAMP,
            "pontosRecebidos": None,
        })
    transacao.update(participante_ref, {"apostasConfirmadasEm": firestore.SERVER_TIMESTAMP})
    return None
