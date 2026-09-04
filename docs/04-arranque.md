# 04 — Qué hace falta para empezar

## Lista de arranque

Seis puntos. Los dos primeros bloquean; el resto se puede resolver sobre la marcha.

| # | Qué | Quién | Bloquea |
|---|---|---|---|
| 1 | **Ejecutar `./scripts/check-sources.sh`** y anotar qué responde | Cualquiera con salida a internet | Sí — la estimación no vale hasta saber esto |
| 2 | **Decidir dónde se aloja** (ver abajo) | Tú | Sí — cambia cómo se construye |
| 3 | **Decidir Microsoft 365**: feed público o Microsoft Graph | Tú | No, pero si es Graph hay que pedir el permiso ya |
| 4 | **Crear el webhook entrante de Teams** en el canal que reciba los avisos | Quien administre el canal | No, se añade al final |
| 5 | **Confirmar las regiones** de Azure y AWS que os afectan | Sistemas | No, hay un valor por defecto |
| 6 | **Asignar quién lo mantiene** (1–2 h/mes) | Tú | No, pero sin dueño el panel deja de ser fiable en unos meses |

Nada de esto es trabajo de desarrollo: es media mañana de decisiones. El punto 1 es el
único que puede cambiar el plan, porque si alguna fuente resulta no existir hay que buscar
alternativa.

## La decisión de alojamiento

Sí, **se puede construir y alojar entero dentro de GitHub**, sin servidor. Son dos
arquitecturas distintas y la elección condiciona el resto.

### Opción A — Todo en GitHub

```
  GitHub Actions (cron)                     GitHub Pages
  ┌──────────────────────┐                 ┌─────────────────┐
  │ 1. lee los feeds     │                 │ index.html      │
  │ 2. escribe status.json│ ──── commit ──▶ │ status.json     │ ◀── navegador
  │ 3. avisa a Teams     │                 └─────────────────┘
  └──────────────────────┘
            ▲
            │  lee las incidencias manuales
      GitHub Issues con etiqueta `caida:*`
```

- **El panel** es una página estática que lee `status.json`. Sin servidor, sin base de datos.
- **El histórico** sale gratis: cada ejecución hace *commit*, y el historial de git *es* el
  registro de cambios.
- **El botón manual** se sustituye por **issues etiquetadas**: alguien abre una issue con la
  etiqueta `caida:vodafone` y esa luz se pone en rojo; al cerrarla, vuelve a verde. El autor
  y la hora vienen dados, se puede hacer desde el móvil y queda el hilo de conversación.
- **La alerta** la manda el propio workflow al webhook de Teams, con la URL en los secretos
  del repositorio.

**Lo que hay que saber antes de elegirla** (verificar los tres puntos, son condiciones de
GitHub que cambian con el tiempo y con vuestro plan):

| Límite | Consecuencia |
|---|---|
| **El cron de Actions no es puntual.** El intervalo mínimo es de 5 min y las ejecuciones se retrasan cuando hay carga | El retardo de detección pasa de ~2 min a **10–20 min**, que se suman a los 10–45 min que tarda el proveedor en reconocer la caída |
| **Minutos de Actions en repositorio privado.** El plan gratuito da 2.000 min/mes y se factura redondeando al minuto por ejecución | Una ejecución cada 30 min ≈ 1.440 min/mes y cabe. Cada 15 min ≈ 2.880 min/mes y **no cabe** en el plan gratuito |
| **GitHub Pages en repositorio privado publica un sitio público**, salvo con Enterprise Cloud | El panel sería visible desde internet: no muestra datos internos, pero sí **qué proveedores usáis** |
| **Los workflows programados se desactivan solos tras 60 días sin actividad** en el repositorio | Hay que comprobar si los *commits* del propio workflow cuentan como actividad; si no, se desactivaría solo |

### Opción B — Un contenedor en un VPS

Lo del plan original: un proceso con su poller, su SQLite y su página.

| | **A · GitHub** | **B · VPS** |
|---|---|---|
| Coste | 0 € | ~5 €/mes |
| Servidor que mantener | Ninguno | Uno |
| Cadencia realista | 15–30 min | 2 min |
| Privacidad del panel | Público (salvo Enterprise) | Privado |
| Estado manual | Issues etiquetadas | Un botón |
| Trabajo | ~4,5 días | ~5 días |
| Fuera de nuestra red | ✅ | ✅ |

### Recomendación

**Si el panel puede ser público, opción A.** No muestra nada confidencial —son estados de
proveedores que ya son públicos uno a uno— y a cambio elimina el servidor, el coste y el
despliegue. La cadencia de 15–30 min es aceptable porque el cuello de botella real no es el
sondeo, sino que el proveedor tarda hasta 45 min en reconocer la avería.

**Si tiene que ser privado, opción B.** Cinco euros al mes y control total.

Lo que sí desaconsejo es empezar por B «por si acaso»: A se monta en menos tiempo y, si
algún día no llega, migrar el poller a un contenedor es reaprovechar casi todo el código.

## Y sí, el desarrollo también se lanza desde GitHub

Independientemente de dónde se aloje: el trabajo se hace en este repositorio, en la rama
`claude/service-status-monitor-planner-un9nz5`, y se puede arrancar desde una issue o desde
`claude.ai/code` apuntando aquí.
