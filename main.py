from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Sos el editor jefe digital de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.

ESTILO DIARIO ENE:
- Título directo, sin vueltas
- Urgencia funcional, no exagerada
- Lenguaje claro, sobrio, cero adjetivos grandilocuentes
- Pensado para el lector patagónico

Evitar: "en el marco de", "con el objetivo de", "se llevó a cabo", párrafos de longitud idéntica.
Negrita: nombres propios, datos numéricos, keywords SEO. Cursiva: marcas, términos técnicos. Máx 15% del texto.

RESPONDÉ SOLO con JSON válido (sin markdown):
{"seccion":"","kw_principal":"","kw_secundarias":["","","","",""],"kw_longtail":["","",""],"tipo_guia":false,"etiquetas":["","","",""],"volanta":"","titulo":"","copete":"","desarrollo":"","bloque_guia":null,"interlinking":[{"frase":"","destino":""}],"micro_seo":"","rrss":{"instagram":"","twitter":"","facebook":""},"newsletter":"","titulos":[{"tipo":"Informativo puro","texto":""},{"tipo":"Informativo puro","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Híbrido estratégico","texto":""}],"titulo_recomendado_index":0,"titulo_recomendado_razon":"","meta_title":"","meta_description":"","slug":"","revision":{"variacion_ritmo":true,"dato_local":true,"sin_genericos":true,"observaciones":""},"portada":"","horario":""}"""


class FetchRequest(BaseModel):
    urls: list[str]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}


async def fetch_article_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; DiarioENE/1.0)"}
            r = await client.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
                tag.decompose()
            body = (
                soup.find("article")
                or soup.find(class_=lambda c: c and "content" in c)
                or soup.find(class_=lambda c: c and "nota" in c)
                or soup.body
            )
            text = body.get_text(separator=" ", strip=True) if body else ""
            return " ".join(text.split())[:3000]
    except Exception as e:
        return f"(error al obtener texto: {e})"


async def fetch_listing(url: str) -> list[dict]:
    """Fetch article list from a news source homepage."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; DiarioENE/1.0)"}
            r = await client.get(url, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            articles = []
            seen = set()

            if "prensa.rionegro.gov.ar" in url:
                links = soup.find_all("a", href=lambda h: h and "/articulo/" in h)
                for a in links:
                    href = a.get("href", "")
                    full_url = href if href.startswith("http") else f"https://prensa.rionegro.gov.ar{href}"
                    if full_url in seen:
                        continue
                    seen.add(full_url)
                    heading = a.find(["h2", "h3", "h4"])
                    title = (heading or a).get_text(strip=True).replace("\n", " ")
                    if not title or len(title) < 20:
                        continue
                    parent = a.find_parent("article") or a.parent
                    sec_el = parent.find(class_=lambda c: c and any(x in c for x in ["categ", "section", "tag"])) if parent else None
                    sec = sec_el.get_text(strip=True) if sec_el else "Río Negro"
                    img_el = parent.find("img") if parent else None
                    img = img_el.get("src") or img_el.get("data-src") if img_el else None
                    # fix next/image URLs
                    if img and "_next/image" in img:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(img)
                        params = urllib.parse.parse_qs(parsed.query)
                        img = urllib.parse.unquote(params.get("url", [""])[0])
                    articles.append({"url": full_url, "title": title, "sec": sec, "img": img, "source": "Prensa Río Negro"})
                    if len(articles) >= 16:
                        break
            return articles
    except Exception as e:
        return []


@app.get("/")
def root():
    return {"status": "ENE Redactor API ok"}


@app.get("/noticias")
async def get_noticias(fuente: str = "prensa"):
    sources = {
        "prensa": "https://prensa.rionegro.gov.ar/",
        "muni": "https://www.bariloche.gov.ar/prensa/",
    }
    url = sources.get(fuente, sources["prensa"])
    articles = await fetch_listing(url)
    return {"articles": articles, "total": len(articles)}


@app.post("/generar")
async def generar(req: FetchRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY no configurada")

    # Fetch text for each URL
    texts = []
    for url in req.urls:
        text = await fetch_article_text(url)
        texts.append(f"URL: {url}\n\n{text}")

    combined = "\n\n---\n\n".join(texts)

    user_msg = f"Procesá estas fuentes y generá la nota ENE:\n\n{combined}"
    if req.seccion:
        user_msg += f"\n\nSECCIÓN FORZADA: {req.seccion}"
    if req.tono != "informativo":
        user_msg += f"\n\nTONO: {req.tono}"
    if not req.extras.get("rrss"):
        user_msg += "\n\nDejar rrss vacío."
    if not req.extras.get("newsletter"):
        user_msg += "\n\nDejar newsletter vacío."
    if not req.extras.get("micro_seo"):
        user_msg += "\n\nDejar micro_seo vacío."

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_msg}],
            },
        )

    if resp.status_code != 200:
        raise HTTPException(500, f"Error API Anthropic: {resp.text}")

    data = resp.json()
    raw = "".join(b.get("text", "") for b in data.get("content", []))
    raw = raw.replace("```json", "").replace("```", "").strip()

    import json
    try:
        parsed = json.loads(raw)
    except Exception:
        raise HTTPException(500, "No se pudo parsear la respuesta de la IA")

    return parsed
