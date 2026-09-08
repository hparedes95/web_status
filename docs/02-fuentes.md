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
| Google Gemini | Paneles de Google Cloud y Workspace | ✅ Lista de incidencias en JSON |
| Cloudflare España | `www.cloudflarestatus.com`, componentes MAD y BCN | ✅ Ambos operativos |
| Microsoft 365 | — | ❌ **No existe feed público** |

## Cloudflare: el indicador global no vale

Cloudflare publica **479 componentes** en formato Statuspage, y **343 son centros de
datos**. Eso rompe el uso normal de la fuente: el indicador global de la página está casi
siempre en ámbar porque siempre hay algún centro en obras en algún sitio. En la
comprobación del 8-9-2026, con todo dentro de lo normal, había a la vez quince en avería
parcial o mantenimiento — Izmir, Basra, Nayaf, Jacksonville, Guam, Arica…

Tomar esa señal como propia sería tener una luz permanentemente encendida que no significa
nada. Y filtrar por el grupo entero de productos (128 componentes) tampoco sirve: en esa
misma comprobación había cuatro degradados (Browser Isolation, Dashboard, Gateway, WARP).

Así que la luz mira **solo los emplazamientos españoles**, que son los que sirven el
tráfico de aquí:

| Componente | Verificado |
|---|---|
| `Madrid, Spain - (MAD)` | ✅ |
| `Barcelona, Spain - (BCN)` | ✅ |

No hay más. Se revisaron uno a uno los 58 componentes del grupo *Europe* y los 34 de
*Africa* — donde estarían las Canarias si existieran — y no aparece ningún otro
emplazamiento español.

**Las incidencias también se filtran**, no solo los componentes. Cloudflare casi siempre
tiene alguna abierta en alguna parte del mundo; listarlas bajo una luz que solo mira España
sería dar por nuestro un problema ajeno. El adaptador se quedó solo con las que tocan un
componente de los elegidos, y eso beneficia igualmente a GitHub y Copilot.

**Sin alerta de Telegram, a propósito.** Cuando cae un centro, Cloudflare desvía el tráfico
a los vecinos (Lisboa, Marsella, París): se nota en latencia más que en caída. Es
información útil para entender una lentitud, no un motivo para sonar de madrugada. Cambiar
`alerta` a `true` en `services.yaml` si preferís enteraros igualmente.

## Google: dos paneles para un mismo producto

Google publica `incidents.json` en dos sitios, con el mismo formato: el panel de Cloud y el
de Workspace. **Gemini aparece en ambos** —en Workspace como aplicación, en Cloud como API
de Vertex AI—, así que se consultan los dos y manda la peor señal. Si uno falla, el otro
sigue dando dato.

Dos detalles del formato: una incidencia está abierta cuando el campo `end` viene vacío, y
el filtro por producto es por subcadena y sin distinguir mayúsculas, que aguanta mejor los
cambios de marca de Google. Además se ignoran las incidencias abiertas que no se tocan
desde hace más de 48 horas: casi siempre son avisos que a Google se le olvidó cerrar.

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

## Energía: sí hay fuente, pero es nacional

`apidatos.ree.es` es la **API pública y documentada de Red Eléctrica de España**. No es
scraping. Publica la demanda nacional en tiempo real; comprobado: HTTP 200, JSON, dato de
hace minutos.

**Qué ve.** La red nacional. Un apagón peninsular como el de abril de 2025 aparece aquí en
minutos, porque la demanda se desploma. El adaptador avisa si cae más de un 30 % en una
hora — la curva normal día/noche no se mueve así ni de lejos, de ahí el umbral.

**Qué no ve.** Un corte en vuestra calle, en vuestro edificio o en vuestro polígono. Para
eso **no existe fuente pública**, y no es por no buscar:

| Probado | Resultado |
|---|---|
| `edistribucion.com` y su mapa de cortes | Sitio AEM; las rutas evidentes dan 404 y no expone API |
| `edistribucion.com/es/red-electrica/Corte_luz.html` | 404 |
| Endesa como comercializadora | No tiene red: los cortes son de la distribuidora |

Además, en parte del Pirineo de Lleida la distribuidora ni siquiera es e-distribución, así
que «¿está Endesa activo en Lleida?» no es una pregunta con una sola respuesta.

## Operadores móviles: no hay nada

Se ha buscado, y el resultado es concluyente:

Nueve URLs probadas, en dos tandas, **con y sin cabeceras de navegador**:

| Probado | Sin navegador | Imitando un navegador |
|---|---|---|
| `movistar.es` | SPA de Next.js, sin endpoint de estado | — |
| `movistar.es/particulares/atencion-cliente/averias` | 404 | **404** |
| `movistar.es/_next/data/<build>/…/averias.json` | — | **404** |
| `ayuda.vodafone.es/particulares/averias` | Error TLS | — |
| `ayuda.vodafone.es/` | — | **Mismo error TLS** |
| `vodafone.es/c/particulares/es/atencion-al-cliente/averias/` | — | **404** |
| `telefonica.com/es/sala-comunicacion/` | — | 200, pero es la sala de prensa |

La segunda tanda existe porque estas webs suelen bloquear a los clientes que no
parecen un navegador, y sin comprobarlo el descarte no era concluyente. **Lo es:** el
comportamiento es idéntico con cabeceras de navegador. No es que nos bloqueen, es que
esas páginas no existen.

Ni Movistar ni Vodafone publican estado por zona. Sus páginas de averías van tras login y
atadas a una línea concreta.

**Tampoco vale una sonda remota.** Se podría comprobar desde el runner si responden sus DNS
públicos, pero eso no dice nada útil: una caída de cobertura móvil en Lleida no afecta a la
infraestructura pública de Telefónica, y un fallo de rutado desde GitHub daría un rojo
falso. Sería una luz que parece informar y no informa — justo lo que este panel evita.

Por eso esos dos indicadores **se quedan en manual**, y la fila lo dice: «Sin fuente
pública: se marca a mano».

Para que lo manual no se quede en buena intención, cada fila sin fuente lleva un enlace
**«marcar avería»** que abre la issue ya etiquetada. Con la avería encima, nadie se acuerda
de abrir una issue, escribir el título y elegir la etiqueta: si no es un clic, no se hace,
y la luz se queda en verde mintiendo.

## Lo que se descartó, y por qué

| Fuente | Motivo |
|---|---|
| **Downdetector** | Sus términos prohíben el scraping y su API es comercial. Además mide *gente quejándose*, no el estado del servicio: da falsos positivos |
| Agregadores comerciales (StatusGator, IsDown…) | De pago, y agregan la misma página que ya no da datos |
| El bundle JavaScript del panel de Microsoft | Endpoint no documentado, con hash que cambia en cada despliegue |
| Scraping de webs de operadoras y distribuidoras | Frágil y contrario a sus términos |
| Sonda remota a los DNS de los operadores | Verde que no significa nada: no ve la cobertura móvil |

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
