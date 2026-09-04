#!/usr/bin/env python3
"""Sonda de fuentes: dice qué devuelve de verdad cada URL candidata.

Sirve para averiguar la URL buena de un proveedor sin ir a ciegas. Se ejecuta
desde el workflow «Comprobar fuentes», porque el runner de GitHub sí tiene
salida a internet.

    python scripts/probe.py URL [URL...]
"""

import re
import sys
import urllib.error
import urllib.request

UA = "web-status-probe/1.0 (+https://github.com/hparedes95/web_status)"


def sondear(url: str) -> None:
    print(f"\n── {url}")
    peticion = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json, application/rss+xml, */*"}
    )
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
    for url in sys.argv[1:]:
        sondear(url)
