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

# ── Statuspage: las incidencias también se filtran ───────────────────────
# Cloudflare publica 479 componentes y casi siempre tiene alguna incidencia
# abierta en algún sitio del mundo. Bajo una luz que solo mira España, listarlas
# todas sería dar por nuestro un problema ajeno.
CLOUDFLARE = {
    "status": {"indicator": "minor", "description": "Partially Degraded Service"},
    "components": [
        {"name": "Madrid, Spain - (MAD)", "status": "operational"},
        {"name": "Barcelona, Spain - (BCN)", "status": "operational"},
        {"name": "Izmir, Turkey - (ADB)", "status": "partial_outage"},
    ],
    "incidents": [
        {"name": "Problemas en Izmir", "components": [{"name": "Izmir, Turkey - (ADB)"}]},
    ],
}
ESPANA = ["Madrid, Spain - (MAD)", "Barcelona, Spain - (BCN)"]

fingir_json(CLOUDFLARE)
r = poller.leer_statuspage({"url": "https://www.cloudflarestatus.com", "componentes": ESPANA})
comprobar(r.estado == "operativo", "una avería en Turquía no apaga la luz de España")
comprobar(r.incidencias == [], "ni se cuela en la lista de incidencias")
comprobar("Izmir" not in r.mensaje, "ni se menciona en el mensaje")

CLOUDFLARE_AQUI = dict(CLOUDFLARE)
CLOUDFLARE_AQUI["incidents"] = [
    {"name": "Reencaminamiento en Madrid", "components": [{"name": "Madrid, Spain - (MAD)"}]},
]
fingir_json(CLOUDFLARE_AQUI)
r = poller.leer_statuspage({"url": "https://www.cloudflarestatus.com", "componentes": ESPANA})
comprobar(r.incidencias == ["Reencaminamiento en Madrid"],
          "una incidencia que sí toca España sí se recoge")
comprobar("Madrid" in r.mensaje, "y se ve en el mensaje aunque el estado sea verde")

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

# ── Red Eléctrica de España ──────────────────────────────────────────────
print("\nRed eléctrica (API de REE)")


def demanda(valores):
    """Respuesta de apidatos.ree.es con la serie de demanda real."""
    return {"data": {}, "included": [
        {"attributes": {"title": "Demanda prevista", "values": []}},
        {"attributes": {"title": "Demanda real", "values": valores}},
    ]}


def punto(minutos_atras, mw):
    cuando = poller.ahora() - timedelta(minutes=minutos_atras)
    return {"value": mw, "datetime": cuando.isoformat()}


CFG_REE = {"url": "https://x", "panel": "https://p", "serie": "real",
           "max_minutos": 60, "caida_pct_1h": 30}

# Curva normal: siete puntos de diez minutos, con variación suave.
normal = [punto(60 - i * 10, 28000 + i * 100) for i in range(7)]
fingir_json(demanda(normal))
r = poller.leer_ree(CFG_REE)
comprobar(r.estado == "operativo", "demanda normal -> operativo")
comprobar("28.600 MW" in r.mensaje, "muestra los megavatios actuales")

# Apagón: la demanda se desploma en una hora.
apagon = [punto(60 - i * 10, 28000) for i in range(6)] + [punto(0, 9000)]
fingir_json(demanda(apagon))
r = poller.leer_ree(CFG_REE)
comprobar(r.estado == "caido", "una caída del 68 % en una hora -> apagón")
comprobar("%" in r.mensaje, "y dice cuánto ha caído")

# La curva normal noche/día no puede disparar el aviso.
noche = [punto(60 - i * 10, 30000 - i * 400) for i in range(7)]
fingir_json(demanda(noche))
comprobar(poller.leer_ree(CFG_REE).estado == "operativo",
          "la bajada normal de la curva diaria no dispara falso positivo")

# REE deja de publicar: no sabemos, no es que no haya luz.
fingir_json(demanda([punto(300, 28000)]))
r = poller.leer_ree(CFG_REE)
comprobar(r.estado == "desconocido", "sin datos nuevos de REE -> desconocido, no caído")

fingir_json({"data": {}})
comprobar(poller.leer_ree(CFG_REE).estado == "desconocido",
          "formato inesperado -> desconocido")

# ── IODA: caídas de red por sistema autónomo ─────────────────────────────
print("\nIODA (operadores sin página de estado)")

CFG_IODA = {"asn": 12430, "ventana_horas": 6}

fingir_json({"type": "outages.alerts", "error": None, "data": []})
r = poller.leer_ioda(CFG_IODA)
comprobar(r.estado == "operativo", "sin avisos -> operativo")
comprobar(r.limitado, "la lectura va marcada como indirecta")
comprobar("12430" in r.mensaje, "el mensaje dice de qué red habla")

# IODA emite también avisos de recuperación: no pueden pintar la luz de rojo.
fingir_json({"error": None, "data": [{"level": "normal", "datasource": "bgp"}]})
comprobar(poller.leer_ioda(CFG_IODA).estado == "operativo",
          "un aviso de recuperación no cuenta como caída")

fingir_json({"error": None, "data": [{"level": "warning", "datasource": "ping-slash24"}]})
comprobar(poller.leer_ioda(CFG_IODA).estado == "degradado", "un aviso de nivel warning -> ámbar")

fingir_json({"error": None, "data": [
    {"level": "critical", "datasource": "bgp"},
    {"level": "warning", "datasource": "ping-slash24"},
]})
r = poller.leer_ioda(CFG_IODA)
comprobar(r.estado == "caido", "un aviso crítico -> caída")
comprobar("bgp" in r.mensaje and "ping-slash24" in r.mensaje,
          "y nombra las señales que lo detectaron")

fingir_json({"error": "algo falló", "data": None})
comprobar(poller.leer_ioda(CFG_IODA).estado == "desconocido",
          "si IODA devuelve error -> desconocido, no caído")

fingir_json({"data": "esto no es una lista"})
comprobar(poller.leer_ioda(CFG_IODA).estado == "desconocido", "formato raro -> desconocido")

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
