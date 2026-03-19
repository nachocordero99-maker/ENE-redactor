from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import os
import json
import re
from bs4 import BeautifulSoup

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")  # opcional, gratis en pexels.com/api

SYSTEM_PROMPT = """Actuá como editor jefe digital patagónico y estratega SEO de Diario ENE, medio regional con base en Bariloche y foco en Río Negro y la Patagonia. Tu tarea es crear un artículo periodístico optimizado al máximo nivel profesional, generando un texto original y natural.

ESTILO DIARIO ENE:
- Título directo, sin vueltas
- Urgencia funcional, no exagerada
- Foco en lo que pasa y por qué importa
- Lenguaje claro, sobrio, cero adjetivos grandilocuentes
- Pensado para el lector patagónico, no para gacetilla

Evitar siempre: "en el marco de", "con el objetivo de", "se llevó a cabo", estructuras simétricas y repetitivas, párrafos de longitud idéntica en serie.

Redacción humana y natural: variá la longitud de los párrafos, incluí observaciones editoriales propias, usá datos específicos locales, las citas deben estar destacadas dentro del desarrollo.

Texto enriquecido: Negrita para nombres propios relevantes, datos numéricos, keywords SEO principales y frases de alto impacto. Cursiva para marcas, términos técnicos o palabras en otro idioma. Máx 15-20% del texto.

ESTRUCTURA OBLIGATORIA DEL JSON:
- volanta: máx 3 palabras (topónimos no cuentan). Dos estilos: Causa+consecuencia O Lugar+situación. Nunca un sustantivo suelto.
- titulo: máx 80 caracteres
- copete: máx 200 caracteres, máx 3 oraciones, sin subordinadas, sin adjetivos
- desarrollo: 500-800 palabras. OBLIGATORIO incluir subtítulos <h3> cada 4-5 párrafos. Primer párrafo amplía el quién y el marco sin repetir el copete. Incluir citas destacadas con <blockquote>.
- interlinking: OBLIGATORIO entre 2 y 4 oportunidades. Jerarquía: 1) nota pilar de sección, 2) notas de profundidad, 3) sección temática. Cada uno con frase sugerida y destino.
- revision: 5 checks obligatorios: sin_estructura_identica, sin_expresiones_genericas, variacion_ritmo, dato_local_especifico, lectura_humana. Cada uno true/false + observacion si es false.

RESPONDÉ SOLO con JSON válido sin markdown:
{"seccion":"","kw_principal":"","kw_secundarias":["","","","",""],"kw_longtail":["","",""],"tipo_guia":false,"etiquetas":["","","",""],"etiqueta_sugerida":null,"volanta":"","titulo":"","copete":"","desarrollo":"","bloque_guia":null,"interlinking":[{"frase":"","destino":"","jerarquia":""}],"micro_seo":"","rrss":{"instagram":"","twitter":"","facebook":""},"titulos":[{"tipo":"Informativo puro","texto":""},{"tipo":"Informativo puro","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Impacto periodístico","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Explicativo / Contexto","texto":""},{"tipo":"Híbrido estratégico","texto":""}],"titulo_recomendado_index":0,"titulo_recomendado_razon":"","meta_title":"","meta_description":"","slug":"","revision":{"sin_estructura_identica":true,"sin_expresiones_genericas":true,"variacion_ritmo":true,"dato_local_especifico":true,"lectura_humana":true,"observaciones":""},"portada":"","horario":""}"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

SOURCES = {
    "prensa":    {"name":"Prensa Río Negro",   "url":"https://prensa.rionegro.gov.ar/busqueda/articulo?q=", "base":"https://prensa.rionegro.gov.ar",  "pattern":"/articulo/",  "type":"silvercoder"},
    "bariloche": {"name":"Bariloche Informa",  "url":"https://barilocheinforma.gob.ar/noticias/",           "base":"https://barilocheinforma.gob.ar", "pattern":"barilocheinforma.gob.ar/","type":"wordpress"},
    "policia":   {"name":"Policía Río Negro",  "url":"https://policia.rionegro.gov.ar/category/noticias/",  "base":"https://policia.rionegro.gov.ar", "pattern":"/policia.rionegro.gov.ar/",  "type":"wordpress"},
    "quorum":    {"name":"Quorum Legislativo", "url":"https://quorum.legisrn.gov.ar/",                      "base":"https://quorum.legisrn.gov.ar",   "pattern":"quorum.legisrn.gov.ar/","type":"wordpress"},
}

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Redactor ENE</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--ink:#04080f;--ink2:#2a3a4a;--ink3:#5a7a9a;--paper:#f5faff;--paper2:#e8f4fc;--paper3:#d8edf8;--blue:#3ab8e8;--blue2:#0a7ab8;--blue3:#061830;--border:#d0e4f0;--ok:#2a7a4b;--r:4px;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'DM Sans',sans-serif;background:var(--paper);color:var(--ink);min-height:100vh;}
header{background:var(--ink);border-bottom:3px solid var(--blue);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.logo{display:flex;flex-direction:column;line-height:1;}
.logo-d{font-size:9px;font-style:italic;font-weight:300;color:var(--blue);letter-spacing:2px;}
.logo-e{font-family:'Instrument Serif',serif;font-size:24px;color:#fff;letter-spacing:-0.5px;}
.logo-e em{color:var(--blue);font-style:italic;}
#hst{font-size:11px;color:#1a4a6a;}
.main-tabs{display:flex;gap:2px;padding:20px 24px 0;max-width:1300px;margin:0 auto;}
.main-tab{padding:9px 20px;font-size:12px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:var(--r) var(--r) 0 0;border-bottom:none;cursor:pointer;}
.main-tab.on{background:#fff;color:var(--ink);border-bottom:1px solid #fff;margin-bottom:-1px;z-index:1;}
.wrap{max-width:1300px;margin:0 auto;padding:0 24px 48px;}
.panel{display:none;background:#fff;border:1px solid var(--border);border-radius:0 var(--r) var(--r) var(--r);padding:24px;}
.panel.on{display:block;}

/* PORTAL */
.src-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:20px;}
.src-chip{display:flex;align-items:center;gap:6px;padding:6px 14px;border:1px solid var(--border);border-radius:20px;font-size:12px;cursor:pointer;background:var(--paper);user-select:none;}
.src-chip input{display:none;}
.src-chip.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.btn{padding:9px 18px;background:var(--blue2);color:#fff;border:none;border-radius:var(--r);font-size:12px;font-weight:600;cursor:pointer;font-family:'DM Sans',sans-serif;}
.btn:hover{background:var(--blue);}
.btn:disabled{background:#bbb;cursor:not-allowed;}
.btn-sec{padding:9px 14px;background:transparent;border:1px solid var(--border);border-radius:var(--r);font-size:12px;color:var(--ink3);cursor:pointer;font-family:'DM Sans',sans-serif;}
.btn-sec:hover{border-color:var(--ink);color:var(--ink);}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;}
.card{border:1px solid var(--border);border-radius:var(--r);cursor:pointer;background:#fff;overflow:hidden;position:relative;transition:border-color .15s;}
.card:hover{border-color:var(--blue2);}
.card:hover .card-preview{display:-webkit-box;}
.card-preview{display:none;}
.card.sel{border:2px solid var(--blue2);box-shadow:0 0 0 3px rgba(58,184,232,.12);}
.card-chk{position:absolute;top:8px;right:8px;width:22px;height:22px;background:var(--blue2);color:#fff;border-radius:50%;font-size:12px;font-weight:700;display:none;align-items:center;justify-content:center;}
.card.sel .card-chk{display:flex;}
.card-body{padding:12px 14px;}
.card-sec{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.card-title{font-size:12px;font-weight:500;line-height:1.45;color:var(--ink);}
.card-src{font-size:10px;color:var(--ink3);margin-top:4px;}
.card-img{width:100%;height:90px;object-fit:cover;display:block;background:var(--paper3);}
.card-preview{font-size:11px;color:var(--ink3);line-height:1.5;margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
/* Modal preview */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(4,8,15,.6);z-index:1000;align-items:center;justify-content:center;}
.modal-overlay.on{display:flex;}
.modal-box{background:#fff;border-radius:6px;max-width:560px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.3);}
.modal-hdr{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;justify-content:space-between;gap:12px;position:sticky;top:0;background:#fff;}
.modal-title{font-size:14px;font-weight:600;color:var(--ink);line-height:1.4;flex:1;}
.modal-close{font-size:18px;color:var(--ink3);cursor:pointer;background:none;border:none;padding:0;line-height:1;flex-shrink:0;}
.modal-close:hover{color:var(--ink);}
.modal-img{width:100%;height:160px;object-fit:cover;display:block;}
.modal-body{padding:14px 18px;}
.modal-sec{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--blue2);margin-bottom:8px;}
.modal-text{font-size:13px;color:var(--ink2);line-height:1.8;white-space:pre-wrap;}
.modal-footer{padding:12px 18px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;position:sticky;bottom:0;background:#fff;}
.sel-footer{margin-top:18px;padding:12px 16px;background:var(--paper2);border:1px solid var(--border);border-radius:var(--r);display:flex;align-items:center;justify-content:space-between;gap:12px;}
.sel-info{font-size:13px;color:var(--ink2);}
.sel-info b{color:var(--blue2);}
.skl{background:linear-gradient(90deg,var(--paper2) 25%,var(--paper3) 50%,var(--paper2) 75%);background-size:200% 100%;animation:sk 1.2s infinite;border-radius:var(--r);height:90px;}
@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}
.preview-btn{position:absolute;bottom:8px;right:8px;font-size:9px;padding:3px 8px;background:var(--blue2);color:#fff;border:none;border-radius:3px;cursor:pointer;opacity:0;transition:opacity .15s;font-family:'DM Sans',sans-serif;z-index:2;}
.card:hover .preview-btn{opacity:1;}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(4,8,15,.6);z-index:1000;align-items:center;justify-content:center;}
.modal-overlay.on{display:flex;}
.modal-box{background:#fff;border-radius:var(--r);max-width:600px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 8px 40px rgba(0,0,0,.3);}
.modal-hdr{padding:14px 18px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;justify-content:space-between;gap:12px;position:sticky;top:0;background:#fff;z-index:1;}
.modal-title{font-size:14px;font-weight:600;color:var(--ink);line-height:1.4;flex:1;}
.modal-close{background:transparent;border:none;font-size:18px;color:var(--ink3);cursor:pointer;flex-shrink:0;padding:0 4px;}
.modal-close:hover{color:var(--ink);}
.modal-body{padding:18px;}
.modal-img{width:100%;max-height:220px;object-fit:cover;border-radius:var(--r);margin-bottom:14px;display:block;}
.modal-meta{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;}
.modal-tag{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:3px 8px;border-radius:2px;background:var(--paper2);color:var(--blue2);}
.modal-text{font-size:13px;color:var(--ink2);line-height:1.8;}
.modal-footer{padding:12px 18px;border-top:1px solid var(--border);display:flex;gap:8px;justify-content:flex-end;position:sticky;bottom:0;background:#fff;}

/* REDACTOR */
.gen-layout{display:grid;grid-template-columns:280px 1fr;gap:24px;}
.sub-tabs{display:flex;gap:4px;margin-bottom:14px;}
.sub-tab{padding:7px 14px;font-size:11px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:var(--r);cursor:pointer;}
.sub-tab.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.sub-panel{display:none;}
.sub-panel.on{display:block;}
textarea{width:100%;min-height:140px;padding:12px;font-family:'DM Sans',sans-serif;font-size:13px;line-height:1.7;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;resize:vertical;margin-bottom:10px;}
textarea:focus{border-color:var(--blue2);}
textarea::placeholder{color:#bbb;}
input[type=text]{width:100%;padding:9px 12px;font-family:'DM Sans',sans-serif;font-size:13px;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;margin-bottom:8px;}
input[type=text]:focus{border-color:var(--blue2);}
.slbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:8px;display:flex;align-items:center;gap:6px;}
.slbl::after{content:'';flex:1;height:1px;background:var(--border);}
.prev-list{display:flex;flex-direction:column;gap:6px;margin-bottom:14px;}
.prev-item{padding:8px 10px;background:var(--paper);border:1px solid var(--border);border-radius:var(--r);font-size:11px;color:var(--ink2);line-height:1.4;}
.prev-item small{display:block;font-size:9px;color:var(--ink3);text-transform:uppercase;letter-spacing:1px;margin-bottom:2px;}
.opts{background:var(--paper);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;margin-bottom:10px;}
.opt{padding:9px 12px;border-bottom:1px solid var(--paper3);}
.opt:last-child{border-bottom:none;}
.opt label{display:block;font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
select{width:100%;padding:7px 10px;font-family:'DM Sans',sans-serif;font-size:12px;color:var(--ink);background:#fff;border:1px solid var(--border);border-radius:var(--r);outline:none;appearance:none;}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;}
.chip{display:flex;align-items:center;gap:4px;padding:5px 10px;border:1px solid var(--border);border-radius:20px;font-size:11px;cursor:pointer;background:#fff;user-select:none;}
.chip input{display:none;}
.chip.on{background:var(--ink);color:#fff;border-color:var(--ink);}
.btn-gen{display:block;width:100%;padding:12px;background:var(--blue2);color:#fff;font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;border:none;cursor:pointer;border-radius:var(--r);}
.btn-gen:hover{background:var(--blue);}
.btn-gen:disabled{background:#bbb;cursor:not-allowed;}
.spin{display:none;width:13px;height:13px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:6px;}
.loading .spin{display:inline-block;}
@keyframes spin{to{transform:rotate(360deg)}}
.err{background:#fde8e3;border:1px solid #f5b8b0;border-radius:var(--r);padding:10px 14px;font-size:12px;color:#c83030;margin-top:10px;display:none;}
.err.on{display:block;}

/* OUTPUT con TABS de notas */
.out{min-height:400px;}
.empty{text-align:center;padding:60px 20px;color:var(--ink3);}
.note-tabs-wrap{margin-bottom:0;}
.note-tabs{display:flex;gap:2px;flex-wrap:wrap;margin-bottom:0;}
.note-tab{padding:7px 16px;font-size:11px;font-weight:500;border:1px solid var(--border);background:var(--paper2);color:var(--ink3);border-radius:var(--r) var(--r) 0 0;border-bottom:none;cursor:pointer;position:relative;}
.note-tab.on{background:#fff;color:var(--blue2);border-bottom:1px solid #fff;margin-bottom:-1px;z-index:1;font-weight:600;}
.note-tab .note-tab-status{font-size:9px;margin-left:4px;}
.note-tab-txt{cursor:pointer;}
.note-tab-close{margin-left:8px;color:var(--ink3);cursor:pointer;font-size:10px;padding:1px 4px;border-radius:2px;}
.note-tab-close:hover{background:var(--paper3);color:var(--ink);}
.note-panel{display:none;border:1px solid var(--border);border-radius:0 var(--r) var(--r) var(--r);padding:0;animation:fi .3s ease;}
.note-panel.on{display:block;}
@keyframes fi{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}

/* Fotos */
.photos-row{display:flex;gap:10px;padding:16px;background:var(--paper2);border-bottom:1px solid var(--border);flex-wrap:wrap;}
.photo-card{border:2px solid transparent;border-radius:var(--r);overflow:hidden;cursor:pointer;transition:all .15s;flex:0 0 auto;}
.photo-card:hover{border-color:var(--blue2);}
.photo-card.selected{border-color:var(--blue2);box-shadow:0 0 0 3px rgba(58,184,232,.2);}
.photo-card img{width:130px;height:87px;object-fit:cover;display:block;}
.photo-card.main-photo img{width:160px;height:107px;}
.photo-card.resized-photo img{width:130px;height:87px;}
.photo-label{font-size:9px;padding:3px 6px;background:rgba(0,0,0,.5);color:#fff;text-align:center;}
.photos-lbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-right:8px;display:flex;align-items:center;align-self:center;}

/* Secciones de output */
.sec{border-bottom:1px solid var(--border);}
.sec:last-child{border-bottom:none;}
.sec-hd{display:flex;align-items:center;justify-content:space-between;padding:8px 14px;background:var(--paper2);}
.sec-row{display:flex;align-items:center;gap:7px;}
.bdg{font-size:8px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:2px 6px;border-radius:2px;}
.b1{background:#e8f4ec;color:#2a7a4b;}.b2{background:#e4f0fc;color:var(--blue2);}.b3{background:#e8edf8;color:#2a4a9a;}.b4{background:#fdf6e3;color:#b8962e;}.b5{background:#f0e8f8;color:#6a2a9a;}.bx{background:#e4f4f8;color:#1a6a8a;}
.sec-nm{font-size:11px;font-weight:600;color:var(--ink2);}
.cp{font-size:10px;padding:4px 10px;background:transparent;border:1px solid var(--border);border-radius:20px;cursor:pointer;color:var(--ink3);font-family:'DM Sans',sans-serif;}
.cp:hover{border-color:var(--ink2);color:var(--ink);}
.cp.ok{background:var(--ok);color:#fff;border-color:var(--ok);}
.sec-body{padding:16px 18px;font-size:13px;line-height:1.8;color:var(--ink);white-space:pre-wrap;}
.kw-bl{padding:12px 16px;}
.kwr{margin-bottom:10px;}
.kwl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:5px;}
.kwcs{display:flex;flex-wrap:wrap;gap:5px;}
.kwc{font-size:11px;padding:3px 9px;border-radius:2px;border:1px solid var(--border);color:var(--ink2);background:var(--paper);}
.kwc.pr{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:500;}
.tl{padding:12px 16px;}
.ti{display:flex;gap:8px;padding:9px 0;border-bottom:1px solid var(--paper3);align-items:flex-start;}
.ti:last-child{border-bottom:none;}
.tt{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);min-width:90px;padding-top:2px;}
.tx{font-size:12px;color:var(--ink);flex:1;line-height:1.5;}
.ti.rec .tx{font-weight:600;color:var(--blue2);}
.rtag{font-size:8px;background:var(--blue2);color:#fff;padding:2px 6px;border-radius:2px;white-space:nowrap;}
.il-item{padding:8px 0;border-bottom:1px solid var(--paper3);display:flex;gap:10px;}
.il-item:last-child{border-bottom:none;}
.il-frase{font-size:12px;font-weight:500;color:var(--ink);flex:1;}
.il-dest{font-size:11px;color:var(--blue2);font-family:'DM Mono',monospace;}
.il-jer{font-size:9px;padding:2px 7px;border-radius:10px;background:var(--paper2);color:var(--ink3);white-space:nowrap;}
.mr{display:grid;grid-template-columns:110px 1fr;border-bottom:1px solid var(--paper3);}
.mr:last-child{border-bottom:none;}
.mk{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--ink3);padding:10px 14px;background:var(--paper2);border-right:1px solid var(--paper3);}
.mv{padding:10px 14px;font-size:12px;font-family:'DM Mono',monospace;color:var(--ink);}
.rev-item{display:flex;align-items:flex-start;gap:8px;padding:8px 0;border-bottom:1px solid var(--paper3);}
.rev-item:last-child{border-bottom:none;}
.rev-icon{font-size:14px;min-width:20px;}
.rev-body{flex:1;}
.rev-lbl{font-size:12px;font-weight:500;color:var(--ink);}
.rev-obs{font-size:11px;color:var(--ink3);margin-top:2px;}
.er{display:grid;grid-template-columns:1fr 1fr;}
.ec{padding:12px 16px;border-right:1px solid var(--border);}
.ec:last-child{border-right:none;}
.ek{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:4px;}
.ev{font-size:13px;font-weight:500;}
.generating-placeholder{padding:40px;text-align:center;color:var(--ink3);}
.gen-spin{width:24px;height:24px;border:3px solid var(--paper3);border-top-color:var(--blue2);border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 12px;}
@media(max-width:900px){.gen-layout{grid-template-columns:1fr}.er{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div class="logo"><div class="logo-d">diario</div><div class="logo-e"><em>E</em>NE</div></div>
  <span id="hst">Listo</span>
</header>
<div class="main-tabs">
  <div class="main-tab on" id="mt0" onclick="goMain(0)">📰 Noticias del día</div>
  <div class="main-tab" id="mt1" onclick="goMain(1)">✍️ Redactar notas ENE</div>
</div>
<div class="wrap">

  <!-- PANEL A: PORTALES -->
  <div class="panel on" id="pa">
    <p style="font-size:13px;color:var(--ink2);margin-bottom:16px;">Seleccioná las fuentes, cargá las noticias y elegí las que querés redactar.</p>
    <div class="src-bar">
      <label class="src-chip on" id="sc-prensa"><input type="checkbox" value="prensa" checked onchange="toggleSrc(this,'sc-prensa')">📰 Prensa Río Negro</label>
      <label class="src-chip" id="sc-bariloche"><input type="checkbox" value="bariloche" onchange="toggleSrc(this,'sc-bariloche')">🏔 Bariloche Informa</label>
      <label class="src-chip" id="sc-policia"><input type="checkbox" value="policia" onchange="toggleSrc(this,'sc-policia')">🚔 Policía RN</label>
      <label class="src-chip" id="sc-quorum"><input type="checkbox" value="quorum" onchange="toggleSrc(this,'sc-quorum')">🏛 Quorum Legislativo</label>

      <button class="btn" id="btn-load" onclick="loadNews()">Cargar noticias →</button>
    </div>
    <div id="cards-grid" class="cards-grid"></div>
    <div id="sel-footer" class="sel-footer" style="display:none">
      <span class="sel-info">Seleccionadas: <b id="sel-n">0</b></span>
      <div style="display:flex;gap:8px">
        <button class="btn-sec" onclick="clearSel()">Limpiar</button>
        <button class="btn" id="btn-pass" disabled onclick="passToRedactor()">Redactar notas seleccionadas →</button>
      </div>
    </div>
  </div>

  <!-- MODAL PREVIEW -->
  <div class="modal-overlay" id="modal-overlay" onclick="closeModal(event)">
    <div class="modal-box" id="modal-box">
      <div class="modal-hdr">
        <div class="modal-title" id="modal-title"></div>
        <button class="modal-close" onclick="closeModal()">✕</button>
      </div>
      <div class="modal-body">
        <img id="modal-img" class="modal-img" src="" style="display:none" onerror="this.style.display='none'">
        <div class="modal-meta" id="modal-meta"></div>
        <div class="modal-text" id="modal-text"></div>
      </div>
      <div class="modal-footer">
        <button class="btn-sec" onclick="closeModal()">Cerrar</button>
        <button class="btn" id="modal-select-btn" onclick="modalSelect()">+ Agregar al redactor →</button>
      </div>
    </div>
  </div>

  <!-- PANEL B: REDACTOR -->
  <div class="panel" id="pb">
    <div class="gen-layout">
      <div>
        <div class="sub-tabs">
          <div class="sub-tab on" id="st0" onclick="goSub(0)">📋 Texto</div>
          <div class="sub-tab" id="st1" onclick="goSub(1)">🔗 URL(s)</div>
          <div class="sub-tab" id="st2" onclick="goSub(2)">📌 Portal</div>
        </div>

        <!-- Texto -->
        <div class="sub-panel on" id="sp0">
          <textarea id="texto-input" placeholder="Pegá la gacetilla, comunicado o texto de WhatsApp..."></textarea>
          <button class="btn" onclick="addFromTexto()" style="width:100%;margin-bottom:8px">+ Agregar a la cola</button>
          <div id="cola-preview" class="prev-list" style="display:none"></div>
          <button class="btn-sec" id="btn-clear-cola" onclick="clearCola()" style="width:100%;display:none">Limpiar cola</button>
        </div>

        <!-- URLs múltiples -->
        <div class="sub-panel" id="sp1">
          <textarea id="url-input" placeholder="Pegá una o más URLs (una por línea):&#10;https://prensa.rionegro.gov.ar/articulo/...&#10;https://prensa.rionegro.gov.ar/articulo/..." style="min-height:100px;"></textarea>
          <button class="btn" id="btn-url" onclick="addFromUrls()" style="width:100%">
            <span class="spin" id="spin-url"></span>
            <span id="btn-url-lbl">Agregar URL(s) a la cola →</span>
          </button>
          <div id="url-cola-preview" class="prev-list" style="margin-top:8px;display:none"></div>
        </div>

        <!-- Del portal -->
        <div class="sub-panel" id="sp2">
          <div id="portal-prev" class="prev-list">
            <p style="font-size:12px;color:var(--ink3);">Cargá noticias en el panel anterior y pasalas acá.</p>
          </div>
        </div>

        <div style="margin-top:12px">
          <div class="slbl">Cola de notas (<span id="cola-count">0</span>)</div>
          <div id="main-cola" class="prev-list"></div>
        </div>

        <div class="slbl">Opciones</div>
        <div class="opts">
          <div class="opt"><label>Sección</label>
            <select id="sec-ov">
              <option value="">Detectar automático</option>
              <option>Sociedad</option><option>Política</option><option>Economía</option>
              <option>Policiales / Judiciales</option><option>Turismo</option>
              <option>Cultura / Espectáculos</option><option>Deportes</option>
              <option>Medio Ambiente</option><option>Tecnología</option><option>Salud</option>
            </select>
          </div>
          <div class="opt"><label>Tono</label>
            <select id="tone">
              <option value="informativo">Informativo (ENE default)</option>
              <option value="urgente">Urgente / breaking</option>
              <option value="análisis">Análisis / contexto</option>
              <option value="servicio">Guía práctica</option>
            </select>
          </div>
        </div>
        <div class="chips">
          <label class="chip on" id="ch-rrss"><input type="checkbox" checked onchange="tChip(this,'ch-rrss')">Posts RRSS</label>
          <label class="chip on" id="ch-seo"><input type="checkbox" checked onchange="tChip(this,'ch-seo')">Micro SEO</label>
          <label class="chip on" id="ch-rev"><input type="checkbox" checked onchange="tChip(this,'ch-rev')">Anti-IA</label>
        </div>
        <button class="btn-gen" id="btn-gen" onclick="generateAll()">
          <span class="spin" id="spin"></span>
          <span id="btn-lbl">Generar todas las notas →</span>
        </button>
        <div class="err" id="err"></div>
        <button class="btn-sec" onclick="goMain(0)" style="width:100%;margin-top:8px;text-align:center;">← Volver a noticias</button>
      </div>

      <!-- OUTPUT CON TABS -->
      <div class="out">
        <div class="empty" id="empty">
          <div style="font-size:32px;opacity:.15;margin-bottom:10px">✦</div>
          <p style="font-size:13px;color:var(--ink3)">Cargá una o varias fuentes y<br>hacé clic en <strong>Generar todas las notas</strong></p>
        </div>
        <div id="notes-area" style="display:none">
          <div class="note-tabs-wrap">
            <div class="note-tabs" id="note-tabs"></div>
          </div>
          <div id="note-panels"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- MODAL PREVIEW -->
<div class="modal-overlay" id="modal-overlay" onclick="closeModal(event)">
  <div class="modal-box" id="modal-box">
    <div class="modal-hdr">
      <div class="modal-title" id="modal-title"></div>
      <button class="modal-close" onclick="closeModalDirect()">✕</button>
    </div>
    <img id="modal-img" class="modal-img" src="" alt="" style="display:none" onerror="this.style.display='none'">
    <div class="modal-body">
      <div class="modal-sec" id="modal-sec"></div>
      <div class="modal-text" id="modal-text">Cargando…</div>
    </div>
    <div class="modal-footer">
      <button class="btn-sec" onclick="closeModalDirect()">Cerrar</button>
      <button class="btn" id="modal-add-btn">+ Agregar a la cola →</button>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

// ── ESTADO ──
let portalArticles = [], portalSelected = new Set();
let cola = []; // [{id, title, text, url, photo}]
let noteResults = []; // resultados generados
let busy = false;
let activeNoteTab = 0;

// ── NAV ──
function goMain(n){ $('mt0').classList.toggle('on',n===0); $('mt1').classList.toggle('on',n===1); $('pa').classList.toggle('on',n===0); $('pb').classList.toggle('on',n===1); }
function goSub(n){ [0,1,2].forEach(i=>{ $('st'+i).classList.toggle('on',i===n); $('sp'+i).classList.toggle('on',i===n); }); }
function tChip(inp,id){ $(id).classList.toggle('on',inp.checked); }
function toggleSrc(inp,id){ $(id).classList.toggle('on',inp.checked); }
function st(t){ $('hst').textContent=t; }

// ── PORTAL ──
async function loadNews(){
  const checks=[...$('pa').querySelectorAll('.src-chip input:checked')].map(i=>i.value);
  if(!checks.length){ alert('Seleccioná al menos una fuente.'); return; }
  const btn=$('btn-load'); btn.disabled=true; btn.textContent='Cargando…'; st('Cargando…');
  portalArticles=[]; portalSelected.clear();
  $('cards-grid').innerHTML=Array(9).fill(0).map(()=>`<div class="skl"></div>`).join('');
  for(const src of checks){
    try{ const r=await fetch(`/noticias/${src}`); const d=await r.json(); portalArticles.push(...(d.articles||[])); }catch(e){}
  }
  btn.disabled=false; btn.textContent='Actualizar →';
  st(portalArticles.length+' noticias');
  renderCards();
}
// ── MODAL PREVIEW ──
let modalCurrentIdx = null;
function showPreview(e, idx){
  e.stopPropagation();
  const a = portalArticles[idx];
  modalCurrentIdx = idx;
  $('modal-title').textContent = a.title||'';
  const img = $('modal-img');
  if(a.photo){ img.src=a.photo; img.style.display='block'; } else { img.style.display='none'; }
  $('modal-meta').innerHTML = [
    a.sec&&a.sec!=='—'?`<span class="modal-tag">${esc(a.sec)}</span>`:'',
    a.source?`<span class="modal-tag" style="background:var(--paper);color:var(--ink3)">${esc(a.source)}</span>`:'',
    a.date?`<span class="modal-tag" style="background:var(--paper);color:var(--ink3)">${esc(a.date)}</span>`:'',
  ].filter(Boolean).join('');
  // Show preview text or loading
  const previewEl = $('modal-text');
  if(a.fullText){
    previewEl.textContent = a.fullText;
  } else if(a.preview){
    previewEl.textContent = a.preview + '…';
    // Try to load full text in background
    fetch(`/articulo?url=${encodeURIComponent(a.url)}`)
      .then(r=>r.json())
      .then(d=>{ if(d.text){ a.fullText=d.text; previewEl.textContent=d.text.slice(0,800)+'…'; }})
      .catch(()=>{});
  } else {
    previewEl.textContent = 'Cargando preview…';
    fetch(`/articulo?url=${encodeURIComponent(a.url)}`)
      .then(r=>r.json())
      .then(d=>{ if(d.text){ a.fullText=d.text; previewEl.textContent=d.text.slice(0,800)+'…'; }})
      .catch(()=>{ previewEl.textContent='No se pudo cargar el preview.'; });
  }
  // Update select button state
  const btn=$('modal-select-btn');
  const already = portalSelected.has(idx);
  btn.textContent = already?'✓ Ya seleccionada':'+ Agregar al redactor →';
  btn.disabled = already;
  $('modal-overlay').classList.add('on');
}
function closeModal(e){
  if(e && e.target !== $('modal-overlay')) return;
  $('modal-overlay').classList.remove('on');
  modalCurrentIdx = null;
}
function modalSelect(){
  if(modalCurrentIdx===null) return;
  portalSelected.add(modalCurrentIdx);
  $('sel-n').textContent=portalSelected.size;
  $('btn-pass').disabled=false;
  $('sel-footer').style.display='flex';
  renderCards();
  $('modal-select-btn').textContent='✓ Seleccionada';
  $('modal-select-btn').disabled=true;
}
// Close with Escape
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeModal({target:$('modal-overlay')}); });

function renderCards(){
  const g=$('cards-grid');
  if(!portalArticles.length){ g.innerHTML='<p style="color:var(--ink3);font-size:13px;grid-column:1/-1">Sin noticias. Verificá el backend.</p>'; return; }
  g.innerHTML=portalArticles.map((a,i)=>`
    <div class="card${portalSelected.has(i)?' sel':''}" onclick="toggleCard(${i})">
      <div class="card-chk">✓</div>
      <div class="card-body">
        <div class="card-sec">${esc(a.sec||'')}</div>
        <div class="card-title">${esc((a.title||'').slice(0,85))}${(a.title||'').length>85?'…':''}</div>
        <div class="card-src">${esc(a.source||'')}</div>
      </div>
    </div>`).join('');
  $('sel-footer').style.display='flex';
}
function toggleCard(i){
  portalSelected.has(i)?portalSelected.delete(i):portalSelected.add(i);
  $('sel-n').textContent=portalSelected.size;
  $('btn-pass').disabled=portalSelected.size===0;
  renderCards();
}
function toggleCardFromModal(i){
  portalSelected.has(i)?portalSelected.delete(i):portalSelected.add(i);
  $('sel-n').textContent=portalSelected.size;
  $('btn-pass').disabled=portalSelected.size===0;
  const btn=$('modal-sel-btn');
  if(btn) btn.textContent=portalSelected.has(i)?'Quitar selección':'Seleccionar';
  renderCards();
}
function showPreview(i,e){
  e.stopPropagation();
  const a=portalArticles[i];
  const existing=$('card-modal');
  if(existing) existing.remove();
  const m=document.createElement('div');
  m.id='card-modal';
  m.style.cssText='position:fixed;inset:0;background:rgba(4,8,15,.6);z-index:999;display:flex;align-items:center;justify-content:center;padding:24px;';
  m.innerHTML=`<div style="background:#fff;border-radius:8px;max-width:560px;width:100%;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.2)">
    ${a.photo?`<img src="${esc(a.photo)}" style="width:100%;height:200px;object-fit:cover" onerror="this.style.display='none'">`:''}
    <div style="padding:20px">
      <div style="font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--ink3);margin-bottom:8px">${esc(a.sec||'')} · ${esc(a.source||'')}</div>
      <div style="font-family:'Instrument Serif',serif;font-size:20px;line-height:1.3;color:var(--ink);margin-bottom:10px">${esc(a.title||'')}</div>
      ${a.preview?`<div style="font-size:13px;color:var(--ink3);line-height:1.7;margin-bottom:14px">${esc(a.preview)}</div>`:''}
      <div style="display:flex;gap:8px">
        <button id="modal-sel-btn" onclick="toggleCardFromModal(${i})" style="padding:8px 16px;background:var(--blue2);color:#fff;border:none;border-radius:4px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit">${portalSelected.has(i)?'Quitar selección':'Seleccionar'}</button>
        <button onclick="$('card-modal').remove()" style="padding:8px 16px;background:transparent;border:1px solid var(--border);border-radius:4px;font-size:12px;cursor:pointer;font-family:inherit">Cerrar</button>
        <a href="${esc(a.url)}" target="_blank" style="padding:8px 16px;background:transparent;border:1px solid var(--border);border-radius:4px;font-size:12px;cursor:pointer;font-family:inherit;text-decoration:none;color:var(--ink3)">Ver nota →</a>
      </div>
    </div>
  </div>`;
  m.onclick=(ev)=>{ if(ev.target===m) m.remove(); };
  document.body.appendChild(m);
}

let _modalIdx = -1;
function openPreview(i){
  const a = portalArticles[i];
  _modalIdx = i;
  $('modal-title').textContent = a.title||'';
  $('modal-sec').textContent = (a.source||'') + (a.sec&&a.sec!=='—'?' · '+a.sec:'') + (a.date?' · '+a.date:'');
  const img=$('modal-img');
  if(a.photo){ img.src=a.photo; img.style.display='block'; } else { img.style.display='none'; }
  // Botón agregar
  $('modal-add-btn').onclick=()=>{ addToColaFromModal(i); closeModalDirect(); };
  $('modal-add-btn').textContent = portalSelected.has(i) ? '✓ Ya en cola' : '+ Agregar a la cola →';
  // Texto
  const previewEl = $('modal-text');
  if(a.fullText){
    previewEl.textContent = a.fullText;
  } else if(a.preview){
    previewEl.textContent = a.preview + '…

Cargando nota completa…';
    fetch(`/articulo?url=${encodeURIComponent(a.url)}`)
      .then(r=>r.json())
      .then(d=>{ if(d.text){ a.fullText=d.text; previewEl.textContent=d.text.slice(0,1000)+'…'; }})
      .catch(()=>{ previewEl.textContent=a.preview+'…'; });
  } else {
    previewEl.textContent = 'Cargando…';
    fetch(`/articulo?url=${encodeURIComponent(a.url)}`)
      .then(r=>r.json())
      .then(d=>{ if(d.text){ a.fullText=d.text; previewEl.textContent=d.text.slice(0,1000)+'…'; }})
      .catch(()=>{ previewEl.textContent='No se pudo cargar la nota.'; });
  }
  $('modal-overlay').classList.add('on');
  document.body.style.overflow='hidden';
}
function addToColaFromModal(i){
  const a=portalArticles[i];
  if(!cola.find(c=>c.url===a.url)){
    cola.push({id:Date.now()+Math.random(),title:a.title,text:a.fullText||'',url:a.url,photo:a.photo||null});
    renderCola();
  }
  portalSelected.add(i);
  $('sel-n').textContent=portalSelected.size;
  $('btn-pass').disabled=false;
}
function closeModal(e){ if(e.target===$('modal-overlay')) closeModalDirect(); }
function closeModalDirect(){ $('modal-overlay').classList.remove('on'); document.body.style.overflow=''; }
function clearSel(){ portalSelected.clear(); $('sel-n').textContent=0; $('btn-pass').disabled=true; renderCards(); }
function passToRedactor(){
  const arts=[...portalSelected].map(i=>portalArticles[i]);
  arts.forEach(a=>{ if(!cola.find(c=>c.url===a.url)) cola.push({id:Date.now()+Math.random(),title:a.title,text:'',url:a.url,photo:a.photo||null}); });
  $('portal-prev').innerHTML=arts.map(a=>`<div class="prev-item"><small>${esc(a.source)}</small>${esc(a.title.slice(0,80))}…</div>`).join('');
  renderCola(); goMain(1); goSub(2);
}

// ── COLA ──
function addFromTexto(){
  const t=$('texto-input').value.trim();
  if(!t||t.length<20){ alert('Pegá un texto más largo.'); return; }
  cola.push({id:Date.now(),title:t.slice(0,60)+'…',text:t,url:'',photo:null});
  $('texto-input').value='';
  renderCola();
}
async function addFromUrls(){
  const raw=$('url-input').value.trim();
  if(!raw){ alert('Pegá al menos una URL.'); return; }
  const urls=raw.split('\n').map(u=>u.trim()).filter(u=>u.startsWith('http'));
  if(!urls.length){ alert('No encontré URLs válidas.'); return; }
  const btn=$('btn-url'); const lbl=$('btn-url-lbl'); const sp=$('spin-url');
  btn.disabled=true; sp.style.display='inline-block'; lbl.textContent='Obteniendo…';
  for(const url of urls){
    if(cola.find(c=>c.url===url)) continue;
    try{
      const r=await fetch(`/articulo?url=${encodeURIComponent(url)}`);
      const d=await r.json();
      cola.push({id:Date.now()+Math.random(),title:d.title||url,text:d.text||'',url,photo:d.photo||null});
    }catch(e){ cola.push({id:Date.now()+Math.random(),title:url,text:'',url,photo:null}); }
  }
  $('url-input').value='';
  btn.disabled=false; sp.style.display='none'; lbl.textContent='Agregar URL(s) a la cola →';
  renderCola();
}
function removeFromCola(id){ cola=cola.filter(c=>c.id!==id); renderCola(); }
function clearCola(){ cola=[]; renderCola(); }
function renderCola(){
  $('cola-count').textContent=cola.length;
  const el=$('main-cola');
  if(!cola.length){ el.innerHTML='<p style="font-size:12px;color:var(--ink3);">Cola vacía.</p>'; $('btn-clear-cola').style.display='none'; $('cola-preview').style.display='none'; return; }
  el.innerHTML=cola.map(c=>`
    <div class="prev-item" style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
      <div style="flex:1;font-size:11px">${esc(c.title.slice(0,70))}${c.title.length>70?'…':''}</div>
      <button onclick="removeFromCola(${c.id})" style="font-size:10px;background:transparent;border:none;color:var(--ink3);cursor:pointer;flex-shrink:0">✕</button>
    </div>`).join('');
  $('btn-clear-cola').style.display='block';
}

// ── GENERAR TODAS ──
async function generateAll(){
  if(busy){ return; }
  if(!cola.length){ alert('Agregá al menos una fuente a la cola.'); return; }
  busy=true; setLoad(true); hideErr();
  $('empty').style.display='none';
  $('notes-area').style.display='block';
  noteResults=[];

  // Crear tabs placeholder
  const tabsEl=$('note-tabs');
  const panelsEl=$('note-panels');
  tabsEl.innerHTML='';
  panelsEl.innerHTML='';

  const seccion=$('sec-ov').value;
  const tono=$('tone').value;
  const extras={ rrss:$('ch-rrss').querySelector('input').checked, micro_seo:$('ch-seo').querySelector('input').checked };

  for(let i=0;i<cola.length;i++){
    const item=cola[i];
    // Tab
    const tab=document.createElement('div');
    tab.className='note-tab'+(i===0?' on':'');
    tab.id=`ntab-${i}`;
    tab.innerHTML=`<span class="note-tab-txt" onclick="switchNoteTab(${i})">${esc(item.title.slice(0,22))}… <span class="note-tab-status">⏳</span></span><span class="note-tab-close" onclick="closeNoteTab(event,${i})">✕</span>`;
    tabsEl.appendChild(tab);
    // Panel placeholder
    const panel=document.createElement('div');
    panel.className='note-panel'+(i===0?' on':'');
    panel.id=`npanel-${i}`;
    panel.innerHTML=`<div class="generating-placeholder"><div class="gen-spin"></div><p>Generando nota ${i+1}...</p></div>`;
    panelsEl.appendChild(panel);
  }

  // Generar en paralelo
  const promises=cola.map(async (item,i)=>{
    try{
      // Enriquecer con texto si viene de URL
      let text=item.text;
      let photo=item.photo;
      if(!text && item.url){
        try{
          const r=await fetch(`/articulo?url=${encodeURIComponent(item.url)}`);
          const d=await r.json();
          text=d.text||'';
          photo=photo||d.photo||null;
        }catch(e){}
      }
      // Buscar fotos relacionadas
      const kw=item.title.split(' ').slice(0,4).join(' ');
      const photosResp=await fetch(`/fotos?q=${encodeURIComponent(kw)}`);
      const photosData=await photosResp.json();
      const extraPhotos=photosData.photos||[];

      const r=await fetch('/generar',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({articles:[{url:item.url,title:item.title,text}],seccion,tono,extras})
      });
      if(!r.ok) throw new Error(`Error ${r.status}`);
      const d=await r.json();
      d._photo=photo;
      d._extraPhotos=extraPhotos;
      d._title=item.title;
      renderNotePanel(i, d);
      $(`ntab-${i}`).querySelector('.note-tab-status').textContent='✓';
      $(`ntab-${i}`).querySelector('.note-tab-status').style.color='var(--ok)';
      noteResults[i]=d;
    }catch(e){
      $(`npanel-${i}`).innerHTML=`<div class="generating-placeholder"><p style="color:#c83030">⚠ Error: ${esc(e.message)}</p></div>`;
      $(`ntab-${i}`).querySelector('.note-tab-status').textContent='✗';
      $(`ntab-${i}`).querySelector('.note-tab-status').style.color='#c83030';
    }
  });

  await Promise.all(promises);
  busy=false; setLoad(false);
  st('Listo — '+cola.length+' nota(s) generada(s)');
  // Limpiar cola para próxima sesión
  cola=[];
  renderCola();
}

function switchNoteTab(n){
  document.querySelectorAll('.note-tab').forEach((t,i)=>t.classList.toggle('on',i===n));
  document.querySelectorAll('.note-panel').forEach((p,i)=>p.classList.toggle('on',i===n));
  activeNoteTab=n;
}

function stripH(s){ return (s||'').replace(/<[^>]+>/g,'').replace(/&[a-z]+;/g,' ').trim(); }

function renderNotePanel(idx, d){
  const panel=$(`npanel-${idx}`);
  const hasRrss=$('ch-rrss').querySelector('input').checked;
  const hasSeo=$('ch-seo').querySelector('input').checked;
  const hasRev=$('ch-rev').querySelector('input').checked;
  const ri=d.titulo_recomendado_index??0;

  // Fotos
  let photosHtml='';
  const allPhotos=[];
  if(d._photo){
    // Foto original
    allPhotos.push({url:d._photo, label:'Original', main:true, isOriginal:true});
    // Versión 1024x768 via proxy de resize gratuito
    const resized = `https://images.weserv.nl/?url=${encodeURIComponent(d._photo)}&w=1024&h=768&fit=cover&output=jpg`;
    allPhotos.push({url:resized, label:'1024×768 recortada', main:false, isResized:true});
  }
  (d._extraPhotos||[]).forEach((p,i)=>allPhotos.push({url:p.url,label:p.photographer||'Pexels',main:false}));
  if(allPhotos.length){
    photosHtml=`<div class="photos-row" style="flex-direction:column;gap:8px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
        <span class="photos-lbl" style="margin:0">📷 Fotos disponibles</span>
        <span style="font-size:10px;color:var(--ink3)">Hacé clic para seleccionar · La seleccionada se usa como destacada</span>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        ${allPhotos.map((p,i)=>`
          <div class="photo-card${p.main?' main-photo':''}${p.isResized?' resized-photo':''}" onclick="selectPhoto(${idx},${i},this)" title="${esc(p.label)}" data-url="${esc(p.url)}">
            <img src="${esc(p.url)}" onerror="this.parentElement.style.display='none'" loading="lazy">
            <div class="photo-label" style="${p.isOriginal?'background:rgba(10,122,184,.8)':p.isResized?'background:rgba(42,122,75,.8)':''}">
              ${p.isOriginal?'⭐ ':p.isResized?'✂ ':''}${esc(p.label.slice(0,22))}
            </div>
          </div>`).join('')}
      </div>
      <div id="photo-selected-${idx}" style="display:none;font-size:11px;color:var(--ok);padding:4px 0">✓ Foto seleccionada — copiá la URL para usarla en el CMS <button onclick="copyPhotoUrl(${idx})" style="font-size:10px;padding:2px 8px;border:1px solid var(--border);border-radius:3px;background:#fff;cursor:pointer;margin-left:6px">Copiar URL</button></div>
    </div>`;
  }

  // Interlinking
  const ilHtml=(d.interlinking||[]).length?`
    <div class="sec">
      <div class="sec-hd"><div class="sec-row"><span class="bdg b2">IL</span><span class="sec-nm">Interlinking estratégico</span></div><button class="cp" onclick="doCopyEl('il-${idx}',this)">⎘ Copiar</button></div>
      <div style="padding:12px 16px" id="il-${idx}">
        ${(d.interlinking||[]).map(l=>`<div class="il-item"><div class="il-frase">"${esc(l.frase)}"</div><div class="il-dest">→ ${esc(l.destino)}</div><span class="il-jer">${esc(l.jerarquia||'')}</span></div>`).join('')}
      </div>
    </div>`:'';

  // Revisión
  const revItems=[
    {key:'sin_estructura_identica',label:'Sin estructura idéntica entre párrafos'},
    {key:'sin_expresiones_genericas',label:'Sin expresiones genéricas'},
    {key:'variacion_ritmo',label:'Variación de ritmo y longitud'},
    {key:'dato_local_especifico',label:'Dato local específico presente'},
    {key:'lectura_humana',label:'Lectura humana con criterio editorial'},
  ];
  const revHtml=hasRev&&d.revision?`
    <div class="sec">
      <div class="sec-hd"><div class="sec-row"><span class="bdg b5">F5</span><span class="sec-nm">Revisión anti-IA</span></div></div>
      <div style="padding:12px 16px">
        ${revItems.map(it=>`<div class="rev-item"><span class="rev-icon">${d.revision[it.key]?'✅':'❌'}</span><div class="rev-body"><div class="rev-lbl">${it.label}</div>${!d.revision[it.key]&&d.revision.observaciones?`<div class="rev-obs">${esc(d.revision.observaciones)}</div>`:''}</div></div>`).join('')}
      </div>
    </div>`:'';

  panel.innerHTML=`
    ${photosHtml}
    <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b1">F1</span><span class="sec-nm">Clasificación · Keywords · Etiquetas</span></div><button class="cp" onclick="doCopyEl('kw-${idx}',this)">⎘ Copiar</button></div>
    <div class="kw-bl" id="kw-${idx}">
      <div class="kwr"><div class="kwl">Sección</div><div class="kwcs"><span class="kwc pr">${esc(d.seccion)}</span></div></div>
      <div class="kwr"><div class="kwl">Keyword principal</div><div class="kwcs"><span class="kwc pr">${esc(d.kw_principal||'')}</span></div></div>
      <div class="kwr"><div class="kwl">Secundarias</div><div class="kwcs">${(d.kw_secundarias||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>
      ${(d.kw_longtail||[]).length?`<div class="kwr"><div class="kwl">Long tail</div><div class="kwcs">${d.kw_longtail.map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>`:''}
      <div class="kwr"><div class="kwl">Etiquetas</div><div class="kwcs">${(d.etiquetas||[]).map(k=>`<span class="kwc">${esc(k)}</span>`).join('')}</div></div>
      ${d.etiqueta_sugerida?`<div class="kwr"><div class="kwl" style="color:#b8962e">Sugerida</div><div class="kwcs"><span class="kwc" style="border-color:#b8962e;color:#b8962e">${esc(d.etiqueta_sugerida)}</span></div></div>`:''}
    </div></div>
    <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b2">F2</span><span class="sec-nm">Volanta · Título · Copete · Desarrollo</span></div><button class="cp" onclick="doCopyEl('nota-${idx}',this)">⎘ Copiar</button></div>
    <div class="sec-body" id="nota-${idx}">${[`VOLANTA\n${d.volanta||''}`,`\nTÍTULO\n${d.titulo||''}`,`\nCOPETE\n${d.copete||''}`,`\nDESARROLLO\n${stripH(d.desarrollo)}`,d.bloque_guia?`\nBLOQUE GUÍA\n${stripH(d.bloque_guia)}`:null].filter(Boolean).join('')}</div></div>
    ${ilHtml}
    ${hasSeo&&d.micro_seo?`<div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg bx">SEO</span><span class="sec-nm">Micro-bloque SEO / Discover</span></div><button class="cp" onclick="doCopyEl('seo-${idx}',this)">⎘ Copiar</button></div><div class="sec-body" id="seo-${idx}">${esc(d.micro_seo)}</div></div>`:''}
    ${hasRrss&&d.rrss&&(d.rrss.instagram||d.rrss.twitter)?`<div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg bx">RRSS</span><span class="sec-nm">Posts redes sociales</span></div><button class="cp" onclick="doCopyEl('rrss-${idx}',this)">⎘ Copiar</button></div><div class="sec-body" id="rrss-${idx}">📸 INSTAGRAM\n${esc(d.rrss.instagram||'')}\n\n𝕏 X\n${esc(d.rrss.twitter||'')}\n\n📘 FACEBOOK\n${esc(d.rrss.facebook||'')}</div></div>`:''}
    <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b3">F3</span><span class="sec-nm">7 títulos estratégicos</span></div><button class="cp" onclick="doCopyEl('tit-${idx}',this)">⎘ Copiar</button></div>
    <div class="tl" id="tit-${idx}">
      ${(d.titulos||[]).map((t,i)=>`<div class="ti${i===ri?' rec':''}"><span class="tt">${esc(t.tipo)}</span><span class="tx">${esc(t.texto)}</span>${i===ri?'<span class="rtag">✓ REC</span>':''}</div>`).join('')}
      ${d.titulo_recomendado_razon?`<div style="padding:8px 0;font-size:11px;color:var(--ink3);border-top:1px solid var(--paper3);margin-top:3px"><strong style="color:var(--blue2)">¿Por qué?</strong> ${esc(d.titulo_recomendado_razon)}</div>`:''}
    </div></div>
    <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b4">F4</span><span class="sec-nm">Metadatos SEO</span></div><button class="cp" onclick="doCopyEl('meta-${idx}',this)">⎘ Copiar</button></div>
    <div id="meta-${idx}">
      <div class="mr"><div class="mk">Meta title</div><div class="mv">${esc(d.meta_title||'')} <span style="color:#aaa;font-size:10px">(${(d.meta_title||'').length} car.)</span></div></div>
      <div class="mr"><div class="mk">Description</div><div class="mv">${esc(d.meta_description||'')} <span style="color:#aaa;font-size:10px">(${(d.meta_description||'').length} car.)</span></div></div>
      <div class="mr"><div class="mk">Slug</div><div class="mv">${esc(d.slug||'')}</div></div>
    </div></div>
    ${revHtml}
    <div class="sec"><div class="sec-hd"><div class="sec-row"><span class="bdg b1">F6</span><span class="sec-nm">Estrategia editorial</span></div></div>
    <div class="er"><div class="ec"><div class="ek">Portada</div><div class="ev">${esc(d.portada||'—')}</div></div><div class="ec"><div class="ek">Horario</div><div class="ev">${esc(d.horario||'—')}</div></div></div></div>
  `;
}

function selectPhoto(noteIdx, photoIdx, el){
  const panel=$(`npanel-${noteIdx}`);
  panel.querySelectorAll('.photo-card').forEach(c=>c.classList.remove('selected'));
  el.classList.add('selected');
  // Store selected URL
  panel._selectedPhotoUrl = el.getAttribute('data-url');
  const info=$(`photo-selected-${noteIdx}`);
  if(info) info.style.display='block';
}
function copyPhotoUrl(noteIdx){
  const panel=$(`npanel-${noteIdx}`);
  const url=panel._selectedPhotoUrl||'';
  navigator.clipboard.writeText(url).catch(()=>{});
  // Visual feedback
  const btn=document.querySelector(`#npanel-${noteIdx} button[onclick="copyPhotoUrl(${noteIdx})"]`);
  if(btn){ btn.textContent='✓ Copiada'; setTimeout(()=>btn.textContent='Copiar URL',2000); }
}

function closeNoteTab(e, idx){
  e.stopPropagation();
  const tabs=document.querySelectorAll('.note-tab');
  const panels=document.querySelectorAll('.note-panel');
  tabs[idx].remove();
  panels[idx].remove();
  // Activate first remaining tab
  const remaining=document.querySelectorAll('.note-tab');
  const remainingPanels=document.querySelectorAll('.note-panel');
  if(remaining.length>0){ remaining[0].classList.add('on'); remainingPanels[0].classList.add('on'); }
  else{ $('notes-area').style.display='none'; $('empty').style.display='block'; }
}
async function doCopyEl(id,btn){
  try{ await navigator.clipboard.writeText($(id)?.innerText||''); }catch(e){}
  btn.textContent='✓'; btn.classList.add('ok');
  setTimeout(()=>{ btn.textContent='⎘ Copiar'; btn.classList.remove('ok'); },2000);
}
function setLoad(v){ const b=$('btn-gen'); b.disabled=v; b.classList.toggle('loading',v); $('btn-lbl').textContent=v?'Generando…':'Generar todas las notas →'; $('spin').style.display=v?'inline-block':'none'; }
function showErr(m){ const e=$('err'); e.textContent='⚠ '+m; e.classList.add('on'); }
function hideErr(){ $('err').classList.remove('on'); }
</script>
</body>
</html>"""

# ── MODELOS ──
class Article(BaseModel):
    url: str = ""
    title: str = ""
    text: str = ""

class GenerateRequest(BaseModel):
    articles: list[Article]
    seccion: str = ""
    tono: str = "informativo"
    extras: dict = {}

# ── SCRAPER ──
SITE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

# URLs a ignorar en el scraping
IGNORE_PATTERNS = [
    "wordpress.org","elementor.com","wp-login","wp-admin","wp-content/themes",
    "wp-content/plugins","#","javascript:","mailto:","tel:","feed/",
    "page/","category/","tag/","author/","wp-json","xmlrpc",
    "?s=","?p=","/servicios","/inicio","/participacion",
    "google.com","facebook.com","twitter.com","instagram.com","youtube.com",
    "wp-sitemap","privacy-policy","aviso-legal","contacto","sobre-nosotros",
]

def is_valid_article_url(url: str, base: str, min_dashes: int = 2) -> bool:
    if not url.startswith("http"): return False
    if not url.startswith(base): return False
    if any(p in url.lower() for p in IGNORE_PATTERNS): return False
    slug = url.replace(base,"").strip("/").split("?")[0]
    if len(slug) < 10: return False
    if slug.count("-") < min_dashes: return False
    return True

def extract_wp_articles(soup, base: str, source_name: str, max_items: int = 20):
    """Scraper genérico para sitios WordPress."""
    articles = []
    seen = set()
    # Buscar en article tags primero
    for article in soup.find_all(["article"], limit=40):
        a_tag = article.find("a", href=True)
        if not a_tag: continue
        href = a_tag.get("href","")
        if not href.startswith("http"): href = base + href
        if not is_valid_article_url(href, base): continue
        if href in seen: continue
        seen.add(href)
        # Título
        heading = article.find(["h1","h2","h3","h4"])
        title = heading.get_text(strip=True) if heading else a_tag.get_text(strip=True)
        title = " ".join(title.split())
        if not title or len(title) < 20 or len(title) > 250: continue
        # Foto
        img = article.find("img")
        photo = None
        if img:
            for attr in ["src","data-src","data-lazy-src","data-original"]:
                raw = img.get(attr,"")
                if raw and not raw.startswith("data:") and len(raw) > 10:
                    photo = raw if raw.startswith("http") else base + raw
                    break
        # Categoría
        cat_el = article.find(class_=lambda c: c and any(x in " ".join(c or []) for x in ["cat","category","tag","section","etiqueta"]))
        sec = cat_el.get_text(strip=True).strip() if cat_el else "General"
        if len(sec) > 30: sec = "General"
        # Preview
        p_el = article.find("p")
        preview = " ".join(p_el.get_text(strip=True).split())[:160] if p_el else ""
        articles.append({"url":href,"title":title,"sec":sec,"source":source_name,"photo":photo,"preview":preview})
        if len(articles) >= max_items: break
    return articles

async def scrape_source(key: str):
    src = SOURCES[key]
    articles = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, verify=False) as client:
            r = await client.get(src["url"], headers=SITE_HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            src_type = src.get("type","")

            # ── BARILOCHE INFORMA ──
            if src_type == "bariloche":
                candidates = extract_wp_articles(soup, src["base"], src["name"])
                # Fallback: buscar todos los links válidos
                if not candidates:
                    seen = set()
                    for a in soup.find_all("a", href=True):
                        href = a.get("href","")
                        if not href.startswith("http"): href = src["base"] + href
                        if not is_valid_article_url(href, src["base"]): continue
                        if href in seen: continue
                        seen.add(href)
                        heading = a.find(["h1","h2","h3","h4"])
                        title = (heading or a).get_text(strip=True)
                        title = " ".join(title.split())
                        if not title or len(title) < 20 or len(title) > 250: continue
                        candidates.append({"url":href,"title":title,"sec":"Bariloche","source":src["name"],"photo":None,"preview":""})
                        if len(candidates) >= 20: break
                articles = candidates[:20]

            # ── WORDPRESS GENÉRICO (Quorum, Policía) ──
            elif src_type == "wordpress":
                articles = extract_wp_articles(soup, src["base"], src["name"])
                # Si no encontró nada con article tags, buscar h2+a
                if not articles:
                    seen = set()
                    for h in soup.find_all(["h2","h3"], limit=40):
                        a_tag = h.find("a", href=True)
                        if not a_tag: continue
                        href = a_tag.get("href","")
                        if not href.startswith("http"): href = src["base"] + href
                        if not is_valid_article_url(href, src["base"], min_dashes=1): continue
                        if href in seen: continue
                        seen.add(href)
                        title = " ".join(h.get_text(strip=True).split())
                        if not title or len(title) < 15 or len(title) > 250: continue
                        # Foto en el parent
                        parent = h.find_parent(["div","li","section"])
                        img = parent.find("img") if parent else None
                        photo = None
                        if img:
                            for attr in ["src","data-src","data-lazy-src"]:
                                raw = img.get(attr,"")
                                if raw and not raw.startswith("data:") and len(raw) > 10:
                                    photo = raw if raw.startswith("http") else src["base"] + raw
                                    break
                        p_el = parent.find("p") if parent else None
                        preview = " ".join(p_el.get_text(strip=True).split())[:160] if p_el else ""
                        articles.append({"url":href,"title":title,"sec":"Legislativa","source":src["name"],"photo":photo,"preview":preview})
                        if len(articles) >= 20: break

            # ── PRENSA RÍO NEGRO ──
            else:
                seen = set()
                pat = src["pattern"]
                links = soup.find_all("a", href=lambda h: h and pat in h)
                for a in links:
                    href = a.get("href","")
                    url = href if href.startswith("http") else src["base"] + href
                    if url in seen or len(url) < 20: continue
                    seen.add(url)
                    heading = a.find(["h2","h3","h4","h5"])
                    title = (heading or a).get_text(strip=True).replace("\n"," ").strip()
                    if not title or len(title) < 20 or len(title) > 200: continue
                    parent = a.find_parent(["article","div","li"])
                    sec = "—"
                    if parent:
                        h6 = parent.find("h6")
                        if h6: sec = re.sub(r'\d+\s+de\s+\w+\s+de\s+\d{4}','',h6.get_text(strip=True)).strip()
                    # Foto
                    img_el = parent.find("img") if parent else None
                    photo = None
                    if img_el:
                        raw_img = img_el.get("src") or img_el.get("data-src") or ""
                        if "/_next/image" in raw_img:
                            import urllib.parse as _up
                            _parsed = _up.urlparse(raw_img)
                            _params = _up.parse_qs(_parsed.query)
                            photo = _up.unquote(_params.get("url", [""])[0])
                        elif raw_img.startswith("http") and "data:image" not in raw_img:
                            photo = raw_img
                    p_el = parent.find("p") if parent else None
                    preview = p_el.get_text(strip=True)[:150] if p_el else ""
                    articles.append({"url":url,"title":title,"sec":sec,"source":src["name"],"photo":photo,"preview":preview})
                    if len(articles) >= 20: break

    except Exception as e:
        print(f"scrape {key}: {e}")
    return articles

# ── ENDPOINTS ──
@app.get("/", response_class=HTMLResponse)
def root(): return HTML

@app.get("/noticias/{source}")
async def get_noticias(source: str):
    if source not in SOURCES: return {"articles":[],"error":"Fuente no encontrada"}
    articles = await scrape_source(source)
    return {"articles": articles, "total": len(articles)}

@app.get("/articulo")
async def get_articulo(url: str):
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, verify=False) as client:
            r = await client.get(url, headers=SITE_HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            h1 = soup.find("h1") or soup.find("h2")
            title = h1.get_text(strip=True) if h1 else ""
            # Foto principal
            photo = None
            og = soup.find("meta", property="og:image")
            if og: photo = og.get("content","")
            if not photo:
                img = soup.find("img", class_=lambda c: c and "primary" in " ".join(c or []))
                if img: photo = img.get("src","")
            for tag in soup(["nav","header","footer","script","style","aside"]): tag.decompose()
            body = soup.find("article") or soup.find(class_=lambda c: c and "content" in " ".join(c or [])) or soup.body
            text = body.get_text(separator=" ", strip=True) if body else ""
            return {"title":title,"text":" ".join(text.split())[:3000],"photo":photo}
    except Exception as e:
        return {"title":"","text":f"(error: {e})","photo":None}

@app.get("/fotos")
async def get_fotos(q: str = Query("")):
    photos = []
    if PEXELS_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": PEXELS_API_KEY},
                    params={"query": q+" Patagonia Argentina", "per_page": 5, "orientation": "landscape"}
                )
                if r.status_code == 200:
                    data = r.json()
                    photos = [{"url":p["src"]["medium"],"photographer":p["photographer"]} for p in data.get("photos",[])]
        except Exception as e:
            print(f"pexels error: {e}")
    else:
        # Unsplash sin key (uso limitado) - 3 variantes
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                variants = [q+" patagonia", q+" argentina", q+" bariloche"]
                for v in variants:
                    terms = v.replace(" ","+")
                    try:
                        r = await client.get(f"https://source.unsplash.com/featured/800x500/?{terms}", follow_redirects=True)
                        if r.status_code == 200 and "image" in r.headers.get("content-type",""):
                            url = str(r.url)
                            if not any(p["url"]==url for p in photos):
                                photos.append({"url":url,"photographer":"Unsplash"})
                    except Exception:
                        pass
        except Exception:
            pass
    return {"photos": photos}

@app.post("/generar")
async def generar(req: GenerateRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY no configurada en Render")
    parts = []
    for a in req.articles:
        parts.append(f"TÍTULO: {a.title}\nURL: {a.url}\n\n{a.text or '(sin texto)'}")
    user_msg = f"Procesá esta fuente y generá la nota ENE completa con TODAS las fases:\n\n{'---'.join(parts)}"
    if req.seccion: user_msg += f"\n\nSECCIÓN FORZADA: {req.seccion}"
    if req.tono != "informativo": user_msg += f"\n\nTONO: {req.tono}"
    if not req.extras.get("rrss"): user_msg += "\n\nDejar rrss vacío."
    if not req.extras.get("micro_seo"): user_msg += "\n\nDejar micro_seo vacío."
    user_msg += "\n\nIMPORTANTE: El desarrollo DEBE tener MÍNIMO 3 subtítulos con formato <h3>Subtítulo</h3> distribuidos cada 4-5 párrafos. El interlinking DEBE tener MÍNIMO 3 ítems (máximo 4) con frase, destino y jerarquía. Sin estos elementos el output es inválido."

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ]
            }
        )
    if resp.status_code != 200:
        raise HTTPException(500, f"Error OpenAI: {resp.text[:500]}")
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    try:
        return json.loads(raw)
    except Exception:
        raise HTTPException(500, "No se pudo parsear la respuesta de GPT")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
