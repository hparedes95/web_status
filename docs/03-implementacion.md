# 03 — Implementación

Está construido. Este documento describe cómo funciona lo que hay en el repositorio.

## Cómo funciona

No hay servidor. Todo vive dentro de GitHub.

```
   GitHub Actions (cada 10 min)                    GitHub Pages
   ┌────────────────────────────┐                 ┌──────────────────┐
   │ src/poller.py              │                 │ site/index.html  │
   │  1. lee las fuentes        │ ── despliega ──▶│ site/status.json │◀── navegador
   │  2. escribe status.json    │                 └──────────────────┘
   │  3. avisa por Telegram     │
   │  4. commit de estado.json  │
   └────────────────────────────┘
              ▲
              │ lee las incidencias marcadas a mano
     Issues con etiqueta `caida:<id>`
```

| Fichero | Qué hace |
|---|---|
| `services.yaml` | Los 10 indicadores y la regla de alerta. Añadir uno es editar aquí |
| `src/poller.py` | Lee las fuentes, normaliza, decide alertas y genera `site/status.json` |
| `site/index.html` | El panel. Página estática que recarga `status.json` cada minuto |
| `estado.json` | Estado anterior y el historial por horas de cada servicio. Lo escribe el workflow |
| `.github/workflows/status.yml` | El cron, el despliegue a Pages y el commit |
| `tests/test_poller.py` | Pruebas sin red: `python tests/test_poller.py` |

## La barra de 72 horas

Cada fila del panel lleva una barra con las últimas 72 horas, una casilla por hora. Sale de
un campo de texto en `estado.json`: una letra por hora (`o` operativo, `d` degradado,
`c` caído, `u` ilegible, `-` sin registro). Siete días ocupan 168 caracteres por servicio,
así que el historial completo son unos pocos KB.

Dos decisiones sobre ese dato:

- **Dentro de una misma hora se guarda la peor lectura.** Una caída de diez minutos no puede
  desaparecer porque las cinco lecturas siguientes fueran buenas.
- **El porcentaje de disponibilidad ignora las horas ilegibles y las que no se registraron.**
  Contarlas como caída convertiría un adaptador roto en una supuesta indisponibilidad del
  proveedor. El hueco sigue siendo visible: en la barra sale en gris y la fila queda marcada
  como «sin datos», que es donde corresponde.

## Estados

Cada proveedor nombra sus averías a su manera; el adaptador traduce a cuatro:

| Estado | Color | Significa |
|---|---|---|
| `operativo` | 🟢 | Nada que reportar |
| `degradado` | 🟡 | Problema parcial, rendimiento degradado o mantenimiento |
| `caido` | 🔴 | Caída declarada |
| `desconocido` | ⚪ | No se pudo leer la fuente |

Dos decisiones deliberadas:

- **`desconocido` se pinta en pantalla**, y cada tarjeta muestra desde cuándo. Un adaptador
  roto en silencio que deja todo en verde es el único fallo grave que puede tener un panel
  así, y por eso ningún camino del código devuelve `operativo` sin haber leído la fuente.
- **Ningún adaptador lanza excepción.** Si una fuente falla, esa luz se pone en blanco y el
  resto del ciclo continúa.

## Adaptadores

| Tipo | Sirve para | Cómo decide |
|---|---|---|
| `statuspage` | Claude, ChatGPT, GitHub, Copilot | `/api/v2/summary.json`. Con `componentes`, filtra y se queda con el peor; sin ellos, usa el indicador global |
| `rss` | Azure, Microsoft 365 | Un RSS publica *eventos*, no estado. Si hay entradas recientes que mencionen nuestras regiones → `degradado`. Es una señal gruesa, y por eso el panel siempre enlaza a la página oficial |
| `json` | AWS | Health Dashboard público. Formato no documentado como API estable, así que se lee de forma defensiva: lo que no encaje devuelve `desconocido` |
| `manual` | Telefónica, Vodafone, energía | Issues abiertas con la etiqueta `caida:<id>` |

GitHub y GitHub Copilot salen de **la misma petición**, filtrando por componente: dos luces
independientes, para que una avería de Copilot no apague la luz de GitHub ni al revés.

## El estado manual

Para encender una de las tres luces sin feed, se abre una issue con la etiqueta
`caida:telefonica`, `caida:vodafone` o `caida:energia`. Al cerrarla, la luz vuelve a verde.

- El autor y la hora salen de la propia issue: el panel muestra «marcado por @alguien».
- El workflow también se dispara al abrir, cerrar o etiquetar una issue, así que **el panel
  se actualiza al momento**, sin esperar al siguiente ciclo.
- En un repositorio público cualquiera puede abrir una issue, pero **solo quien tiene
  permiso de escritura puede poner etiquetas**. Nadie de fuera puede encender una luz.

## La alerta

Por Telegram, con una sola regla deliberadamente estrecha:

- Se avisa **al pasar a `caido`**, nunca a `degradado`, `mantenimiento` ni `desconocido`.
- **Antirrebote:** hacen falta dos lecturas seguidas en rojo (~20 min) antes de avisar.
- **Un aviso por incidencia**, no uno por ciclo.
- **Aviso de recuperación** con la duración: «🟢 Azure operativo tras 34 min».
- Solo para los servicios con `alerta: true` en `services.yaml`. Hoy: Microsoft 365, Azure
  y AWS.

Las credenciales (`TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`) van en los secretos del
repositorio. **Nunca en el código: el repositorio es público.**

> Ampliar las alertas es cambiar un `false` por un `true`. Recuperar la atención de un
> canal que la gente ya ha silenciado, no. Si en un mes alguien echa algo en falta, se añade.

## Detalles del ciclo

- **Cadencia: cada 10 minutos.** El cron de Actions no es puntual —con carga se retrasa—,
  así que la cadencia real es de 10 a 20 min. Los minutos son gratis porque el repositorio
  es público; si algún día pasa a privado, hay que subir el intervalo a 30 min para caber
  en el plan gratuito.
- **`estado.json` se commitea solo cuando cambia algo.** Como incluye el historial por
  horas, eso son unos 24 commits al día. No es ruido gratuito: mantiene vivo el repositorio,
  y GitHub desactiva los workflows programados tras 60 días sin actividad.
- El `concurrency` del workflow evita que dos ciclos se pisen al escribir o al desplegar.

## Mantenimiento

**1–2 h/mes.** Los proveedores cambian sus feeds sin avisar. Cuando eso pasa, la luz se
pone en blanco (`desconocido`) en lugar de mentir: esa es la señal de que hay que mirar el
adaptador. Conviene que alguien tenga esa media hora reconocida en su carga.
