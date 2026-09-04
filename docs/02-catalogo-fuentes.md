# 02 — Catálogo de fuentes de datos

> ⚠️ **Ninguna URL de este documento ha sido verificada en vivo.** El entorno donde se
> redactó el plan tiene bloqueada la salida a estos dominios por política de egreso
> (403 en el proxy). Las URLs se dan con su **nivel de confianza** y el primer
> entregable de la Fase 0 es ejecutar `scripts/check-sources.sh` y corregir esta tabla
> con lo que responda de verdad. **No se estima ninguna fase sobre estas URLs sin
> haberlas comprobado antes.**

Niveles de confianza: **Alta** = patrón estándar y estable · **Media** = correcto en su
momento, el proveedor puede haber migrado · **Baja** = hay que investigar.

## A. Patrón Statuspage (Atlassian) — el que más rendimiento da

Docenas de proveedores usan el mismo producto, así que **un solo adaptador** los cubre
todos. Sobre el dominio de la página de estado:

| Ruta | Devuelve |
|---|---|
| `/api/v2/status.json` | Indicador global (`none`/`minor`/`major`/`critical`) |
| `/api/v2/summary.json` | Estado global + componentes + incidencias abiertas (**la que usaremos**) |
| `/api/v2/components.json` | Desglose por componente (ej.: solo "Copilot") |
| `/api/v2/incidents.json` | Histórico de incidencias con sus actualizaciones |

Sin autenticación, sin clave, JSON estable y versionado. Un `GET` cada 60–120 s por
proveedor es un uso razonable.

| Servicio | Dominio de estado | Confianza | Nota |
|---|---|---|---|
| Anthropic / Claude | `status.anthropic.com` | Alta | |
| OpenAI / ChatGPT | `status.openai.com` | Media | Verificar si sigue en Statuspage |
| GitHub + **Copilot** | `www.githubstatus.com` | Alta | Copilot es un *componente*: filtrar por él |
| Cloudflare | `www.cloudflarestatus.com` | Alta | |
| Atlassian (Jira, Confluence) | `status.atlassian.com` | Alta | |
| Zoom | `status.zoom.us` | Alta | |
| Dropbox | `status.dropbox.com` | Media | |
| Twilio | `status.twilio.com` | Alta | |
| Salesforce | — | Baja | API propia (`api.status.salesforce.com`), no Statuspage |
| Slack | `slack-status.com/api/v2.0.0/current` | Media | **Formato propio**, no Statuspage |

> **Regla de oro:** antes de escribir un adaptador nuevo, probar
> `https://<dominio-status>/api/v2/summary.json`. Si responde, ya está hecho.

## B. Hiperescalares — formato propio, un adaptador cada uno

| Proveedor | Fuente | Tipo | Confianza | Nota |
|---|---|---|---|---|
| **Azure** (público) | Feed RSS del estado de Azure | RSS | Media | Global, no de nuestra suscripción |
| **Azure** (nuestro) | Azure Resource Health / Service Health vía ARM (`Microsoft.ResourceHealth`) | REST + OAuth | Alta | **Mucho mejor**: es *nuestra* suscripción. Requiere service principal con rol *Reader* |
| **Microsoft 365** | Microsoft Graph: `serviceAnnouncement/healthOverviews` e `issues` | REST + OAuth | Alta | **La joya**: estado real de *nuestro* tenant, Teams incluido. Requiere app en Entra ID con permiso de aplicación `ServiceHealth.Read.All` y consentimiento de administrador |
| **Google Cloud** | `status.cloud.google.com/incidents.json` | JSON | Media | Lista de incidencias, hay que derivar el estado actual |
| **Google Workspace** | Panel de estado de Workspace, `incidents.json` | JSON | Media | Mismo formato que GCP |
| **AWS** | Health Dashboard público + RSS por servicio | JSON/RSS | Media | La *AWS Health API* (nuestra cuenta) exige plan de soporte Business o Enterprise |

**Punto importante para la decisión:** el trabajo de montar la app de Entra ID para
Microsoft 365 (unas 2–3 h con permisos) da el dato de **más calidad de todo el
proyecto**, porque distingue "Teams está mal" de "Teams está mal *para nosotros*".
Es la primera integración no trivial que hay que hacer.

## C. Servicios de IA

| Servicio | Fuente | Confianza |
|---|---|---|
| Claude (Anthropic) | Statuspage — sección A | Alta |
| ChatGPT / API OpenAI | Statuspage — sección A | Media |
| GitHub Copilot | Componente de `githubstatus.com` | Alta |
| Microsoft 365 Copilot | Microsoft Graph — sección B | Alta |
| Google Gemini | Panel de estado de Google Cloud / Workspace | Baja |
| Otros (Mistral, Perplexity…) | Probar patrón Statuspage | Baja |

Para las APIs de IA que consumimos con clave propia, la señal más honesta no es la
página de estado, sino una **sonda sintética**: una llamada real y mínima cada N
minutos, midiendo latencia y errores. Detecta antes la degradación y detecta problemas
que solo nos afectan a nosotros (cuota agotada, clave caducada, límite de tasa).
Coste: céntimos al mes. **Recomendado para Claude y OpenAI desde la Fase 3.**

## D. Conectividad, telefonía y energía — aquí no hay feeds

| Necesidad | Lo que **no** funciona | Lo que sí funciona |
|---|---|---|
| ¿Se ha caído nuestra línea de internet? | Web del operador (sin API, HTML cambiante) | **Sonda propia**: ping/HTTP a varios destinos estables desde dentro de la red |
| ¿Es nuestro router o es el operador? | — | Sonda por saltos: gateway → DNS del operador → destino externo. El primer salto que falla identifica la capa |
| ¿Hay caída general del operador? | Scraping de Downdetector (prohibido por sus términos) | Correlación entre sedes + confirmación manual |
| ¿Cobertura móvil? | — | Estado manual, reportado por quien lo detecta |
| ¿Corte eléctrico? | Mapa web de la distribuidora (sin API) | Sensor del SAI/UPS por SNMP si es gestionable; si no, estado manual |

**Decisión de diseño:** todo lo de esta sección se modela como un servicio más, pero
con `tipo_fuente = sonda` o `tipo_fuente = manual`. La interfaz debe dejar clarísimo
cuál es cuál — un cuadro ámbar puesto a mano por un compañero es información valiosa,
pero no es lo mismo que un feed oficial y no puede parecerlo.

## E. Lo que queda descartado

| Fuente | Motivo |
|---|---|
| Downdetector (scraping) | Términos de servicio; su API es comercial y cara |
| Scraping de webs de operadoras y eléctricas | Frágil, se rompe en cada rediseño, dudoso legalmente |
| Cuentas de X/Twitter de proveedores | API de pago y contenido no estructurado |

## F. Plantilla para dar de alta un servicio nuevo

```yaml
- id: anthropic-claude
  nombre: "Claude (Anthropic)"
  categoria: ia
  criticidad: alta          # alta | media | baja -> ordena el panel
  fuentes:
    - tipo: statuspage
      url: "https://status.anthropic.com"
      componentes: ["API", "Claude.ai"]   # vacío = página completa
    - tipo: sonda_sintetica
      intervalo_s: 300
  responsable: "equipo-sistemas"
```
