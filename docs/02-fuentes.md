# 02 — Fuentes de datos

> ⚠️ **Ninguna URL está verificada.** El entorno donde se redactó tiene bloqueada la salida
> a estos dominios. **Antes de desarrollar, ejecutar `./scripts/check-sources.sh`** y
> corregir esta tabla con lo que responda de verdad.

## Grupo 1 — Página de estado estándar (Statuspage)

Tres de los seis servicios automáticos usan el mismo producto, así que **un solo adaptador
los cubre**. Sobre el dominio de la página, la ruta `/api/v2/summary.json` devuelve estado
global, componentes e incidencias abiertas. Sin autenticación ni claves.

| Servicio | Dominio | Confianza | Nota |
|---|---|---|---|
| Claude (Anthropic) | `status.anthropic.com` | Alta | |
| ChatGPT / OpenAI | `status.openai.com` | Media | Verificar si sigue en Statuspage |
| GitHub Copilot | `www.githubstatus.com` | Alta | Filtrar por el componente *Copilot*, para que no se ponga rojo si falla otra cosa de GitHub |

Este grupo es medio día de trabajo y da tres de las nueve luces.

## Grupo 2 — Formato propio

| Servicio | Fuente | Tipo | Confianza |
|---|---|---|---|
| Azure | Feed RSS del estado de Azure | RSS | Media |
| AWS | Health Dashboard público | JSON | Media |
| Microsoft 365 | Feed público de estado | RSS | **Baja — ver abajo** |

## Microsoft 365: la única decisión técnica que queda

Es el servicio más importante del panel y el que peor fuente pública tiene. Hay dos vías:

| | **A · Feed público** | **B · Microsoft Graph** |
|---|---|---|
| Credenciales | Ninguna | App en Entra ID con `ServiceHealth.Read.All` y consentimiento de administrador |
| Qué da | Estado global de Microsoft | Estado de **nuestro tenant** |
| Trabajo | 0,5 d | 1 d + 2–3 h de trámite |
| Plazo | Inmediato | Depende de quién apruebe el consentimiento |
| Riesgo | La fuente puede no existir o cambiar | Ninguno, es una API estable y documentada |

**Recomendación:** empezar por **A** y comprobarlo con el script. Si el feed público no
responde o resulta inservible, pasar a **B**, que es la vía sólida. Si se opta por B, pedir
el permiso el primer día: el trámite no depende de nosotros.

Mientras tanto, el panel funciona con los otros ocho indicadores.

## Sin fuente: botón manual

Telefónica/Movistar, Vodafone y suministro eléctrico. No hay API y el *scraping* de las
webs de operadoras y distribuidoras queda descartado (frágil y contrario a sus términos de
servicio).

El botón guarda **quién lo marcó y cuándo**, y el panel muestra «marcado por Juan hace
40 min». Eso es lo que evita que cinco personas llamen al mismo soporte.
