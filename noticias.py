import re
from datetime import datetime, timedelta
from urllib.parse import urlencode, urljoin

import requests
import streamlit as st
from bs4 import BeautifulSoup

URL_BUSCA = "https://busca.ebc.com.br/sites/agenciabrasil/nodes"
DIAS_RECENTES = 150   # 5 meses
MAX_POR_TEMA = 5
TEMPO_CACHE = 21600

# Nome da aba - o que é digitado na busca
TEMAS = {
    "Apostas e bets": "apostas esportivas bets",
    "Vício e saúde mental": "ludopatia dependência apostas",
    "Endividamento": "endividamento apostas online",
    "Regulamentação": "regulamentação bets fiscalização",
    "Futebol e bets": "bets patrocínio futebol",
}


def _ler_data(texto):
    achou = re.search(r"(\d{2}/\d{2}/\d{4})(?:\s+(?:às|as)\s+(\d{2}:\d{2}))?", texto) #procura datas no formato dd/mm/aaaa
    if not achou:
        return None
    dia, hora = achou.groups()
    try:
        if hora:
            return datetime.strptime(f"{dia} {hora}", "%d/%m/%Y %H:%M")
        return datetime.strptime(dia, "%d/%m/%Y")
    except ValueError:
        return None
    
def _limpar(texto):
    return " ".join(texto.split()) # troca quebras de linha e espaços repetidos por um espaço só.


@st.cache_data(ttl=TEMPO_CACHE, show_spinner=False)
def buscar_noticias(termo):
    data_limite = datetime.now() - timedelta(days=DIAS_RECENTES) #pega só recente

    url = f"{URL_BUSCA}?{urlencode({'q': termo, 'sort': 'relevance'})}" #ssegue um modelo de url, daí só insere a pesquisa
    resposta = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20) # disfarça de navegador comum
    resposta.raise_for_status()
    if not resposta.encoding or resposta.encoding.lower() == "iso-8859-1":
        resposta.encoding = resposta.apparent_encoding
    sopa = BeautifulSoup(resposta.text, "html.parser") #trata comoo html

    noticias = []
    for item in sopa.select("ul li"): #cada li é umaa noticia, e ficam dentro de uma ul
        link = item.find("a", href=True)
        titulo = item.find(["h2", "h3", "h4"])
        info_data = item.select_one("p.info-new")
        if not link or not titulo or not info_data: #ignora se não tiver link título ou data
            continue

        data = _ler_data(info_data.get_text(" ", strip=True)) #lê a data, se nãoo tiver oou for antiga passa reto
        if data is None or data < data_limite:
            continue

        resumo = "" #cria um resumo com o primeiroo p
        for p in item.find_all("p"):
            if "info-new" not in p.get("class", []):
                resumo = _limpar(p.get_text(" ", strip=True)), "..."
                break

        imagem = item.find("img") #encontra imagem p usar
        noticias.append({ #salva as infos da noticia
            "titulo": _limpar(titulo.get_text(" ", strip=True)),
            "resumo": resumo[:300],
            "url": urljoin("https://agenciabrasil.ebc.com.br/", link["href"]),
            "imagem": urljoin("https://busca.ebc.com.br/", imagem["src"]) if imagem and imagem.get("src") else None,
            "publicada_em": data,
        })

        if len(noticias) >= MAX_POR_TEMA: #impede mais de 5 noticias por tema
            break

    return noticias


def obter_noticias_por_tema():
    """Retorna {nome_do_tema: [notícias]} sem repetir a mesma matéria entre temas."""
    resultado = {}
    links_vistos = set()

    for nome, termo in TEMAS.items():#percorre os temass e busca noticias
        noticias = buscar_noticias(termo)

        escolhidas = []
        for n in noticias:
            if n["url"] in links_vistos: #se a noticia ja foi vista, ignora
                continue
            links_vistos.add(n["url"]) #adiciona a noticia ao conjunto de vistas
            escolhidas.append({**n, "categoria": nome})  #guarda noticia, e copia oscampos da noticia, adicionando a categoria
        resultado[nome] = escolhidas

    return resultado