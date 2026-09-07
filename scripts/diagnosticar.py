#!/usr/bin/env python3
"""Ejecuta el adaptador de un indicador y enseña exactamente qué devuelve.

Es la herramienta para cuando una luz se queda en gris y no se sabe por qué: en
vez de bucear en el log del ciclo completo, ejecuta solo ese adaptador y escribe
el estado y el mensaje.

    python scripts/diagnosticar.py red-electrica
    python scripts/diagnosticar.py             # todos
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml  # noqa: E402

import poller  # noqa: E402

if __name__ == "__main__":
    config = yaml.safe_load(poller.CONFIG.read_text(encoding="utf-8"))
    querido = sys.argv[1] if len(sys.argv) > 1 else None

    for servicio in config["servicios"]:
        if querido and servicio["id"] != querido:
            continue
        print(f"\n── {servicio['id']}  ({servicio['fuente']['tipo']})")
        lectura = poller.leer(servicio)
        print(f"   estado : {lectura.estado}")
        print(f"   mensaje: {lectura.mensaje}")
        if lectura.url:
            print(f"   enlace : {lectura.url}")
