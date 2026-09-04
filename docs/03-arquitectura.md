# 03 — Arquitectura propuesta

## 1. La restricción que manda sobre todo lo demás

> **Si se cae internet, el panel tiene que seguir siendo visible.**

Un panel de estado alojado dentro de la red que se cae justo cuando se cae la red es
inútil precisamente en el momento para el que se construyó. Y a la vez, las sondas que
miden *nuestra* conectividad tienen que ejecutarse *desde dentro*. Las dos cosas no
caben en el mismo sitio, así que la arquitectura es híbrida:

```
                    ┌──────────────────────────────────┐
   Feeds públicos   │   RECOLECTOR (fuera: cloud/VPS)  │
   ───────────────► │   · adaptadores de proveedores   │
   Graph / ARM      │   · almacena histórico            │
   ───────────────► │   · API + panel web              │◄── navegador / móvil
                    └───────────────▲──────────────────┘     (visible aunque
                                    │ push cada 60 s           la oficina esté
                    ┌───────────────┴──────────────────┐      sin línea)
                    │   AGENTE LOCAL (dentro de la red)│
                    │   · sondas: gateway, DNS, WAN    │
                    │   · SNMP del SAI                 │
                    └──────────────────────────────────┘
```

El agente local **empuja** (no se le consulta): si deja de reportar durante 3 ciclos,
el recolector lo interpreta como *"la sede X ha perdido conectividad"*, que es
exactamente la señal que queremos. **El silencio del agente es un dato, no un fallo.**

## 2. Componentes

| Componente | Responsabilidad | Fase |
|---|---|---|
| **Poller** | Ejecuta los adaptadores según su intervalo, normaliza y guarda | 1 |
| **Adaptadores** | Un módulo por tipo de fuente. Contrato común (ver §4) | 1–2 |
| **Almacén** | Estado actual + histórico de cambios e incidencias | 1 |
| **API** | REST/JSON para el panel y para integraciones | 1 |
| **Panel web** | La pantalla que se mira. Debe cargar en <2 s | 1 |
| **Agente local** | Sondas dentro de la red, empuja resultados | 3 |
| **Notificador** | Teams/correo con reglas antirruido | 4 |
| **Informes** | Resumen semanal, exportable | 5 |

## 3. Modelo de datos

Tres tablas bastan. Resistir la tentación de añadir más.

```sql
-- Catálogo: qué vigilamos (se carga desde services.yaml)
CREATE TABLE service (
  id           TEXT PRIMARY KEY,        -- 'anthropic-claude'
  nombre       TEXT NOT NULL,
  categoria    TEXT NOT NULL,           -- cloud | ia | saas | conectividad | suministro
  criticidad   TEXT NOT NULL,           -- alta | media | baja
  config       JSON NOT NULL            -- fuentes y sus parámetros
);

-- Última lectura de cada par (servicio, fuente). Se sobrescribe.
CREATE TABLE current_status (
  service_id   TEXT NOT NULL REFERENCES service(id),
  fuente       TEXT NOT NULL,           -- 'statuspage' | 'graph' | 'sonda' | 'manual'
  estado       TEXT NOT NULL,           -- operational|degraded|partial|major|maintenance|unknown
  detalle      TEXT,                    -- texto del proveedor
  url          TEXT,                    -- enlace a la página oficial
  medido_en    TIMESTAMP NOT NULL,
  PRIMARY KEY (service_id, fuente)
);

-- Histórico: SOLO cambios de estado, no cada sondeo.
CREATE TABLE status_change (
  id           INTEGER PRIMARY KEY,
  service_id   TEXT NOT NULL REFERENCES service(id),
  fuente       TEXT NOT NULL,
  estado_ant   TEXT,
  estado_nuevo TEXT NOT NULL,
  detalle      TEXT,
  ocurrido_en  TIMESTAMP NOT NULL
);
CREATE INDEX idx_change_svc_time ON status_change(service_id, ocurrido_en DESC);
```

**Guardar solo transiciones** y no cada sondeo mantiene la base de datos en unos pocos
MB al año. 40 servicios sondeados cada minuto durante un año serían ~21 millones de
filas inútiles; los cambios reales son unos pocos miles. SQLite sobra para este
volumen y evita administrar un servidor de base de datos.

## 4. Contrato del adaptador

Todo adaptador implementa la misma interfaz. Es lo que permite añadir un proveedor
nuevo en minutos y probarlo sin red.

```python
@dataclass(frozen=True)
class Lectura:
    estado: Estado            # enum normalizado, común a todas las fuentes
    detalle: str | None       # texto tal cual lo publica el proveedor
    url: str | None           # enlace a la página oficial
    medido_en: datetime

class Adaptador(Protocol):
    tipo: str
    def leer(self, cfg: dict) -> list[tuple[str, Lectura]]:
        """Devuelve (service_id, Lectura). Ante error de red o formato
        inesperado, devuelve estado=UNKNOWN. NUNCA lanza excepción:
        un adaptador roto no puede tumbar el ciclo de los demás."""
```

Normalización de estados — cada proveedor usa su vocabulario, nosotros solo cinco:

| Nuestro estado | Color | Equivalencias típicas |
|---|---|---|
| `operational` | 🟢 | operational, none, Available, Normal service |
| `degraded` | 🟡 | degraded_performance, minor, Advisory |
| `partial` | 🟠 | partial_outage, Service degradation |
| `major` | 🔴 | major_outage, critical, Service interruption |
| `maintenance` | 🔵 | under_maintenance, planned |
| `unknown` | ⚪ | no se pudo leer la fuente |

`unknown` es un estado de primera clase y se pinta en el panel. Un adaptador que lleva
tres días fallando en silencio es el fallo más peligroso de un sistema así: parece que
todo va bien porque nadie mira lo que no se ve.

## 5. Reglas de agregación

Cuando un servicio tiene varias fuentes, el estado que se muestra es **el peor**, y el
panel indica cuál manda:

| Feed oficial | Sonda propia | Se muestra | Texto |
|---|---|---|---|
| 🟢 | 🟢 | 🟢 | Operativo |
| 🟢 | 🔴 | 🟠 | "No nos responde; el proveedor aún no lo reconoce" |
| 🔴 | 🟢 | 🔴 | "Incidencia declarada por el proveedor" |
| ⚪ | 🟢 | 🟢 | Operativo (con aviso de fuente no disponible) |

## 6. Pila técnica recomendada

| Capa | Elección | Motivo |
|---|---|---|
| Lenguaje | **Python 3.12** | El equipo ya trabaja en Python; `httpx` + `feedparser` cubren el 100 % de los adaptadores |
| API | **FastAPI** | Tipado, documentación automática, arranque rápido |
| Planificación | **APScheduler** en el mismo proceso | Un servicio menos que operar. Migrar a Celery solo si hace falta |
| Datos | **SQLite** (con WAL) | Volumen mínimo, cero administración. Postgres si algún día hay varias instancias |
| Panel | **HTML + HTMX**, sin framework SPA | La pantalla es una rejilla que se autorefresca. Un React aquí es coste sin retorno |
| Empaquetado | **Docker**, imagen única | Recolector y agente en la misma imagen con distinto modo de arranque |
| Despliegue | Contenedor en VPS o Azure Container Apps | Barato y, sobre todo, **fuera de nuestra red** |

**Alternativa consciente:** si en Fase 3 las sondas se complican, desplegar
**Uptime Kuma** y escribir un adaptador que lea su API. Deja de ser trabajo nuestro.

## 7. Requisitos no funcionales

| Requisito | Objetivo | Por qué |
|---|---|---|
| Carga del panel | < 2 s | Se consulta en medio de un incendio |
| Retardo de detección | < 2 min desde que el proveedor lo publica | Marca la diferencia frente a mirar a mano |
| Disponibilidad del panel | Mayor que la de nuestra red | Es su razón de ser |
| Uso de red | 1 petición por fuente y minuto | Ser buen ciudadano; evitar bloqueos por tasa |
| Secretos | Variables de entorno, nunca en el repositorio | Hay credenciales de Entra ID y claves de API |
| Acceso | Solo lectura, sin cuentas de usuario en el MVP | El contenido no es sensible; añadir SSO en Fase 5 si se publica fuera |

## 8. Lo que este proyecto NO es

Delimitarlo por escrito evita el desvío de alcance, que es el riesgo número uno:

- ❌ No es una herramienta de monitorización de nuestras aplicaciones (eso es Zabbix,
  Grafana o lo que ya se use).
- ❌ No es un sistema de gestión de incidencias ni un tickets.
- ❌ No es una página de estado pública para clientes.
- ❌ No sustituye al soporte del proveedor: informa, no resuelve.
