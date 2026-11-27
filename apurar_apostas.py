from datetime import datetime

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from apostas_db import PALPITES
from resultados_ge import buscar_resultados_ge, normalizar_time


def _apostas_pendentes(db, jogos, ids_rodadas):
    # pega os palpites confirmados que ainda precisam ser corrigidos
    for sala in db.collection("salas").stream():
        if str(sala.to_dict().get("rodadaId")) not in ids_rodadas:
            continue
        for participante in sala.reference.collection("participantes").stream():
            if not participante.to_dict().get("apostasConfirmadasEm"):
                continue
            apostas = participante.reference.collection("apostas")
            for aposta in apostas.where(filter=FieldFilter("pontosRecebidos", "==", None)).stream():
                # o documento do palpite usa o mesmo id do jogo dentro da rodada
                chave = aposta.to_dict().get("rodadaId"), aposta.id
                if chave in jogos:
                    # entrega um palpite por vez para a apuração
                    yield jogos[chave], participante.reference, aposta.reference


def _registrar_resultado(transacao, jogo_ref, resultado):
    jogo = jogo_ref.get(transaction=transacao).to_dict() or {}
    # mantém o resultado se ele já estiver no banco
    if not jogo or jogo.get("resultado") is not None:
        return False
    transacao.update(jogo_ref, {"resultado": resultado})
    return True


def _corrigir_aposta(transacao, jogo_ref, participante_ref, aposta_ref, resultado_ge):
    jogo = jogo_ref.get(transaction=transacao).to_dict() or {}
    aposta = aposta_ref.get(transaction=transacao).to_dict() or {}
    # confere se o jogo tem o resultado esperado e se o palpite ainda está pendente
    if (
        jogo.get("resultado") != resultado_ge
        or aposta.get("palpite") not in PALPITES
        or aposta.get("pontosRecebidos") is not None
    ):
        return False

    # a comparação vira 1 ponto para acerto e 0 para erro
    pontos = int(aposta["palpite"] == resultado_ge)
    # grava a correção e a pontuação de uma vez só para evitar ponto em dobro
    # o horário da correção vem do próprio banco
    transacao.update(aposta_ref, {"pontosRecebidos": pontos, "corrigidaEm": firestore.SERVER_TIMESTAMP})
    if pontos:
        # soma o ponto direto no total mais recente guardado no banco
        transacao.update(participante_ref, {"pontos": firestore.Increment(pontos)})
    return True


def apurar_apostas(db):
    """atualiza os jogos e corrige os palpites da rodada aberta no ge"""
    numero, resultados = buscar_resultados_ge()
    if not resultados:
        return numero, 0, 0

    rodadas = db.collection("rodadas").where(filter=FieldFilter("numero", "==", numero))
    ids_rodadas = {str(numero)}  # algumas salas antigas guardam só o número da rodada
    jogos = {}
    # a transação pode tentar de novo se outra execução mexer no mesmo jogo
    registrar = firestore.transactional(_registrar_resultado)
    atualizados = 0

    for rodada in rodadas.stream():
        ids_rodadas.add(rodada.id)
        temporada_rodada = rodada.to_dict().get("temporada")
        for doc in rodada.reference.collection("jogos").stream():
            jogo = doc.to_dict()
            inicio = jogo.get("inicioEm")
            # se faltar a temporada, usa o ano em que o jogo começa
            temporada = temporada_rodada or (inicio.year if isinstance(inicio, datetime) else None)
            mandante, visitante = jogo.get("mandante"), jogo.get("visitante")
            if not str(temporada).isdecimal() or not mandante or not visitante:
                continue

            # compara o ano e os dois times para achar o mesmo jogo no ge
            confronto = int(temporada), normalizar_time(mandante), normalizar_time(visitante)
            resultado = resultados.get(confronto)
            if resultado is None:
                continue
            # só soma 1 quando um resultado novo é gravado
            atualizados += registrar(db.transaction(), doc.reference, resultado)
            # inclui jogos com resultado já salvo para corrigir palpites que ficaram pendentes
            jogos[rodada.id, doc.id] = (doc.reference, resultado)

    if not jogos:
        raise ValueError(f"Nenhum dos jogos encerrados da rodada {numero} foi encontrado no banco de dados.")

    # corrige só os palpites dos jogos que foram conferidos no ge
    corrigir = firestore.transactional(_corrigir_aposta)
    corrigidas = 0
    for (jogo_ref, resultado), participante_ref, aposta_ref in _apostas_pendentes(db, jogos, ids_rodadas):
        # um palpite errado também conta como corrigido
        corrigidas += corrigir(db.transaction(), jogo_ref, participante_ref, aposta_ref, resultado)
    return numero, atualizados, corrigidas
