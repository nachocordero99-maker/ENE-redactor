from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import urllib.parse
import json
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """Sos el editor jefe digital de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia.
ESTILO ENE: título directo, urgencia funcional, lenguaje claro, cero adjetivos grandilocuentes, pensado para el lector patagónico.
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
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["nav","header","footer","script","style","aside"]):
                tag.decompose()
            body = soup.find("article") or soup.find(class_=lambda c: c and "content" in c) or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return " ".join(text.split())[:3000]
    except Exception as e:
        return f"(error: {e})"

async def fetch_listing(source: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DiarioENE/1.0)"}
    articles = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:

        # Strategy 1: parse __NEXT_DATA__ from homepage
        try:
            r = await client.get("https://prensa.rionegro.gov.ar/", headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if script and script.string:
                data = json.loads(script.string)

                def find_article_lists(obj, depth=0):
                    if depth > 12:
                        return []
                    if isinstance(obj, list) and len(obj) >= 3:
                        if all(isinstance(x, dict) and ("title" in x or "titulo" in x) for x in obj[:2]):
                            return obj
                    if isinstance(obj, dict):
                        for v in obj.values():
                            r2 = find_article_lists(v, depth+1)
                            if r2:
                                return r2
                    return []

                items = find_article_lists(data)
                for item in items[:16]:
                    title = item.get("title") or item.get("titulo") or ""
                    if not title or len(str(title)) < 20:
                        continue
                    art_id = item.get("id") or item.get("articleId") or ""
                    slug = item.get("slug") or item.get("url_slug") or str(art_id)
                    full_url = f"https://prensa.rionegro.gov.ar/articulo/{art_id}/{slug}" if art_id else ""
                    sec = item.get("category") or item.get("section") or item.get("categoria") or "Río Negro"
                    if isinstance(sec, dict):
                        sec = sec.get("name") or sec.get("nombre") or "Río Negro"
                    img = item.get("image") or item.get("imagen") or item.get("thumbnail") or item.get("photo") or ""
                    if isinstance(img, dict):
                        img = img.get("url") or img.get("src") or ""
                    if img and "_next/image" in str(img):
                        parsed = urllib.parse.urlparse(str(img))
                        params = urllib.parse.parse_qs(parsed.query)
                        img = urllib.parse.unquote(params.get("url", [""])[0])
                    articles.append({
                        "url": full_url, "title": str(title).strip(),
                        "sec": str(sec).strip(),
                        "img": str(img).strip() if img else None,
                        "source": "Prensa Río Negro"
                    })
                if articles:
                    return articles
        except Exception as e:
            print(f"next_data error: {e}")

        # Strategy 2: scrape /archivo (sometimes server-side rendered)
        try:
            r = await client.get("https://prensa.rionegro.gov.ar/archivo", headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            seen = set()
            for a in soup.find_all("a", href=lambda h: h and "/articulo/" in str(h)):
                href = a.get("href", "")
                full_url = href if href.startswith("http") else f"https://prensa.rionegro.gov.ar{href}"
                if full_url in seen:
                    continue
                seen.add(full_url)
                heading = a.find(["h2","h3","h4","strong"])
                title = (heading or a).get_text(strip=True).replace("\n"," ").strip()
                if not title or len(title) < 20:
                    continue
                parent = a.find_parent(["article","li","div"])
                sec_el = None
                if parent:
                    for t in parent.find_all(["span","p","div"]):
                        classes = " ".join(t.get("class") or [])
                        if any(x in classes for x in ["categ","section","tag","category"]):
                            sec_el = t
                            break
                sec = sec_el.get_text(strip=True) if sec_el else "Río Negro"
                img_el = parent.find("img") if parent else None
                img = None
                if img_el:
                    raw = img_el.get("src") or img_el.get("data-src") or ""
                    if "_next/image" in raw:
                        parsed = urllib.parse.urlparse(raw)
                        params = urllib.parse.parse_qs(parsed.query)
                        img = urllib.parse.unquote(params.get("url",[""])[0])
                    elif raw.startswith("http"):
                        img = raw
                articles.append({"url":full_url,"title":title,"sec":sec,"img":img,"source":"Prensa Río Negro"})
                if len(articles) >= 16:
                    break
            if articles:
                return articles
        except Exception as e:
            print(f"archivo error: {e}")

        # Strategy 3: silvercoder API
        try:
            for api_url in [
                "https://silvercoder.rionegro.gov.ar/api/articles?limit=20&siteId=2",
                "https://silvercoder.rionegro.gov.ar/api/news?limit=20&siteId=2",
            ]:
                try:
                    r = await client.get(api_url, headers={**headers,"Accept":"application/json"})
                    if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                        data = r.json()
                        items = data if isinstance(data,list) else data.get("data",data.get("articles",[]))
                        for item in items[:16]:
                            title = item.get("title") or item.get("titulo") or ""
                            if not title or len(title) < 15:
                                continue
                            art_id = item.get("id") or ""
                            slug = item.get("slug") or str(art_id)
                            articles.append({
                                "url": f"https://prensa.rionegro.gov.ar/articulo/{art_id}/{slug}",
                                "title": str(title).strip(), "sec": "Río Negro",
                                "img": None, "source": "Prensa Río Negro"
                            })
                        if articles:
                            return articles
                except Exception:
                    continue
        except Exception as e:
            print(f"silvercoder error: {e}")

    return articles

@app.get("/")
def root():
    return {"status": "ENE Redactor API ok"}

@app.get("/noticias")
async def get_noticias(fuente: str = "prensa"):
    articles = await fetch_listing(fuente)
    return {"articles": articles, "total": len(articles)}

@app.post("/generar")
async def generar(req: FetchRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY no configurada")
    texts = []
    for url in req.urls:
        text = await fetch_article_text(url)
        texts.append(f"URL: {url}\n\n{text}")
    user_msg = f"Procesá estas fuentes y generá la nota ENE:\n\n{'---'.join(texts)}"
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
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":4000,"system":SYSTEM_PROMPT,"messages":[{"role":"user","content":user_msg}]},
        )
    if resp.status_code != 200:
        raise HTTPException(500, f"Error API: {resp.text}")
    data = resp.json()
    raw = "".join(b.get("text","") for b in data.get("content",[])).replace("```json","").replace("```","").strip()
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(500, "No se pudo parsear la respuesta")
@app.get("/debug")
async def debug():
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(
            "https://prensa.rionegro.gov.ar/",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        html = r.text[:3000]
        has_next_data = "__NEXT_DATA__" in r.text
        has_articulo = "/articulo/" in r.text
        return {
            "status": r.status_code,
            "has_next_data": has_next_data,
            "has_articulo_links": has_articulo,
            "html_preview": html
        }
