# 03 — Implementación

## Cómo funciona

Un único proceso. No hay agentes, ni colas, ni servidor de base de datos.

```
  Feeds de los proveedores
           │  (cada 2 min)
           ▼
   ┌───────────────────┐
   │  Poller           │  lee, normaliza y guarda solo los CAMBIOS de estado
   ├───────────────────┤
   │  SQLite           │  un fichero
   ├───────────────────┤
   │  Web + API        │  la pantalla, con autorefresco
   ├───────────────────┤
   │  Alerta           │  webhook a Teams cuando algo pasa a rojo
   └───────────────────┘
           ▲
           │  botón manual (telefonía, energía)
        persona
```

**Alojarlo fuera de la red que vigila** (VPS de ~5 €/mes o el contenedor que ya se use).
Si vive en la oficina, se cae justo el día que hace falta.

## Pila

| Capa | Elección |
|---|---|
| Lenguaje | Python 3.12 con `httpx` y `feedparser` |
| Web y API | FastAPI |
| Planificación | APScheduler, en el mismo proceso |
| Datos | SQLite |
| Pantalla | HTML + HTMX, sin framework |
| Despliegue | Un contenedor Docker |

## Estados

Cada proveedor nombra sus averías a su manera; el adaptador traduce a cuatro:

| Estado | Color | Significa |
|---|---|---|
| `operativo` | 🟢 | Nada que reportar |
| `degradado` | 🟡 | Problema parcial o rendimiento degradado |
| `caido` | 🔴 | Caída declarada |
| `desconocido` | ⚪ | No se pudo leer la fuente |

`desconocido` **se pinta en pantalla**, y cada tarjeta muestra la antigüedad del dato
(«hace 2 min»). Un adaptador roto en silencio que deja todo en verde es el único fallo
grave que puede tener un sistema así.

## La alerta

Una sola regla, deliberadamente estrecha:

- Se avisa **al pasar a rojo**, nunca al pasar a amarillo.
- **Antirrebote:** hacen falta dos lecturas seguidas en rojo (unos 4 minutos) para evitar
  avisar de un fallo puntual de red.
- **Un aviso por incidencia**, no uno por ciclo.
- **Aviso de recuperación**, con la duración: «Azure operativo tras 34 min».
- **No se avisa** de mantenimientos programados ni de `desconocido`.
- Canal: webhook entrante de Teams. Correo SMTP como alternativa.

> Ampliar esto es fácil; recuperar la atención de un canal que la gente ha silenciado, no.
> Si en un mes alguien echa algo en falta, se añade.

## Tareas

| # | Tarea | Días |
|---|---|---|
| 1 | Verificar las fuentes con `./scripts/check-sources.sh` y corregir `02-fuentes.md` | 0,25 |
| 2 | Esqueleto: FastAPI, SQLite, carga de `services.yaml`, poller | 1 |
| 3 | Adaptador Statuspage → Claude, ChatGPT, Copilot | 0,5 |
| 4 | Adaptadores RSS y JSON → Azure, AWS, Microsoft 365 | 1 |
| 5 | Pantalla: rejilla de luces, antigüedad del dato, enlace a la página oficial | 1 |
| 6 | Botón de estado manual, con autor y hora | 0,5 |
| 7 | Alerta a Teams con las reglas de arriba | 0,5 |
| 8 | Docker y despliegue | 0,5 |
|  | **Total** | **~5 días** |

Si Microsoft 365 acaba yendo por Microsoft Graph (opción B de [`02-fuentes.md`](02-fuentes.md)),
sumar 1 día y el trámite del permiso.

## Mantenimiento

**1–2 h/mes.** Los proveedores cambian sus feeds sin avisar. Cada adaptador degrada a
`desconocido` en lugar de tumbar el proceso, y esa luz blanca es la señal de que algo hay
que arreglar. Conviene que alguien tenga esa media hora reconocida en su carga.
