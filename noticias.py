import calendar
import logging
import re
import unicodedata
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


URL_BUSCA = "https://busca.ebc.com.br/sites/agenciabrasil/nodes"
DOMINIO_NOTICIAS = "agenciabrasil.ebc.com.br"
MAX_POR_PESQUISA = 10
TEMPO_CACHE = 21600  

PESQUISAS = [
    ("Impactos financeiros", "impactos financeiros das apostas esportivas no Brasil"),
    ("Saúde mental e dependência", "saúde mental e dependência em apostas online"),
    ("Publicidade no futebol", "publicidade de bets e influência no futebol"),
    ("Regulamentação e fiscalização", "regulamentação e fiscalização das apostas online"),
    ("Manipulação de resultados", "manipulação de resultados e integridade esportiva"),
]

# Termo e peso. O título recebe a maior parte da pontuação.
PALAVRAS_CHAVE = [
    ("endividamento", 10), ("vício", 10), ("dependência", 10),
    ("prejuízo", 10), ("perdas financeiras", 10), ("saúde mental", 10),
    ("fraude", 10), ("manipulação de resultados", 10),
    ("superendividamento", 10), ("transtorno do jogo", 10),
    ("apostas esportivas", 9), ("bets", 9), ("apostas online", 9),
    ("compulsão", 9), ("dívidas", 9), ("impacto financeiro", 9),
    ("lavagem de dinheiro", 9), ("ludopatia", 9), ("falência", 9),
    ("perda de patrimônio", 9), ("publicidade", 8), ("regulamentação", 8),
    ("investigação", 8), ("irregularidades", 8), ("vulnerabilidade", 8),
    ("saúde pública", 8), ("dependência psicológica", 8),
    ("perdas econômicas", 8), ("recaída", 8), ("exploração financeira", 8),
    ("consumidores", 7), ("famílias", 7), ("influenciadores", 7),
    ("propaganda", 7), ("fiscalização", 7), ("prevenção", 7),
    ("conscientização", 7), ("superstição", 6), ("impulsividade", 7),
    ("crédito", 6), ("empréstimos", 7), ("inadimplência", 9),
    ("corrupção", 8), ("crime organizado", 8), ("fraude esportiva", 9),
    ("integridade esportiva", 8), ("patrocínio esportivo", 7),
    ("futebol brasileiro", 6), ("torcedores", 6),
    ("manipulação de mercado", 8), ("proteção ao consumidor", 8),
    ("restrição de acesso", 6), ("proibição", 6), ("bloqueio de contas", 7),
    ("publicidade abusiva", 9), ("jogo responsável", 7),
    ("autoexclusão", 8), ("pesquisa científica", 7),
    ("impactos sociais", 8), ("assistência psicológica", 8),
]

PALAVRAS_COMUNS = {
    "a", "as", "o", "os", "de", "da", "das", "do", "dos", "em",
    "no", "na", "nos", "nas", "e", "para", "por", "com", "sobre",
    "entre", "ao", "aos", "uma", "um", "brasil",
}

CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://busca.ebc.com.br/",
}


def _normalizar(texto: str) -> str:
    """Converte para minúsculas e remove acentos para comparar termos."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", texto).strip()


def _url_artigo_valida(url: str) -> bool:
    """Aceita URLs de matérias da Agência Brasil, incluindo rotas novas/antigas."""
    partes = urlparse(url)
    dominio = (partes.hostname or "").lower().removeprefix("www.")
    dominio_valido = (
        dominio == DOMINIO_NOTICIAS
        or dominio.endswith("." + DOMINIO_NOTICIAS)
    )
    caminho = partes.path.lower()

    caminho_valido = (
        "/noticia/" in caminho
        or re.search(r"^/node/\d+/?$", caminho) is not None
    )
    return partes.scheme in ("https", "http") and dominio_valido and caminho_valido


def _urls_de_artigo(href: str) -> list[str]:
    """Normaliza links diretos, relativos e URLs de matéria dentro de redirecionamentos."""
    href = unescape(str(href or "")).strip().replace("\\/", "/")
    if not href or href.startswith(("#", "javascript:", "mailto:")):
        return []

    candidatas = []
    valores = [href]

    atual = href
    for _ in range(2):
        partes = urlparse(atual)
        for chave, valores_parametro in parse_qs(partes.query).items():
            if chave.lower() in {"url", "u", "target", "destination", "dest", "redirect", "redirect_url", "link"}:
                valores.extend(valores_parametro)
        decodificado = unquote(atual)
        if decodificado == atual:
            break
        valores.append(decodificado)
        atual = decodificado

    for valor in list(valores):
        encontrados = re.findall(
            r"https?://(?:www\.)?agenciabrasil\.ebc\.com\.br[^\s\"'<>]+",
            valor,
            flags=re.IGNORECASE,
        )
        valores.extend(encontrados)

    for valor in valores:
        valor = unescape(str(valor)).strip().strip("\"'<> )]")
        if not valor:
            continue

        partes = urlparse(valor)
        if not partes.scheme and valor.startswith("//"):
            valor = "https:" + valor
            partes = urlparse(valor)
        elif not partes.scheme and valor.startswith("/"):

            valor = urljoin("https://agenciabrasil.ebc.com.br/", valor.lstrip("/"))
            partes = urlparse(valor)
        elif not partes.scheme:

            valor = urljoin("https://agenciabrasil.ebc.com.br/", valor)
            partes = urlparse(valor)

        if partes.scheme == "http" and _url_artigo_valida(valor):
            valor = "https://" + valor[len("http://"):]
        if _url_artigo_valida(valor):

            partes = urlparse(valor)
            url_limpa = f"https://{partes.netloc}{partes.path}"
            if url_limpa not in candidatas:
                candidatas.append(url_limpa)

    return candidatas


def _ler_data(texto: str, cartao=None) -> datetime | None:
    """Lê primeiro a data oficial exibida em p.info-new na lista de resultados."""
    if cartao:
        info_data = cartao.select_one("p.info-new")
        if info_data:
            texto_data = info_data.get_text(" ", strip=True)
            resultado = re.search(
                r"(\d{2}/\d{2}/\d{4})(?:\s+(?:às|as)\s+(\d{2}:\d{2}))?",
                texto_data,
                flags=re.IGNORECASE,
            )
            if resultado:
                data_texto, hora_texto = resultado.groups()
                formato = "%d/%m/%Y %H:%M" if hora_texto else "%d/%m/%Y"
                valor = f"{data_texto} {hora_texto}" if hora_texto else data_texto
                try:
                    return datetime.strptime(valor, formato)
                except ValueError:
                    pass

        marca_tempo = cartao.find("time")
        if marca_tempo:
            valor = marca_tempo.get("datetime", "").strip()
            if valor:
                try:
                    data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
                    if data.tzinfo is not None:
                        data = data.astimezone().replace(tzinfo=None)
                    return data
                except ValueError:
                    pass

    resultado = re.search(
        r"\b(\d{2}/\d{2}/\d{4})(?:\s+(?:às|as)\s+(\d{2}:\d{2}))?",
        texto,
        flags=re.IGNORECASE,
    )
    if not resultado:
        return None

    data_texto, hora_texto = resultado.groups()
    if hora_texto:
        try:
            return datetime.strptime(f"{data_texto} {hora_texto}", "%d/%m/%Y %H:%M")
        except ValueError:
            return None
    try:
        return datetime.strptime(data_texto, "%d/%m/%Y")
    except ValueError:
        return None


def _subtrair_meses(data: datetime, meses: int) -> datetime:
    """Retorna a data de meses atrás, ajustando meses com menos dias."""
    numero_mes = data.year * 12 + data.month - 1 - meses
    ano = numero_mes // 12
    mes = numero_mes % 12 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return data.replace(year=ano, month=mes, day=dia)

def _encontrar_cartao(link):
    """Procura o bloco visual que contém um resultado, sem depender de uma classe só."""
    for pai in link.parents:
        if pai.name in ("article", "li"):
            return pai

        classes = " ".join(pai.get("class", [])).lower() if pai.name else ""
        if any(palavra in classes for palavra in ("views-row", "search-result", "result-item", "node-result")):
            return pai

        if pai.name == "div" and pai.find("p") and len(pai.get_text(" ", strip=True)) < 1800:
            if any("/noticia/" in (a.get("href") or "") for a in pai.find_all("a", href=True)):
                return pai

    return link.parent


def _extrair_noticias(html: str, termo_pesquisa: str) -> list[dict]:
    """Lê resultados dentro de ul/li e mantém apenas notícias dos últimos 8 meses."""
    sopa = BeautifulSoup(html, "html.parser")
    noticias = []
    urls_vistas = set()
    agora = datetime.now()
    data_limite = _subtrair_meses(agora, 8)
    itens_lista = sopa.select("ul li")

    for item in itens_lista:
        marca_data = item.select_one("p.info-new")
        if not marca_data:
            continue

        data = _ler_data(marca_data.get_text(" ", strip=True), item)
        if data is None or data < data_limite or data > agora:
            continue

        urls_artigo = []
        links_item = item.find_all("a", href=True)
        for link in links_item:
            urls_artigo.extend(_urls_de_artigo(link.get("href", "")))
        urls_artigo = list(dict.fromkeys(urls_artigo))
        if not urls_artigo:
            continue

        titulo = ""
        for cabecalho in item.find_all(["h1", "h2", "h3", "h4", "h5"]):
            texto_cabecalho = re.sub(r"\s+", " ", cabecalho.get_text(" ", strip=True)).strip()
            if len(texto_cabecalho) >= 12:
                titulo = texto_cabecalho
                break

        if not titulo:
            for link in links_item:
                texto_link = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
                if len(texto_link) >= 12 and _normalizar(texto_link) not in {
                    "continuar lendo", "leia mais", "saiba mais", "ver mais"
                }:
                    titulo = texto_link
                    break

        if len(titulo) < 12:
            continue

        # O p.info-new contém só a data e a identificação da fonte; ele não é resumo.
        resumo = ""
        for paragrafo in item.find_all("p"):
            if "info-new" in paragrafo.get("class", []):
                continue
            texto_paragrafo = re.sub(r"\s+", " ", paragrafo.get_text(" ", strip=True)).strip()
            if len(texto_paragrafo) >= 35 and _normalizar(texto_paragrafo) != _normalizar(titulo):
                resumo = texto_paragrafo
                break

        if not resumo:
            texto_item = item.get_text(" ", strip=True)
            texto_item = texto_item.replace(marca_data.get_text(" ", strip=True), " ")
            texto_item = texto_item.replace(titulo, " ")
            resumo = re.sub(r"\s+", " ", texto_item).strip(" -|·")
        resumo = re.sub(r"\s+", " ", resumo).strip()
        if len(resumo) > 300:
            resumo = resumo[:297].rsplit(" ", 1)[0] + "..."

        imagem_url = None
        imagem = item.find("img")
        if imagem:
            caminho_imagem = (
                imagem.get("src") or imagem.get("data-src")
                or imagem.get("data-lazy-src") or imagem.get("data-original") or ""
            ).strip()
            if caminho_imagem:
                possivel_imagem = urljoin("https://busca.ebc.com.br/", caminho_imagem)
                dominio_imagem = (urlparse(possivel_imagem).hostname or "").lower()
                if possivel_imagem.startswith("https://") and (
                    dominio_imagem.endswith("ebc.com.br") or dominio_imagem.endswith("glbimg.com")
                ):
                    imagem_url = possivel_imagem

        url = urls_artigo[0]
        if url in urls_vistas:
            continue
        urls_vistas.add(url)
        noticias.append({
            "titulo": titulo,
            "resumo": resumo,
            "url": url,
            "imagem": imagem_url,
            "publicada_em": data,
            "termo_pesquisa": termo_pesquisa,
            "pontuacao": 0,
        })

        if len(noticias) >= MAX_POR_PESQUISA:
            break

    logger.info(
        "Busca EBC: termo=%r; itens li=%d; notícias recentes extraídas=%d; período a partir de %s; título=%r",
        termo_pesquisa,
        len(itens_lista),
        len(noticias),
        data_limite.strftime("%d/%m/%Y"),
        sopa.title.get_text(" ", strip=True) if sopa.title else "sem título",
    )
    if not noticias:
        exemplos_data = [
            li.select_one("p.info-new").get_text(" ", strip=True)
            for li in itens_lista if li.select_one("p.info-new")
        ][:5]
        logger.warning(
            "Nenhuma notícia recente extraída para %r. Datas de exemplo=%r. Início da página=%r",
            termo_pesquisa,
            exemplos_data,
            sopa.get_text(" ", strip=True)[:350],
        )

    return noticias

def _pontuar_titulo(titulo: str, termo_pesquisa: str) -> int:
    """Soma os pesos dos termos no título e dá bônus pela relação com a consulta."""
    titulo_normalizado = _normalizar(titulo)
    pontuacao = 0

    for palavra, peso in PALAVRAS_CHAVE:
        termo = _normalizar(palavra)
        if re.search(r"(?<!\w)" + re.escape(termo) + r"(?!\w)", titulo_normalizado):
            pontuacao += peso

    palavras_pesquisa = _normalizar(termo_pesquisa).split()
    palavras_titulo = set(titulo_normalizado.split())
    bonus = sum(
        2 for palavra in palavras_pesquisa
        if palavra not in PALAVRAS_COMUNS and len(palavra) > 2 and palavra in palavras_titulo
    )
    return pontuacao + min(bonus, 10)


def _escolher_melhores(resultados_por_tema: dict[str, list[dict]]) -> list[dict]:
    """Escolhe a melhor notícia por tema sem repetir o mesmo link."""
    selecionadas = []
    urls_selecionadas = set()

    for categoria, termo_pesquisa in PESQUISAS:
        resultados = resultados_por_tema.get(termo_pesquisa, [])
        for noticia in resultados:
            noticia["pontuacao"] = _pontuar_titulo(noticia["titulo"], termo_pesquisa)

        resultados.sort(key=lambda noticia: noticia["pontuacao"], reverse=True)
        escolhida = next(
            (noticia for noticia in resultados if noticia["url"] not in urls_selecionadas),
            None,
        )
        if escolhida:
            escolhida["categoria"] = categoria
            urls_selecionadas.add(escolhida["url"])
            selecionadas.append(escolhida)

    return selecionadas


@st.cache_data(ttl=TEMPO_CACHE, max_entries=1, show_spinner=False)
def obter_noticias() -> list[dict]:
    """Pesquisa cinco temas, coleta até 10 matérias recentes por tema e guarda em cache por 6h."""
    resultados_por_tema = {}
    buscas_com_sucesso = 0
    resultados_encontrados = 0
    max_paginas = 3  # tenta páginas extras caso os primeiros resultados sejam antigos

    for categoria, termo_pesquisa in PESQUISAS:
        resultados_tema = []
        urls_tema = set()

        for pagina in range(max_paginas):
            parametros = {"q": termo_pesquisa}
            if pagina > 0:
                parametros["page"] = pagina
            # sort=relevance fica no final da url, para ordenar por relevância
            parametros["sort"] = "relevance"
            url = f"{URL_BUSCA}?{urlencode(parametros)}"

            try:
                resposta = requests.get(url, headers=CABECALHOS, timeout=20)
                resposta.raise_for_status()
                if not resposta.encoding or resposta.encoding.lower() == "iso-8859-1":
                    resposta.encoding = resposta.apparent_encoding
                logger.info(
                    "Resposta da busca EBC: tema=%r, página=%d, status=%s, URL final=%s, tamanho=%s bytes",
                    termo_pesquisa,
                    pagina + 1,
                    resposta.status_code,
                    resposta.url,
                    len(resposta.content),
                )
            except requests.RequestException as erro:
                logger.warning("Falha na busca EBC '%s' (página %d): %s", termo_pesquisa, pagina + 1, erro)
                break

            buscas_com_sucesso += 1
            resultados_pagina = _extrair_noticias(resposta.text, termo_pesquisa)
            novos_resultados = 0
            for noticia in resultados_pagina:
                if noticia["url"] in urls_tema:
                    continue
                urls_tema.add(noticia["url"])
                resultados_tema.append(noticia)
                novos_resultados += 1
                if len(resultados_tema) >= MAX_POR_PESQUISA:
                    break

            if len(resultados_tema) >= MAX_POR_PESQUISA:
                resultados_tema = resultados_tema[:MAX_POR_PESQUISA]
                break
            if pagina > 0 and novos_resultados == 0:
                break

        resultados_por_tema[termo_pesquisa] = resultados_tema
        resultados_encontrados += len(resultados_tema)
        logger.info(
            "Total recente para %r: %d/%d notícias",
            termo_pesquisa,
            len(resultados_tema),
            MAX_POR_PESQUISA,
        )

    if buscas_com_sucesso == 0:
        raise requests.RequestException("Não foi possível acessar a busca da Agência Brasil.")

    if resultados_encontrados == 0:
        raise ValueError(
            "A busca da EBC abriu, mas não encontrou matérias com data válida nos últimos 8 meses. "
            "Confira no terminal as datas detectadas; a busca pode ter alterado sua paginação."
        )

    noticias_escolhidas = _escolher_melhores(resultados_por_tema)
    if not noticias_escolhidas:
        raise ValueError("Foram encontradas matérias recentes, mas nenhuma pôde ser selecionada.")

    return noticias_escolhidas

