import json
import re
import time
from datetime import date, datetime, timedelta
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://ge.globo.com/agenda/#/futebol"
URL_PARTIDAS_RODADA = "https://api.cartola.globo.com/partidas/{rodada}"
DIAS_A_FRENTE = 7
NOME_CAMPEONATO = "Campeonato Brasileiro"   # tem q ser o nome  exato
TEMPO_CACHE = 1800 

#roda dentro do navegador, acha cada cartão de jogo e o título do dia ao qual ele pertence.
JS_EXTRAIR = r"""
() => {
  const ehDia = /^[A-Za-zÀ-ú\-]+,\s*\d{2}\/\d{2}$/;   // regex q filtra só formatoo Dia / data ex: "Hoje, 18/11"
  const resultado = [];
  const vistos = new Set();
  let diaAtual = null;

  for (const el of document.querySelectorAll('*')) { // percorre todos elementos
    if (el.children.length > 0) continue;              // só elementos que têm apenas texto
    const texto = (el.textContent || '').trim();

    if (ehDia.test(texto)) { diaAtual = texto; continue; }
    if (!diaAtual || !texto.startsWith('Rodada')) continue;

    // sobe ate achar o bloco que tem os 2 brasões = o cartão do jogo
    let cartao = el;
    while (cartao && cartao.querySelectorAll('img').length < 2) cartao = cartao.parentElement; // sobe hierarquia até achar o cartão do jogo
    if (!cartao || vistos.has(cartao) || cartao.querySelectorAll('img').length !== 2) continue;
    vistos.add(cartao);

    resultado.push({ // guarda:
      dia: diaAtual, // dia
      rodada: texto,
      linhas: cartao.innerText.split('\n').map(l => l.trim()).filter(Boolean), // texto do cartão
      escudos: [...cartao.querySelectorAll('img')].map(i => i.currentSrc || i.src), // imagens dos brasões
    });
  }
  return resultado;
}
"""

# ignorar  esssas palavras
IGNORAR = ("rodada", "acompanhe", "onde assistir", "ao vivo", "pré-jogo",
           "fique por dentro", "hoje", "amanhã", "•")


def _eh_nome_de_time(linha):
    if linha.isdigit() or re.search(r"\d{1,2}:\d{2}", linha):
        return False
    return not any(palavra in linha.lower() for palavra in IGNORAR)


def _clicar(navegador, por, seletor):
    """Espera o elemento existir pra clicar"""
    elemento = WebDriverWait(navegador, 20).until(
        lambda nav: nav.find_elements(por, seletor)[0] if nav.find_elements(por, seletor) else False #
    )
    navegador.execute_script("arguments[0].click()", elemento)


def _buscar_cartoes(*, somente_primeiro=False):
    """Abre o ge, aplica o filtro do Brasileirão e devolve os cartões."""
    opcoes = webdriver.ChromeOptions()

    opcoes.add_argument("--window-size=1400,900")
    opcoes.add_argument("--headless=new")  # roda sem abrir janela
    navegador = webdriver.Chrome(options=opcoes)

    try:
        navegador.get(URL)

        #3 passos pra filtrar:
        
        # 1- clica no botão do filtro "campeonato"
        _clicar(navegador, By.CSS_SELECTOR, '[data-filter-id="CHAMPIONSHIP"]') #procura pelo botão usando a classe csss dele
        time.sleep(1)

        # 2- opção do pop-up: procura pelo texto exato e clica
        _clicar(
            navegador,
            By.XPATH,
            f"//p[contains(@class, 'SelectionModrawerContentstyles__ItemLabel') "
            f"and normalize-space()='{NOME_CAMPEONATO}']", #procura usando 2 coisas, a classe e o texto exato
        )
        time.sleep(1)

        # 3- clica no botão "Filtrar" para confirmar
        _clicar(
            navegador,
            By.XPATH,
            "//span[contains(@class, 'SelectionModrawerContentstyles__ButtonCTALabel') "
            "and normalize-space()='Filtrar']", #msm coisa que de cima
        )
        time.sleep(3)   # espera a lista de jogos atualizar

        if not somente_primeiro:
            # rola a página para carregar os dias seguintes
            for _ in range(8):
                navegador.execute_script("window.scrollBy(0, 1500)")
                time.sleep(0.4)

        cartoes = navegador.execute_script("return (" + JS_EXTRAIR + ")()")
    finally:
        navegador.quit()

    return cartoes


def _montar_jogos():
    hoje = date.today()
    limite = hoje + timedelta(days=DIAS_A_FRENTE)
    por_dia = {}

    for c in _buscar_cartoes():
        texto = " ".join(c["linhas"])
        if "ao vivo" in texto.lower() or "encerrado" in texto.lower():  #busca só jogos q não aconteceram
            continue  

        hora = re.search(r"(\d{1,2}):(\d{2})", texto) 
        data = re.search(r"(\d{2})/(\d{2})", c["dia"]) #procura data
        nomes = [l for l in c["linhas"] if _eh_nome_de_time(l)] #encontra os nomes dos times
        if not hora or not data or len(nomes) < 2 or len(c["escudos"]) < 2:
            continue

        try:
            data_jogo = date(hoje.year, int(data.group(2)), int(data.group(1)))
        except ValueError:
            continue
        if (data_jogo - hoje).days < -180:    
            data_jogo = data_jogo.replace(year=hoje.year + 1)
        if not (hoje <= data_jogo <= limite):
            continue

        dia = por_dia.setdefault(data_jogo, {"rotulo": c["dia"], "jogos": []}) #jogos do dia
        dia["jogos"].append({ #guarda infos dos jogos
            "mandante": nomes[-2],
            "visitante": nomes[-1],
            "escudo_mandante": c["escudos"][0],
            "escudo_visitante": c["escudos"][1],
            "horario": f"{int(hora.group(1)):02d}:{hora.group(2)}",
        })

    return [
        (dia["rotulo"], sorted(dia["jogos"], key=lambda j: j["horario"])) #ordena pelo horário
        for _, dia in sorted(por_dia.items())
    ]


@st.cache_data(ttl=TEMPO_CACHE, show_spinner=False)
def obter_jogos_por_dia():
    return _montar_jogos()


@st.cache_data(ttl=TEMPO_CACHE, show_spinner="Consultando a rodada do Brasileirão...")
def obter_rodada_atual() -> int | None:
    cartoes = _buscar_cartoes(somente_primeiro=True)
    if not cartoes:
        return None

    rodada = re.match(r"Rodada\s+(\d+)\b", cartoes[0]["rodada"])
    return int(rodada.group(1)) if rodada else None


@st.cache_data(ttl=TEMPO_CACHE, show_spinner="Consultando o primeiro jogo da rodada...")
def obter_inicio_primeiro_jogo(rodada: int) -> datetime | None:
    """Busca o primeiro horário da rodada, incluindo partidas adiantadas."""
    with urlopen(URL_PARTIDAS_RODADA.format(rodada=rodada), timeout=8) as resposta:
        dados = json.load(resposta)

    if dados.get("rodada") != rodada:
        return None

    horarios = (partida.get("timestamp") for partida in dados.get("partidas") or [])
    primeiro_horario = min((hora for hora in horarios if isinstance(hora, int) and hora > 0), default=None)
    if primeiro_horario is None:
        return None

    return datetime.fromtimestamp(primeiro_horario, ZoneInfo("America/Sao_Paulo"))


if __name__ == "__main__":
    for rotulo, jogos in _montar_jogos():
        print(rotulo)
        for j in jogos:
            print("  ", j["horario"], j["mandante"], "x", j["visitante"])
