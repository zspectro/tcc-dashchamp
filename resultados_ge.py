import re
from unicodedata import normalize

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


TABELA_GE = "https://ge.globo.com/futebol/brasileirao-serie-a/"


def normalizar_time(nome):
    nome = normalize("NFKD", nome.casefold()).encode("ascii", "ignore").decode("ascii")
    nome = " ".join(re.findall(r"[a-z0-9]+", nome)).removeprefix("red bull ")
    return {"atletico pr": "athletico pr"}.get(nome, nome)


def extrair_resultados(cards):
    resultados = {}
    pagina = BeautifulSoup("".join(cards), "html.parser")
    for card in pagina.select(".lista-jogos__jogo"):
        status = card.select_one(".jogo__transmissao--broadcast")
        # O ge também mostra placares ao vivo. A legenda final distingue esses casos.
        if status is None or status.get_text(strip=True).casefold() != "saiba como foi":
            continue

        times = card.select(".equipes__nome")
        gols = card.select(".placar-box__valor--mandante, .placar-box__valor--visitante")
        data = card.select_one('meta[itemprop="startDate"]')
        temporada = data.get("content", "")[:4] if data else ""
        if len(times) != 2 or len(gols) != 2 or not temporada.isdecimal():
            continue
        placar = [gol.get_text(strip=True) for gol in gols]
        if not all(gol.isdecimal() for gol in placar):
            continue

        mandante, visitante = (normalizar_time(time.get_text(strip=True)) for time in times)
        casa, fora = map(int, placar)
        resultado = "empate" if casa == fora else "mandante" if casa > fora else "visitante"
        resultados[int(temporada), mandante, visitante] = resultado
    return resultados


def _ler_rodada(navegador):
    rotulo, cards = navegador.execute_script("""
        return [document.querySelector('.lista-jogos__navegacao--rodada')?.textContent,
                [...document.querySelectorAll('.lista-jogos__jogo')].map(j => j.outerHTML)];
    """)
    numero = re.match(r"\s*(\d+)", rotulo or "")
    return (int(numero[1]), cards) if numero and cards else None


def buscar_resultados_ge(rodadas):
    """Lê as rodadas no site com um único navegador por apuração."""
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument("--headless=new")
    opcoes.page_load_strategy = "eager"
    resultados = {}
    with webdriver.Chrome(options=opcoes) as navegador:
        navegador.set_page_load_timeout(30)
        navegador.get(TABELA_GE)
        espera = WebDriverWait(navegador, 15)
        atual, cards = espera.until(_ler_rodada)

        for numero in sorted(rodadas):
            while numero != atual:
                passo = 1 if numero > atual else -1
                direcao = "direita" if passo > 0 else "esquerda"
                seletor = f".lista-jogos__navegacao--seta-{direcao}.lista-jogos__navegacao--setas-ativa"
                seta = navegador.find_element(By.CSS_SELECTOR, seletor)
                navegador.execute_script("arguments[0].click()", seta)
                proxima = atual + passo
                anteriores = cards

                # Aguarda os jogos novos, pois o título pode mudar antes de a lista carregar.
                atual, cards = espera.until(
                    lambda nav: (dados := _ler_rodada(nav))
                    and dados[0] == proxima and dados[1] != anteriores and dados
                )
            resultados[numero] = extrair_resultados(cards)

    return resultados
