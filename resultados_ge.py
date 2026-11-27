import re
from unicodedata import normalize

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


TABELA_GE = "https://ge.globo.com/futebol/brasileirao-serie-a/"


def normalizar_time(nome):
    # passa o nome para minúsculas e tira os acentos
    nome = normalize("NFKD", nome.casefold()).encode("ascii", "ignore").decode("ascii")
    # troca sinais como hífen por espaços e tira red bull do começo
    nome = " ".join(re.findall(r"[a-z0-9]+", nome)).removeprefix("red bull ")
    # aceita a grafia antiga do athletico e devolve os outros nomes como estão
    return {"atletico pr": "athletico pr"}.get(nome, nome)


def extrair_resultados(cards, rodada):
    resultados = {}
    # junta o html dos cartões para procurar os elementos pelas classes
    pagina = BeautifulSoup("".join(cards), "html.parser")
    jogos = pagina.select(".lista-jogos__jogo")
    # pula o primeiro jogo da rodada 37 porque ele ficou fora do banco
    if rodada == 37:
        jogos = jogos[1:] 

    for card in jogos:
        status = card.select_one(".jogo__transmissao--broadcast")
        # o ge mostra "saiba como foi" nos jogos que já acabaram
        if status is None or status.get_text(strip=True).casefold() != "saiba como foi":
            continue

        times = card.select(".equipes__nome")
        gol_mandante = card.select_one(".placar-box__valor--mandante")
        gol_visitante = card.select_one(".placar-box__valor--visitante")
        data = card.select_one('meta[itemprop="startDate"]')
        # pega o ano nos quatro primeiros caracteres da data
        temporada = data.get("content", "")[:4] if data else ""
        if len(times) != 2 or gol_mandante is None or gol_visitante is None or not temporada.isdecimal():
            continue
        placar = [gol.get_text(strip=True) for gol in (gol_mandante, gol_visitante)]
        # pula placares vazios ou com texto antes de converter os gols em números
        if not all(gol.isdecimal() for gol in placar):
            continue

        mandante, visitante = (normalizar_time(time.get_text(strip=True)) for time in times)
        # usa os gols para decidir quem ganhou ou se deu empate
        casa, fora = map(int, placar)
        resultado = "empate" if casa == fora else "mandante" if casa > fora else "visitante"
        resultados[int(temporada), mandante, visitante] = resultado
    return resultados


def _ler_rodada(navegador):
    # roda javascript no navegador para pegar o título da rodada e o html dos cartões
    rotulo, cards = navegador.execute_script("""
        return [document.querySelector('.lista-jogos__navegacao--rodada')?.textContent,
                [...document.querySelectorAll('.lista-jogos__jogo')].map(j => j.outerHTML)];
    """)
    # pega os primeiros dígitos de um título como 37ª rodada
    numero = re.match(r"\s*(\d+)", rotulo or "")
    # o retorno vazio faz a espera tentar ler a página de novo
    return (int(numero[1]), cards) if numero and cards else None


def buscar_resultados_ge():
    """busca os resultados da rodada que já abre no ge"""
    opcoes = webdriver.ChromeOptions()
    # abre o chrome sem mostrar uma janela
    opcoes.add_argument("--headless=new")
    # segue com o html pronto enquanto imagens e outros arquivos podem carregar
    opcoes.page_load_strategy = "eager"
    # o with fecha o navegador mesmo se a consulta der erro
    with webdriver.Chrome(options=opcoes) as navegador:
        navegador.set_page_load_timeout(30)
        navegador.get(TABELA_GE)
        # espera os jogos aparecerem antes de ler os placares
        rodada, cards = WebDriverWait(navegador, 15).until(_ler_rodada)
    return rodada, extrair_resultados(cards, rodada)
