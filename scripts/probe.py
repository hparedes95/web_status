#!/usr/bin/env python3
"""Sonda de fuentes: dice qué devuelve de verdad cada URL candidata.

Sirve para averiguar la URL buena de un proveedor sin ir a ciegas. Se ejecuta
desde el workflow «Comprobar fuentes», porque el runner de GitHub sí tiene
salida a internet.

    python scripts/probe.py URL [URL...]
"""

import json
import re
import sys
import urllib.error
import urllib.request

UA = "web-status-probe/1.0 (+https://github.com/hparedes95/web_status)"

# Muchas webs comerciales devuelven 404 o cortan el TLS a cualquier cliente que no
# parezca un navegador. Con --navegador se repite la petición imitando uno, para
# distinguir «esta URL no existe» de «esta URL me está bloqueando a mí».
UA_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
CABECERAS_NAVEGADOR = {
    "User-Agent": UA_NAVEGADOR,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept-Encoding": "identity",
}


def sondear(url: str) -> None:
    print(f"\n── {url}")
    cabeceras = (CABECERAS_NAVEGADOR if "--navegador" in sys.argv else
                 {"User-Agent": UA, "Accept": "application/json, application/rss+xml, */*"})
    peticion = urllib.request.Request(url, headers=cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=20) as r:
            crudo = r.read()
            tipo = r.headers.get("Content-Type", "?")
            final = r.geturl()
    except urllib.error.HTTPError as e:
        print(f"   HTTP {e.code} {e.reason}")
        return
    except Exception as e:  # noqa: BLE001
        print(f"   sin respuesta: {e}")
        return

    print(f"   HTTP 200 · {tipo} · {len(crudo)} bytes")
    if final != url:
        print(f"   redirige a: {final}")
    print(f"   primeros bytes: {crudo[:16]!r}")

    for nombre, codificacion in (("utf-8", "utf-8"), ("utf-16", "utf-16")):
        try:
            texto = crudo.decode(codificacion)
        except UnicodeDecodeError:
            continue
        print(f"   como {nombre}: {texto[:220].strip()!r}")
        break

    try:
        import feedparser

        feed = feedparser.parse(crudo)
        print(f"   feedparser: {len(feed.entries)} entradas · bozo={getattr(feed, 'bozo', '?')}")
        for entrada in feed.entries[:3]:
            print(f"      · {entrada.get('title', '')[:90]}")
    except ImportError:
        pass

    # Si es JSON, lo útil es la forma: qué campos trae y qué valores toman.
    try:
        datos = json.loads(crudo.decode("utf-8", errors="replace").lstrip("\ufeff"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        datos = None
    if datos is not None:
        if isinstance(datos, list):
            print(f"   JSON: lista de {len(datos)} elementos")
            if datos and isinstance(datos[0], dict):
                print(f"   campos: {sorted(datos[0].keys())}")
                print(f"   primer elemento: {json.dumps(datos[0], ensure_ascii=False)[:600]}")
        elif isinstance(datos, dict):
            print(f"   JSON: objeto con campos {sorted(datos.keys())[:20]}")
            # Casi todas las APIs meten lo interesante en "data": sin ver dentro,
            # saber que el campo existe no sirve de nada.
            dentro = datos.get("data")
            if isinstance(dentro, list):
                print(f"   data: lista de {len(dentro)} elementos")
                for elemento in dentro[:3]:
                    print(f"      {json.dumps(elemento, ensure_ascii=False)[:300]}")
            elif isinstance(dentro, dict):
                print(f"   data: objeto con campos {sorted(dentro.keys())[:15]}")
                print(f"      {json.dumps(dentro, ensure_ascii=False)[:300]}")
            # Los títulos revelan qué series trae dentro, que es lo que hay que
            # filtrar. Sin esto hay que adivinar cómo se llaman.
            texto = crudo.decode("utf-8", errors="replace")
            titulos = list(dict.fromkeys(re.findall(r'"title"\s*:\s*"([^"]{0,70})"', texto)))
            if titulos:
                print(f"   títulos que contiene: {titulos[:12]}")
            fechas = re.findall(r'"datetime"\s*:\s*"([^"]{0,40})"', texto)
            if fechas:
                print(f"   primera y última fecha: {fechas[0]} … {fechas[-1]} ({len(fechas)} puntos)")

    # Si es HTML, casi siempre es una aplicación de una sola página: lo que
    # interesa entonces no es el HTML sino de dónde saca sus datos.
    if b"<!doctype html" in crudo[:200].lower() or b"<html" in crudo[:200].lower():
        texto = crudo.decode("utf-8", errors="replace")
        guiones = set(re.findall(r'src="([^"]+\.js[^"]*)"', texto))
        if guiones:
            print("   scripts que carga:")
            for g in sorted(guiones)[:8]:
                print(f"      {g}")
        rutas = set(re.findall(r'["\'](/(?:api|data|status)/[A-Za-z0-9_\-./]*)["\']', texto))
        if rutas:
            print(f"   rutas candidatas en el HTML: {sorted(rutas)[:12]}")


if __name__ == "__main__":
    if "--navegador" in sys.argv:
        print("(imitando un navegador)")
    for url in sys.argv[1:]:
        if url.startswith("--"):
            continue
        sondear(url)
