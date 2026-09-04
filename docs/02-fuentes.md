# 02 — Fuentes de datos

> ✅ **Verificado en ejecución real** el 4 de septiembre de 2026, con el workflow
> «Comprobar fuentes» y el primer ciclo del panel. Lo que sigue no son suposiciones.

## Resultado de la comprobación

| Servicio | Fuente | Resultado |
|---|---|---|
| Claude | `status.anthropic.com` (Statuspage) | ✅ `All Systems Operational` |
| ChatGPT | `status.openai.com` (Statuspage) | ✅ `All Systems Operational` |
| GitHub | `www.githubstatus.com`, componentes propios | ✅ Todos los componentes operativos |
| GitHub Copilot | `www.githubstatus.com`, componente *Copilot* | ✅ Operativo |
| Azure | RSS de estado de Azure | ✅ Feed válido, sin avisos |
| AWS | Health Dashboard público | ✅ Operativo, **tras dos correcciones** |
| Microsoft 365 | — | ❌ **No existe feed público** |

## Las dos correcciones que hizo falta hacer

**AWS servía UTF-16, no UTF-8.** El feed llega con
`Content-Type: application/json;charset=utf-16` y marca de orden de bytes `FE FF`.
Darlo por UTF-8 rompía la lectura con un error de codificación. Ahora se respeta la BOM.

**El feed de AWS trae el histórico completo**, no solo lo que está pasando ahora: son
233 KB de eventos pasados. El filtro original, por coincidencia de texto con la región,
habría marcado la región como degradada de forma permanente. Ahora manda una ventana
temporal de 6 horas.

## Microsoft 365: no hay feed público, punto

Se probaron cuatro URLs candidatas. Todas devuelven **la página web del panel**, no un feed:

| URL probada | Qué devuelve |
|---|---|
| `status.cloud.microsoft/api/feed` | HTML (`<!doctype html>`), 0 entradas |
| `status.cloud.microsoft/rss` | El mismo HTML |
| `status.office365.com/api/feed` | Redirige a la anterior |
| `portal.office.com/servicestatus/rss` | «There was a problem processing your request» |

También se probaron las rutas de API que usa la propia página: `\/api\/status`,
`\/api\/v2\/status`, `\/api\/servicestatus`. **Todas devuelven el mismo HTML**, porque es
una ruta comodín: los datos salen de un bundle JavaScript minificado y con hash en el
nombre. Destriparlo daría un endpoint no documentado que cambia con cada despliegue —
la misma fragilidad que hizo descartar el scraping de Downdetector, solo que con mejor
aspecto. Descartado por el mismo motivo.

La conclusión es firme: **la única fuente oficial para Microsoft 365 es Microsoft Graph.** Eso
tiene una ventaja, además: Graph da el estado de *nuestro* tenant, no el global, que es
mejor dato que el que dan todos los demás proveedores del panel.

Requiere una aplicación en Entra ID con el permiso de aplicación `ServiceHealth.Read.All`
y consentimiento de administrador. El adaptador ya está escrito y probado.

### Mientras tanto: sonda propia

Sin esas credenciales, el indicador cae a una **comprobación propia** contra endpoints de
Microsoft públicos, documentados y estables:

| Endpoint | Verificado |
|---|---|
| `login.microsoftonline.com/common/discovery/keys` | ✅ HTTP 200, JSON |
| `graph.microsoft.com/v1.0/$metadata` | — |

**Qué detecta y qué no.** Detecta una caída total del inicio de sesión, que es la avería
más grave que puede tener Microsoft 365. **No** ve que Teams vaya lento o que Exchange
tenga colas. Por eso la fila del panel lleva la etiqueta **`sonda`** y el mensaje dice
que no es el estado oficial: un verde ahí significa «responde», no «todo bien».

Si la sonda no consigue llegar, el estado es `desconocido`, no `caído`: desde un único
punto de observación no se puede distinguir «Microsoft está caído» de «no llegamos a
Microsoft», y dar por caído lo segundo dispararía una alerta falsa.

## Lo que se descartó, y por qué

| Fuente | Motivo |
|---|---|
| **Downdetector** | Sus términos prohíben el scraping y su API es comercial. Además mide *gente quejándose*, no el estado del servicio: da falsos positivos |
| Agregadores comerciales (StatusGator, IsDown…) | De pago, y agregan la misma página que ya no da datos |
| El bundle JavaScript del panel de Microsoft | Endpoint no documentado, con hash que cambia en cada despliegue |
| Scraping de webs de operadoras y distribuidoras | Frágil y contrario a sus términos |

## Sin fuente posible: botón manual

Telefónica/Movistar, Vodafone y suministro eléctrico. No hay API de operadoras ni de
distribuidoras, y el *scraping* de sus webs queda descartado: frágil y contrario a sus
términos de servicio.

Se marcan abriendo una issue con la etiqueta `caida:<id>` y se apagan al cerrarla.

## Cuando una fuente deje de funcionar

Pasará: los proveedores cambian sus feeds sin avisar. La luz se pondrá en blanco
(`desconocido`), que es la señal. Para averiguar la URL nueva sin ir a ciegas:

**Actions → Comprobar fuentes → Run workflow**, con las URLs candidatas separadas por
espacios. Dice de cada una el código HTTP, el tipo de contenido, los primeros bytes y
cuántas entradas saca `feedparser`. Es exactamente la herramienta con la que se resolvió
lo de AWS y lo de Microsoft 365.
