import argparse
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from selenium.common.exceptions import WebDriverException

from apostas_db import PALPITES
from resultados_ge import buscar_resultados_ge, normalizar_time


def _apostas_pendentes(db):
    pendencias = defaultdict(list)
    for sala in db.collection("salas").stream():
        for participante in sala.reference.collection("participantes").stream():
            if not participante.to_dict().get("apostasConfirmadasEm"):
                continue
            apostas = participante.reference.collection("apostas")
            for aposta in apostas.where(filter=FieldFilter("pontosRecebidos", "==", None)).stream():
                chave = aposta.to_dict()["rodadaId"], aposta.id
                pendencias[chave].append((participante.reference, aposta.reference))
    return pendencias


def _corrigir_aposta(transacao, jogo_ref, participante_ref, aposta_ref):
    jogo = jogo_ref.get(transaction=transacao).to_dict() or {}
    aposta = aposta_ref.get(transaction=transacao).to_dict() or {}
    resultado = jogo.get("resultado")
    if resultado not in PALPITES or aposta.get("palpite") not in PALPITES or aposta.get("pontosRecebidos") is not None:
        return False

    pontos = int(aposta["palpite"] == resultado)
    # A marca de correção e o crédito são atômicos, inclusive se dois processos rodarem juntos.
    transacao.update(aposta_ref, {"pontosRecebidos": pontos, "corrigidaEm": firestore.SERVER_TIMESTAMP})
    if pontos:
        transacao.update(participante_ref, {"pontos": firestore.Increment(pontos)})
    return True


def apurar_apostas(db):
    pendencias = _apostas_pendentes(db)
    rodadas = {}
    jogos = {}
    consultar = set()
    agora = datetime.now(timezone.utc)

    for rodada_id, jogo_id in pendencias:
        if rodada_id not in rodadas:
            rodadas[rodada_id] = db.collection("rodadas").document(rodada_id).get()
        rodada = rodadas[rodada_id]
        if not rodada.exists:
            continue
        doc = rodada.reference.collection("jogos").document(jogo_id).get()
        jogo = doc.to_dict() or {}
        inicio = jogo.get("inicioEm")
        if not isinstance(inicio, datetime) or inicio.tzinfo is None or inicio > agora:
            continue
        dados_rodada = rodada.to_dict()
        numero = dados_rodada.get("numero")
        temporada = dados_rodada.get("temporada") or inicio.year
        jogos[rodada_id, jogo_id] = (doc, numero, temporada)
        if jogo.get("resultado") is None and type(numero) is int and 1 <= numero <= 38:
            consultar.add(numero)

    resultados = {}
    if consultar:
        try:
            resultados = buscar_resultados_ge(consultar)
        except WebDriverException as erro:
            print(f"Tabela do ge indisponível neste ciclo: {erro.msg}", flush=True)

    corrigir = firestore.transactional(_corrigir_aposta)
    corrigidas = 0
    for chave, (doc, numero, temporada) in jogos.items():
        jogo = doc.to_dict()
        resultado = jogo.get("resultado")
        if resultado is None:
            confronto = (temporada, normalizar_time(jogo["mandante"]), normalizar_time(jogo["visitante"]))
            resultado = resultados.get(numero, {}).get(confronto)
            if resultado is None:
                continue
            # Atualiza apenas a versão consultada, preservando o resultado se outra apuração já gravou.
            doc.reference.update({"resultado": resultado}, option=db.write_option(last_update_time=doc.update_time))

        for participante_ref, aposta_ref in pendencias[chave]:
            corrigidas += corrigir(db.transaction(), doc.reference, participante_ref, aposta_ref)
    return corrigidas


def main():
    parser = argparse.ArgumentParser(description="Apura os palpites com os resultados publicados pelo ge.")
    parser.add_argument("--monitorar", action="store_true", help="Repete a apuração a cada 5 minutos.")
    args = parser.parse_args()
    credencial = Path(__file__).with_name("serviceAccountKey.json")
    db = firestore.Client.from_service_account_json(str(credencial))

    while True:
        try:
            corrigidas = apurar_apostas(db)
            print(f"{corrigidas} aposta(s) corrigida(s).", flush=True)
        except (GoogleAPICallError, ValueError) as erro:
            print(f"Erro na apuração: {erro}", flush=True)
            if not args.monitorar:
                return 1
        if not args.monitorar:
            return 0
        time.sleep(300)


if __name__ == "__main__":
    raise SystemExit(main())
