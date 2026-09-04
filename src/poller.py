#!/usr/bin/env python3
"""Lee el estado de los proveedores, genera site/status.json y avisa por Telegram.

Se ejecuta desde GitHub Actions. Ningún adaptador lanza excepción: ante un fallo de
red o un formato inesperado devuelve `desconocido`, para que una fuente rota no deje
el resto del panel sin actualizar.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "services.yaml"
SALIDA = RAIZ / "site" / "status.json"
ESTADO = RAIZ / "estado.json"

UA = "web-status/1.0 (+https://github.com/hparedes95/web_status)"
TIMEOUT = 20

# Gravedad para quedarse con "la peor" señal. `desconocido` pesa más que operativo
# —hay que verlo— pero menos que un problema real y confirmado.
GRAVEDAD = {"operativo": 0, "desconocido": 1, "degradado": 2, "caido": 3}

# El historial se guarda como una letra por hora: es lo que dibuja la barra del
# panel y ocupa unos pocos KB al año. `-` es una hora sin registro (el workflow
# no llegó a ejecutarse), que no cuenta para el porcentaje de disponibilidad.
LETRA = {"operativo": "o", "degradado": "d", "caido": "c", "desconocido": "u"}
ESTADO_DE_LETRA = {v: k for k, v in LETRA.items()}
HORAS_GUARDADAS = 168   # 7 días: la ventana del porcentaje
HORAS_VISIBLES = 72     # 3 días: lo que se dibuja en la barra

# Vocabulario de Statuspage -> el nuestro. `under_maintenance` cae en degradado:
# se ve en el panel, pero como las alertas solo saltan con `caido`, nunca avisa.
COMPONENTE = {
    "operational": "operativo",
    "degraded_performance": "degradado",
    "partial_outage": "degradado",
    "major_outage": "caido",
    "under_maintenance": "degradado",
}
INDICADOR = {
    "none": "operativo",
    "minor": "degradado",
    "major": "caido",
    "critical": "caido",
    "maintenance": "degradado",
}


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def iso(momento: datetime) -> str:
    return momento.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def peor(estados: list[str]) -> str:
    return max(estados, key=lambda e: GRAVEDAD.get(e, 1)) if estados else "desconocido"


@dataclass
class Lectura:
    estado: str = "desconocido"
    mensaje: str = ""
    url: str = ""
    incidencias: list[str] = field(default_factory=list)
    # Una lectura «limitada» no viene del proveedor: es una comprobación nuestra
    # de que su servicio responde. Detecta caídas totales, no degradaciones. El
    # panel la marca para que nadie la confunda con un estado oficial.
    limitado: bool = False


# ─────────────────────────── acceso a red ───────────────────────────


def pedir(url: str, cabeceras: dict | None = None) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": UA, **(cabeceras or {})})
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as respuesta:
        return respuesta.read()


def decodificar(crudo: bytes) -> str:
    """Texto a partir de los bytes, respetando la marca de orden (BOM).

    No todos los proveedores sirven UTF-8: el feed público de AWS llega en
    UTF-16, y darlo por UTF-8 rompe la lectura con un error de codificación.
    """
    for bom, codificacion in (
        (b"\xff\xfe", "utf-16"),
        (b"\xfe\xff", "utf-16"),
        (b"\xef\xbb\xbf", "utf-8-sig"),
    ):
        if crudo.startswith(bom):
            return crudo.decode(codificacion)
    return crudo.decode("utf-8", errors="replace")


def pedir_json(url: str, cabeceras: dict | None = None):
    return json.loads(decodificar(pedir(url, cabeceras)))


# ─────────────────────────── adaptadores ───────────────────────────


def leer_statuspage(cfg: dict) -> Lectura:
    """Páginas de estado con el formato estándar de Statuspage.

    Un mismo dominio da varias luces independientes si se filtra por componente:
    GitHub y GitHub Copilot salen de la misma petición.
    """
    base = cfg["url"].rstrip("/")
    datos = pedir_json(f"{base}/api/v2/summary.json")
    incidencias = [i.get("name", "") for i in datos.get("incidents", []) if i.get("name")]
    filtro = cfg.get("componentes")

    if filtro:
        elegidos = [c for c in datos.get("components", []) if c.get("name") in filtro]
        if not elegidos:
            return Lectura(
                "desconocido",
                f"No se encontraron los componentes {filtro} en la página de estado",
                base,
                incidencias,
            )
        estado = peor([COMPONENTE.get(c.get("status", ""), "desconocido") for c in elegidos])
        rotos = [c["name"] for c in elegidos if c.get("status") != "operational"]
        mensaje = ", ".join(rotos) if rotos else "Todos los componentes operativos"
    else:
        indicador = (datos.get("status") or {}).get("indicator", "")
        estado = INDICADOR.get(indicador, "desconocido")
        mensaje = (datos.get("status") or {}).get("description", "")

    if incidencias and estado == "operativo":
        # La página se declara operativa pero hay incidencias abiertas: se muestran,
        # sin cambiar el estado. Manda lo que diga el proveedor.
        mensaje = f"{mensaje} · Incidencias abiertas: {'; '.join(incidencias[:3])}".strip(" ·")

    return Lectura(estado, mensaje, base, incidencias)


def leer_rss(cfg: dict) -> Lectura:
    """Feeds RSS de incidencias (Azure, Microsoft 365).

    Un RSS no publica un estado, publica *eventos*. La aproximación es: si hay
    entradas recientes que mencionen nuestras regiones, algo pasa. Es una señal
    gruesa y por eso el panel enlaza siempre a la página oficial.
    """
    import feedparser  # se importa aquí para que el resto funcione sin la dependencia

    crudo = pedir(cfg["url"])
    feed = feedparser.parse(crudo)
    if getattr(feed, "bozo", False) and not feed.entries:
        return Lectura("desconocido", "El feed no se pudo interpretar", cfg["url"])

    ventana = timedelta(hours=cfg.get("ventana_horas", 6))
    regiones = [r.lower() for r in cfg.get("regiones", [])]
    limite = ahora() - ventana
    recientes = []

    for entrada in feed.entries:
        marca = entrada.get("published_parsed") or entrada.get("updated_parsed")
        if marca:
            publicada = datetime(*marca[:6], tzinfo=timezone.utc)
            if publicada < limite:
                continue
        titulo = entrada.get("title", "")
        cuerpo = f"{titulo} {entrada.get('summary', '')}".lower()
        if regiones and not any(r in cuerpo for r in regiones):
            continue
        recientes.append(titulo)

    if not recientes:
        return Lectura("operativo", "Sin avisos recientes", cfg["url"])
    return Lectura("degradado", "; ".join(recientes[:3]), cfg["url"], recientes)


def leer_aws(cfg: dict) -> Lectura:
    """Health Dashboard público de AWS.

    Sirve JSON en UTF-16 y **con el histórico completo**, no solo lo que está
    pasando ahora: sin filtrar por fecha, cualquier región acabaría marcada como
    degradada para siempre. El filtro que manda es la ventana temporal.

    El formato no está documentado como API estable, así que se lee de forma
    defensiva: lo que no encaje devuelve `desconocido` en vez de inventarse nada.
    """
    datos = pedir_json(cfg["url"])
    eventos = datos if isinstance(datos, list) else datos.get("events", datos.get("currentEvents"))
    if not isinstance(eventos, list):
        return Lectura("desconocido", "Formato inesperado en el feed de AWS", cfg["url"])

    ventana = timedelta(hours=cfg.get("ventana_horas", 6))
    limite = (ahora() - ventana).timestamp()
    regiones = [r.lower() for r in cfg.get("regiones", [])]
    servicios = [s.lower() for s in cfg.get("servicios", [])]
    afectan = []

    for evento in eventos:
        if not isinstance(evento, dict):
            continue
        try:
            cuando = float(evento.get("date", 0))
        except (TypeError, ValueError):
            continue
        if cuando < limite:
            continue

        texto = json.dumps(evento, ensure_ascii=False).lower()
        if regiones and not any(r in texto for r in regiones):
            continue
        if servicios and not any(s in texto for s in servicios):
            continue
        afectan.append(evento.get("event_title") or evento.get("summary") or "Evento sin título")

    if not afectan:
        return Lectura("operativo", "Sin eventos recientes en nuestras regiones", cfg["url"])
    return Lectura("degradado", "; ".join(afectan[:3]), cfg["url"], afectan)


# Vocabulario de Microsoft Graph -> el nuestro.
SALUD_M365 = {
    "serviceOperational": "operativo",
    "serviceRestored": "operativo",
    "resolved": "operativo",
    "resolvedExternal": "operativo",
    "falsePositive": "operativo",
    "postIncidentReviewPublished": "operativo",
    "mitigated": "degradado",
    "mitigatedExternal": "degradado",
    "extendedRecovery": "degradado",
    "investigating": "degradado",
    "verifyingService": "degradado",
    "restoringService": "degradado",
    "investigationSuspended": "degradado",
    "reported": "degradado",
    "confirmed": "degradado",
    "serviceDegradation": "degradado",
    "serviceInterruption": "caido",
}


def leer_graph(cfg: dict) -> Lectura:
    """Service Health de Microsoft 365, vía Microsoft Graph.

    Es la única fuente real para Microsoft 365: su panel público no publica
    ningún feed, solo una página web (comprobado con scripts/probe.py). A cambio,
    Graph da el estado de *nuestro* tenant, no el global, que es mejor dato.

    Necesita una aplicación en Entra ID con el permiso de aplicación
    ServiceHealth.Read.All y consentimiento de administrador, y sus credenciales
    en los secretos del repositorio.
    """
    tenant = os.environ.get("M365_TENANT_ID", "")
    cliente = os.environ.get("M365_CLIENT_ID", "")
    secreto = os.environ.get("M365_CLIENT_SECRET", "")
    panel = "https://status.cloud.microsoft/"

    if not (tenant and cliente and secreto):
        return Lectura(
            "desconocido",
            "Falta la aplicación de Entra ID: Microsoft no publica ningún feed "
            "para Microsoft 365, así que este estado solo puede venir de Graph "
            "(ver docs/04-arranque.md)",
            panel,
        )

    cuerpo = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cliente,
        "client_secret": secreto,
        "scope": "https://graph.microsoft.com/.default",
    }).encode()
    peticion = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        data=cuerpo,
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(peticion, timeout=TIMEOUT) as r:
        token = json.loads(decodificar(r.read())).get("access_token", "")
    if not token:
        return Lectura("desconocido", "Entra ID no devolvió ningún token", panel)

    datos = pedir_json(
        "https://graph.microsoft.com/v1.0/admin/serviceAnnouncement/healthOverviews",
        {"Authorization": f"Bearer {token}"},
    )
    quiero = cfg.get("servicios") or []
    todos = datos.get("value", [])
    elegidos = [s for s in todos if not quiero or s.get("service") in quiero]
    if not elegidos:
        return Lectura("desconocido", f"Graph no devolvió los servicios {quiero}", panel)

    estado = peor([SALUD_M365.get(s.get("status", ""), "desconocido") for s in elegidos])
    rotos = [
        f"{s['service']} ({s.get('status')})"
        for s in elegidos
        if SALUD_M365.get(s.get("status", "")) != "operativo"
    ]
    mensaje = ", ".join(rotos) if rotos else f"{len(elegidos)} servicios operativos"
    return Lectura(estado, mensaje, panel, rotos)


# Vocabulario del panel de estado de Google -> el nuestro.
IMPACTO_GOOGLE = {
    "SERVICE_OUTAGE": "caido",
    "SERVICE_DISRUPTION": "degradado",
    "SERVICE_INFORMATION": "degradado",
}


def leer_google(cfg: dict) -> Lectura:
    """Paneles de estado de Google (Cloud y Workspace).

    Los dos publican el mismo formato: una lista de incidencias donde `end` vacío
    significa que sigue abierta. Se consultan ambos porque un mismo producto puede
    aparecer en uno u otro —Gemini está en Workspace como aplicación y en Cloud
    como API—, y se filtra por nombre de producto sin distinguir mayúsculas, que
    aguanta mejor los cambios de marca de Google.
    """
    urls = cfg.get("urls") or [cfg["url"]]
    productos = [p.lower() for p in cfg.get("productos", [])]
    ventana = timedelta(hours=cfg.get("ventana_horas", 48))
    limite = ahora() - ventana

    incidencias, leidas = [], 0
    for url in urls:
        try:
            datos = pedir_json(url)
        except Exception:  # noqa: BLE001 — con que responda una de las dos, basta
            continue
        if not isinstance(datos, list):
            continue
        leidas += 1

        for inc in datos:
            if not isinstance(inc, dict) or inc.get("end"):
                continue  # cerrada

            # Una incidencia abierta pero sin tocar en días es casi siempre uno
            # de esos avisos que a Google se le olvida cerrar.
            marca = inc.get("modified") or inc.get("begin") or ""
            try:
                if datetime.fromisoformat(marca.replace("Z", "+00:00")) < limite:
                    continue
            except (ValueError, AttributeError):
                pass

            nombres = [inc.get("service_name", "")] + [
                p.get("title", "") for p in inc.get("affected_products", []) if isinstance(p, dict)
            ]
            texto = " ".join(nombres).lower()
            if productos and not any(p in texto for p in productos):
                continue

            incidencias.append((
                IMPACTO_GOOGLE.get(inc.get("status_impact", ""), "degradado"),
                (inc.get("external_desc") or "Incidencia sin descripción").split("\n")[0][:120],
            ))

    if not leidas:
        return Lectura("desconocido", "No se pudo leer ningún panel de estado de Google")
    panel = urls[0].rsplit("/", 1)[0]
    if not incidencias:
        return Lectura("operativo", "Sin incidencias abiertas", panel)
    return Lectura(
        peor([e for e, _ in incidencias]),
        "; ".join(m for _, m in incidencias[:2]),
        panel,
        [m for _, m in incidencias],
    )


def leer_manual(cfg: dict, servicio_id: str) -> Lectura:
    """Estado marcado a mano mediante issues etiquetadas `caida:<id>`.

    En GitHub solo quien tiene permiso de escritura puede poner etiquetas, así que
    en un repositorio público cualquiera puede abrir una issue, pero nadie de fuera
    puede encender una luz del panel.
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repo:
        # Sin contexto de repositorio no se pueden leer las issues, y por tanto no
        # se sabe nada: nunca dar por operativo lo que no se ha podido comprobar.
        return Lectura("desconocido", "Sin acceso a las issues del repositorio", "")

    etiqueta = urllib.parse.quote(f"caida:{servicio_id}")
    url = f"https://api.github.com/repos/{repo}/issues?state=open&labels={etiqueta}&per_page=5"
    cabeceras = {"Accept": "application/vnd.github+json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"

    issues = pedir_json(url, cabeceras)
    abiertas = [i for i in issues if isinstance(i, dict) and "pull_request" not in i]
    if not abiertas:
        return Lectura("operativo", "Sin incidencia marcada", f"https://github.com/{repo}/issues")

    issue = abiertas[0]
    autor = (issue.get("user") or {}).get("login", "alguien")
    return Lectura(
        "caido",
        f"{issue.get('title', 'Incidencia')} — marcado por @{autor}",
        issue.get("html_url", ""),
        [i.get("title", "") for i in abiertas],
    )


def leer_m365(cfg: dict) -> Lectura:
    """Microsoft 365, por la mejor fuente disponible.

    Con credenciales de Entra ID usa Microsoft Graph, que es el estado oficial de
    nuestro tenant. Sin ellas cae a una sonda propia: Microsoft no publica ningún
    feed —comprobado— y las rutas `/api/*` de su panel devuelven la misma página
    web, porque los datos salen de un bundle JavaScript. Destripar ese bundle
    sería un endpoint no documentado que se rompe solo, así que no se hace.

    La sonda comprueba que responden endpoints públicos y documentados de
    Microsoft. Detecta una caída total del inicio de sesión, que es la avería más
    grave posible, pero **no** ve una degradación de Teams o de Exchange. Por eso
    la lectura se marca como limitada.
    """
    if os.environ.get("M365_TENANT_ID"):
        return leer_graph(cfg)

    fallos = []
    for nombre, url in cfg.get("sondas", {}).items():
        try:
            pedir(url)
        except Exception as e:  # noqa: BLE001
            fallos.append(f"{nombre}: {e}")

    panel = "https://status.cloud.microsoft/"
    if fallos:
        # No se marca como caído: desde un único punto de observación no se puede
        # distinguir «Microsoft está caído» de «no llegamos a Microsoft», y dar
        # por caído lo segundo dispararía una alerta falsa.
        return Lectura(
            "desconocido",
            "No se pudo llegar a los endpoints de Microsoft: " + "; ".join(fallos),
            panel,
            fallos,
            limitado=True,
        )
    return Lectura(
        "operativo",
        "Los endpoints públicos de Microsoft responden. Comprobación propia, no el "
        "estado oficial: Microsoft no publica feed y no ve degradaciones parciales",
        panel,
        limitado=True,
    )


ADAPTADORES = {
    "statuspage": lambda cfg, _id: leer_statuspage(cfg),
    "rss": lambda cfg, _id: leer_rss(cfg),
    "json": lambda cfg, _id: leer_aws(cfg),
    "graph": lambda cfg, _id: leer_graph(cfg),
    "m365": lambda cfg, _id: leer_m365(cfg),
    "google": lambda cfg, _id: leer_google(cfg),
    "manual": lambda cfg, sid: leer_manual(cfg, sid),
}


def leer(servicio: dict) -> Lectura:
    cfg = servicio["fuente"]
    adaptador = ADAPTADORES.get(cfg.get("tipo"))
    if adaptador is None:
        return Lectura("desconocido", f"Tipo de fuente no soportado: {cfg.get('tipo')}")
    try:
        return adaptador(cfg, servicio["id"])
    except urllib.error.HTTPError as e:
        return Lectura("desconocido", f"La fuente respondió HTTP {e.code}", cfg.get("url", ""))
    except Exception as e:  # noqa: BLE001 — un adaptador roto no puede tumbar el ciclo
        return Lectura("desconocido", f"No se pudo leer la fuente: {e}", cfg.get("url", ""))


def actualizar_historial(anterior: dict, estado: str, momento: datetime) -> tuple[str, str]:
    """Añade la lectura a la línea temporal por horas.

    Dentro de una misma hora se conserva **la peor** lectura: una caída de diez
    minutos no debe desaparecer porque las cinco lecturas siguientes fueran buenas.
    """
    horas = anterior.get("horas", "")
    ultima = anterior.get("ultima_hora")
    hora = momento.replace(minute=0, second=0, microsecond=0)
    letra = LETRA[estado]

    if not ultima:
        horas += letra
    else:
        try:
            previa = datetime.fromisoformat(ultima.replace("Z", "+00:00"))
        except ValueError:
            previa = hora
        saltos = int((hora - previa).total_seconds() // 3600)
        if saltos <= 0 and horas:
            previo = ESTADO_DE_LETRA.get(horas[-1], "desconocido")
            horas = horas[:-1] + LETRA[peor([previo, estado])]
        elif saltos <= 0:
            horas = letra
        else:
            horas += "-" * (saltos - 1) + letra

    return horas[-HORAS_GUARDADAS:], iso(hora)


def disponibilidad(horas: str) -> float | None:
    """Porcentaje de horas operativas sobre las horas con lectura concluyente.

    Las horas sin registro (`-`) y las ilegibles (`u`) quedan fuera del cálculo:
    no sabemos qué pasó en ellas, y contarlas como caída convertiría un adaptador
    roto en una supuesta indisponibilidad del proveedor. El hueco sigue siendo
    visible en la barra y en la etiqueta «sin datos», que es donde corresponde.
    """
    concluyentes = [h for h in horas if h in ("o", "d", "c")]
    if len(concluyentes) < 6:  # con menos de 6 horas el número engaña más que informa
        return None
    return round(100 * sum(1 for h in concluyentes if h == "o") / len(concluyentes), 2)


# ─────────────────────────── alertas ───────────────────────────


def avisar(texto: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        print(f"[telegram] sin credenciales, no se envía: {texto}")
        return False

    cuerpo = urllib.parse.urlencode(
        {"chat_id": chat, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": "true"}
    ).encode()
    peticion = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=cuerpo,
        headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT) as r:
            r.read()
        return True
    except Exception as e:  # noqa: BLE001 — que falle el aviso no puede parar el panel
        print(f"[telegram] error al enviar: {e}", file=sys.stderr)
        return False


def duracion_legible(desde: str | None, hasta: datetime) -> str:
    if not desde:
        return "un rato"
    try:
        inicio = datetime.fromisoformat(desde.replace("Z", "+00:00"))
    except ValueError:
        return "un rato"
    minutos = int((hasta - inicio).total_seconds() // 60)
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas} h {resto} min" if resto else f"{horas} h"


# ─────────────────────────── ciclo principal ───────────────────────────


def main() -> int:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    servicios = config["servicios"]
    reglas = config.get("alerta", {})
    minimo = int(reglas.get("lecturas_para_avisar", 2))
    avisar_recuperacion = bool(reglas.get("avisar_recuperacion", True))

    previo = {}
    if ESTADO.exists():
        previo = json.loads(ESTADO.read_text(encoding="utf-8")).get("servicios", {})

    momento = ahora()
    nuevo_estado, salida = {}, []

    for servicio in servicios:
        sid = servicio["id"]
        lectura = leer(servicio)
        anterior = previo.get(sid, {})
        antes = anterior.get("estado")

        cambio = antes != lectura.estado
        desde = momento if cambio or not anterior.get("desde") else None
        fallos = (anterior.get("fallos", 0) + 1) if lectura.estado == "caido" else 0

        # Momento en que el servicio dejó de estar operativo, para poder decir
        # cuánto duró la caída cuando se recupere.
        roto_desde = anterior.get("roto_desde")
        if lectura.estado == "operativo":
            roto_desde = None
        elif not roto_desde:
            roto_desde = iso(momento)

        horas, ultima_hora = actualizar_historial(anterior, lectura.estado, momento)
        alertado = bool(anterior.get("alertado", False))
        nombre = servicio["nombre"]
        enlace = lectura.url or servicio["fuente"].get("url", "")

        if servicio.get("alerta") and lectura.estado == "caido" and fallos >= minimo and not alertado:
            texto = f"🔴 <b>{nombre}</b> caído"
            if lectura.mensaje:
                texto += f"\n{lectura.mensaje}"
            if enlace:
                texto += f"\n{enlace}"
            avisar(texto)
            alertado = True
        elif alertado and lectura.estado == "operativo":
            if avisar_recuperacion:
                avisar(
                    f"🟢 <b>{nombre}</b> operativo tras "
                    f"{duracion_legible(anterior.get('roto_desde'), momento)}"
                )
            alertado = False

        nuevo_estado[sid] = {
            "estado": lectura.estado,
            "desde": iso(desde) if desde else anterior.get("desde", iso(momento)),
            "fallos": fallos,
            "alertado": alertado,
            "roto_desde": roto_desde,
            "horas": horas,
            "ultima_hora": ultima_hora,
        }
        salida.append(
            {
                "id": sid,
                "nombre": nombre,
                "detalle": servicio.get("detalle", ""),
                "estado": lectura.estado,
                "mensaje": lectura.mensaje,
                "url": enlace,
                "desde": nuevo_estado[sid]["desde"],
                "categoria": servicio.get("categoria", "otros"),
                "limitado": lectura.limitado,
                "historial": horas[-HORAS_VISIBLES:],
                "disponibilidad": disponibilidad(horas),
                "manual": servicio["fuente"].get("tipo") == "manual",
                "alerta": bool(servicio.get("alerta")),
            }
        )
        print(f"  {sid:<16} {lectura.estado:<12} {lectura.mensaje[:70]}")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        json.dumps({"generado_en": iso(momento), "servicios": salida}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    # `dia` fuerza un commit diario aunque no cambie nada: GitHub desactiva los
    # workflows programados tras 60 días sin actividad en el repositorio.
    ESTADO.write_text(
        json.dumps(
            {"dia": momento.date().isoformat(), "servicios": nuevo_estado},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    caidos = [s["nombre"] for s in salida if s["estado"] == "caido"]
    print(f"\n{len(salida)} servicios · {len(caidos)} caídos" + (f": {', '.join(caidos)}" if caidos else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
