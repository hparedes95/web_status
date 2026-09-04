#!/usr/bin/env python3
"""Agente de latido: corre DENTRO de nuestra red y le cuenta al panel lo que
ningún feed puede saber — si hay luz, si la línea está viva, si el SAI tira de
batería, si el respaldo móvil responde.

No abre ningún puerto ni necesita que nadie entre desde fuera: solo sale hacia
la API de GitHub. Actualiza el cuerpo de una issue, que el panel lee.

**El silencio también es información.** Si este agente deja de reportar, o se ha
ido la luz, o se ha caído la línea, o la máquina está apagada. El panel lo marca
como caída de la sede sin necesidad de que nadie le avise.

Instalación y configuración: docs/06-agente.md

    python3 agente/latido.py            # un envío
    python3 agente/latido.py --probar   # muestra lo que enviaría, sin enviarlo
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO = os.environ.get("LATIDO_REPO", "hparedes95/web_status")
TOKEN = os.environ.get("LATIDO_TOKEN", "")
ISSUE = os.environ.get("LATIDO_ISSUE", "")

# Nombre del SAI en NUT (`upsc -l` los lista). Vacío = no se consulta el SAI.
UPS = os.environ.get("LATIDO_UPS", "")
# Interfaz por la que sale el respaldo móvil, p. ej. wwan0. Vacío = no se prueba.
IFAZ_MOVIL = os.environ.get("LATIDO_INTERFAZ_MOVIL", "")
DESTINO = os.environ.get("LATIDO_DESTINO", "https://www.google.com/generate_204")

TIMEOUT = 10


def ahora() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ejecutar(orden: list[str]) -> str | None:
    """Ejecuta una orden y devuelve su salida, o None si falla. Nunca lanza."""
    try:
        salida = subprocess.run(
            orden, capture_output=True, text=True, timeout=TIMEOUT, check=True
        )
        return salida.stdout
    except Exception:  # noqa: BLE001 — un colector roto no puede tumbar el latido
        return None


def leer_sai() -> dict:
    """Estado del SAI a través de NUT (`upsc`).

    Devuelve la corriente, la autonomía y la salud de la batería. Si el SAI no
    está configurado o no responde, devuelve un diccionario vacío: el panel
    marcará ese indicador como «sin datos», que es lo honesto.
    """
    if not UPS:
        return {}
    crudo = ejecutar(["upsc", UPS])
    if not crudo:
        return {}

    campos = {}
    for linea in crudo.splitlines():
        if ":" in linea:
            clave, _, valor = linea.partition(":")
            campos[clave.strip()] = valor.strip()

    datos = {}
    estado = campos.get("ups.status", "")
    if estado:
        # OL = on line (hay corriente) · OB = on battery (se ha ido la luz)
        datos["energia"] = "bateria" if "OB" in estado.split() else "red"
    if "battery.runtime" in campos:
        try:
            datos["autonomia_min"] = round(int(campos["battery.runtime"]) / 60)
        except ValueError:
            pass
    if "battery.charge" in campos:
        datos["bateria_pct"] = campos["battery.charge"]
    return datos


def probar_movil() -> dict:
    """Comprueba el respaldo móvil saliendo por su interfaz.

    Es la única forma real de saber si la red del operador funciona: no existe
    ninguna API que lo diga.
    """
    if not IFAZ_MOVIL:
        return {}
    ok = ejecutar([
        "curl", "--silent", "--fail", "--max-time", str(TIMEOUT),
        "--interface", IFAZ_MOVIL, DESTINO,
    ])
    return {"movil": "ok" if ok is not None else "sin_señal"}


def probar_internet() -> dict:
    try:
        peticion = urllib.request.Request(DESTINO, headers={"User-Agent": "latido/1.0"})
        urllib.request.urlopen(peticion, timeout=TIMEOUT).read(1)
        return {"internet": "ok"}
    except Exception:  # noqa: BLE001
        return {"internet": "sin_señal"}


def recoger() -> dict:
    datos = {"ts": ahora(), "maquina": os.uname().nodename if hasattr(os, "uname") else "?"}
    datos.update(probar_internet())
    datos.update(leer_sai())
    datos.update(probar_movil())
    return datos


def enviar(datos: dict) -> int:
    if not (TOKEN and ISSUE):
        print("Faltan LATIDO_TOKEN o LATIDO_ISSUE. Ver docs/06-agente.md", file=sys.stderr)
        return 1

    cuerpo = json.dumps(datos, ensure_ascii=False, indent=2)
    peticion = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/issues/{ISSUE}",
        data=json.dumps({"body": cuerpo}).encode(),
        method="PATCH",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "latido/1.0",
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT) as r:
            r.read()
    except urllib.error.HTTPError as e:
        print(f"GitHub respondió HTTP {e.code}: {e.read()[:200]!r}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        # Que no se pueda enviar no es un error del agente: probablemente es
        # justo la caída que queremos reportar. El panel lo verá por el silencio.
        print(f"No se pudo enviar el latido: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    recogido = recoger()
    if "--probar" in sys.argv:
        print(json.dumps(recogido, ensure_ascii=False, indent=2))
        raise SystemExit(0)
    raise SystemExit(enviar(recogido))
