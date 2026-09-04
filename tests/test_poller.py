#!/usr/bin/env python3
"""Pruebas del poller, sin red: se sustituyen las peticiones por respuestas de ejemplo.

    python tests/test_poller.py
"""

import json
import shutil
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml  # noqa: E402

import poller  # noqa: E402

fallos = []


def comprobar(condicion, descripcion):
    print(("  ok   " if condicion else "  FALLO ") + descripcion)
    if not condicion:
        fallos.append(descripcion)


def fingir_json(respuesta):
    poller.pedir_json = lambda url, cabeceras=None: respuesta


# ── Statuspage: todo operativo ───────────────────────────────────────────
print("\nStatuspage")

fingir_json({"status": {"indicator": "none", "description": "All Systems Operational"},
             "components": [], "incidents": []})
r = poller.leer_statuspage({"url": "https://status.ejemplo.com"})
comprobar(r.estado == "operativo", "página sin incidencias -> operativo")

# ── Statuspage: caída global ─────────────────────────────────────────────
fingir_json({"status": {"indicator": "major", "description": "Major Service Outage"},
             "components": [], "incidents": [{"name": "API errors"}]})
r = poller.leer_statuspage({"url": "https://status.ejemplo.com"})
comprobar(r.estado == "caido", "indicador 'major' -> caido")
comprobar(r.incidencias == ["API errors"], "recoge el nombre de la incidencia abierta")

# ── Statuspage: filtrado por componente ──────────────────────────────────
GITHUB = {
    "status": {"indicator": "minor", "description": "Partially Degraded Service"},
    "components": [
        {"name": "Git Operations", "status": "operational"},
        {"name": "Actions", "status": "operational"},
        {"name": "Copilot", "status": "major_outage"},
    ],
    "incidents": [],
}
fingir_json(GITHUB)
r = poller.leer_statuspage({"url": "https://www.githubstatus.com",
                            "componentes": ["Git Operations", "Actions"]})
comprobar(r.estado == "operativo", "una caída de Copilot no apaga la luz de GitHub")

fingir_json(GITHUB)
r = poller.leer_statuspage({"url": "https://www.githubstatus.com", "componentes": ["Copilot"]})
comprobar(r.estado == "caido", "la luz de Copilot sí refleja su propia caída")
comprobar("Copilot" in r.mensaje, "el mensaje nombra el componente roto")

# ── Statuspage: componente que ya no existe ──────────────────────────────
fingir_json(GITHUB)
r = poller.leer_statuspage({"url": "https://www.githubstatus.com", "componentes": ["Inventado"]})
comprobar(r.estado == "desconocido", "un componente inexistente -> desconocido, no verde")

# ── Paneles de estado de Google ──────────────────────────────────────────
print("\nGoogle (Cloud y Workspace)")

AHORA = poller.iso(poller.ahora())
INCIDENCIAS = [
    {  # cerrada: no debe contar
        "end": "2026-09-01T10:00:00+00:00", "modified": AHORA,
        "service_name": "Gemini", "affected_products": [{"title": "Gemini"}],
        "status_impact": "SERVICE_OUTAGE", "external_desc": "Ya resuelta",
    },
    {  # abierta pero de otro producto
        "end": None, "modified": AHORA,
        "service_name": "Google Chat", "affected_products": [{"title": "Google Chat"}],
        "status_impact": "SERVICE_OUTAGE", "external_desc": "Chat caído",
    },
]
poller.pedir_json = lambda url, cabeceras=None: INCIDENCIAS
r = poller.leer_google({"urls": ["https://x/incidents.json"], "productos": ["gemini"]})
comprobar(r.estado == "operativo", "una incidencia cerrada de Gemini no lo pone en rojo")
comprobar(r.estado == "operativo", "una incidencia de otro producto tampoco")

ABIERTA = [{
    "end": None, "modified": AHORA,
    "service_name": "Vertex AI", "affected_products": [{"title": "Vertex AI"}],
    "status_impact": "SERVICE_DISRUPTION", "external_desc": "Latencia elevada\nmás detalle",
}]
poller.pedir_json = lambda url, cabeceras=None: ABIERTA
r = poller.leer_google({"urls": ["https://x/incidents.json"], "productos": ["gemini", "vertex ai"]})
comprobar(r.estado == "degradado", "una interrupción abierta de Vertex AI lo pone en ámbar")
comprobar(r.mensaje == "Latencia elevada", "el mensaje se queda con la primera línea")

CADUCA = [{
    "end": None, "modified": "2026-01-01T00:00:00+00:00",
    "service_name": "Gemini", "affected_products": [{"title": "Gemini"}],
    "status_impact": "SERVICE_OUTAGE", "external_desc": "Abierta desde hace meses",
}]
poller.pedir_json = lambda url, cabeceras=None: CADUCA
r = poller.leer_google({"urls": ["https://x/incidents.json"], "productos": ["gemini"]})
comprobar(r.estado == "operativo", "una incidencia abierta pero sin tocar en meses se ignora")

# ── Un adaptador roto no puede tumbar el ciclo ───────────────────────────
print("\nTolerancia a fallos")


def explotar(url, cabeceras=None):
    raise ConnectionError("la red se fue")


poller.pedir_json = explotar
r = poller.leer({"id": "x", "nombre": "X", "fuente": {"tipo": "statuspage", "url": "https://x"}})
comprobar(r.estado == "desconocido", "fuente inalcanzable -> desconocido sin excepción")

r = poller.leer({"id": "x", "nombre": "X", "fuente": {"tipo": "inventado"}})
comprobar(r.estado == "desconocido", "tipo de fuente no soportado -> desconocido")

# ── Peor de varias señales ───────────────────────────────────────────────
print("\nAgregación")
comprobar(poller.peor(["operativo", "caido", "degradado"]) == "caido", "manda la peor señal")
comprobar(poller.peor(["operativo", "desconocido"]) == "desconocido",
          "desconocido pesa más que operativo")
comprobar(poller.peor(["desconocido", "degradado"]) == "degradado",
          "un problema real pesa más que una fuente ilegible")

# ── Duración legible ─────────────────────────────────────────────────────
print("\nMensajes de recuperación")
ahora = poller.ahora()
comprobar(poller.duracion_legible(poller.iso(ahora - timedelta(minutes=34)), ahora) == "34 min",
          "34 minutos")
comprobar(poller.duracion_legible(poller.iso(ahora - timedelta(hours=2)), ahora) == "2 h", "2 horas")
comprobar(poller.duracion_legible(poller.iso(ahora - timedelta(minutes=95)), ahora) == "1 h 35 min",
          "1 hora y 35 minutos")
comprobar(poller.duracion_legible(None, ahora) == "un rato", "sin fecha previa no revienta")

# ── Ciclo completo: sin red, todo debe quedar en desconocido ─────────────
print("\nCiclo completo (sin red)")
poller.pedir_json = explotar
poller.pedir = explotar
enviados = []
poller.avisar = lambda texto: enviados.append(texto) or True

# Las pruebas escriben en un directorio temporal: nunca sobre site/status.json
# ni sobre estado.json reales, que son ficheros versionados del proyecto.
temporal = Path(tempfile.mkdtemp(prefix="web-status-test-"))
poller.SALIDA = temporal / "status.json"
poller.ESTADO = temporal / "estado.json"

comprobar(poller.main() == 0, "el ciclo termina sin errores aunque no haya red")
salida = json.loads(poller.SALIDA.read_text())
# El número sale de la configuración, no fijado a mano: añadir un servicio no
# debe romper la prueba.
esperados = len(yaml.safe_load(poller.CONFIG.read_text())["servicios"])
comprobar(len(salida["servicios"]) == esperados, f"genera los {esperados} indicadores")
comprobar(all(s["estado"] == "desconocido" for s in salida["servicios"]),
          "sin red, todo queda en desconocido (nunca en verde)")
comprobar(enviados == [], "desconocido no dispara ninguna alerta")

# ── Antirrebote y aviso de recuperación ──────────────────────────────────
print("\nReglas de alerta")


def ciclo_con(estado_forzado):
    poller.leer = lambda servicio: poller.Lectura(estado_forzado, "prueba", "https://x")
    enviados.clear()
    poller.main()
    return list(enviados)


poller.ESTADO.unlink(missing_ok=True)
primera = ciclo_con("caido")
comprobar(primera == [], "primera lectura en rojo: aún no avisa (antirrebote)")

segunda = ciclo_con("caido")
con_alerta = sum(
    1 for s in yaml.safe_load(poller.CONFIG.read_text())["servicios"] if s.get("alerta")
)
comprobar(len(segunda) == con_alerta,
          f"segunda lectura en rojo: avisa de los {con_alerta} con alerta activada")
comprobar(all(t.startswith("🔴") for t in segunda), "el aviso de caída va marcado en rojo")

tercera = ciclo_con("caido")
comprobar(tercera == [], "sigue caído: no repite el aviso en cada ciclo")

recuperacion = ciclo_con("operativo")
comprobar(len(recuperacion) == con_alerta, "al recuperarse avisa una vez por servicio")
comprobar(all(t.startswith("🟢") and "tras" in t for t in recuperacion),
          "el aviso de recuperación incluye la duración")

siguiente = ciclo_con("operativo")
comprobar(siguiente == [], "ya recuperado: silencio")

# ── Limpieza y resultado ─────────────────────────────────────────────────
shutil.rmtree(temporal, ignore_errors=True)

print()
if fallos:
    print(f"{len(fallos)} comprobaciones fallidas:")
    for f in fallos:
        print(f"  - {f}")
    raise SystemExit(1)
print("Todas las comprobaciones pasan.")
