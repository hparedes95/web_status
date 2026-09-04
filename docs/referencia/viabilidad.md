# 01 — Análisis de viabilidad

## 1. El problema real

El problema no es "no saber si Azure está caído". El problema es el **tiempo que se
pierde en el minuto 1 de una incidencia** decidiendo si el fallo es nuestro o del
proveedor. Ese minuto se repite varias veces por semana y consume tiempo de varias
personas a la vez.

La aplicación debe responder, en una sola pantalla:

1. ¿Hay algo caído ahora mismo que nos afecte?
2. ¿Es del proveedor o es nuestro? (feed oficial vs. sonda propia)
3. ¿Desde cuándo y qué dice el proveedor?
4. ¿Nos ha pasado esto antes con este servicio? (histórico)

Si el proyecto no responde a la 2, aporta poco: eso ya lo da una pestaña de
favoritos. **La combinación feed oficial + sonda propia es el valor diferencial.**

## 2. Viabilidad por familia de servicio

Semáforo de dificultad: 🟢 trivial · 🟡 asumible · 🟠 costoso · 🔴 no resoluble con feeds

| Familia | Ejemplos | Fuente disponible | Dificultad | Fiabilidad del dato |
|---|---|---|---|---|
| SaaS con Statuspage | Anthropic, OpenAI, GitHub/Copilot, Cloudflare, Atlassian, Zoom | JSON público estándar `/api/v2/summary.json` | 🟢 | Alta |
| Hiperescalares | Azure, AWS, GCP | RSS / JSON públicos, formato propio de cada uno | 🟡 | Alta |
| Microsoft 365 (nuestro tenant) | Teams, Exchange, SharePoint | Microsoft Graph `serviceAnnouncement` (requiere app en Entra ID) | 🟡 | **Muy alta** (es nuestro tenant, no el global) |
| SaaS sin Statuspage | Herramientas de nicho, ERPs verticales | Página HTML, a veces RSS | 🟠 | Media |
| Conectividad (ISP, fibra, MPLS) | Movistar, Vodafone, Orange, Digi | No hay API pública fiable | 🔴 → sonda propia | — |
| Telefonía móvil | Cualquier operador | No hay API pública | 🔴 → sonda propia / manual | — |
| Energía | Distribuidora eléctrica | Mapas de incidencias web, sin API | 🔴 → sensor propio (UPS/SAI) o manual | — |

**Conclusión:** el catálogo se parte en dos mitades con soluciones distintas.
Todo lo que es *cloud y SaaS* se resuelve leyendo feeds. Todo lo que es
*infraestructura física* (línea, móvil, luz) **no se resuelve leyendo feeds**: se
resuelve midiendo desde dentro. Intentar cubrir la segunda mitad con scraping de
Downdetector o de webs de operadoras es la vía rápida a un proyecto que da datos
falsos y viola términos de servicio.

## 3. La trampa clásica: las páginas de estado mienten

Hay que asumirlo desde el diseño, no descubrirlo en producción:

- **Llegan tarde.** Un proveedor tarda entre 10 y 45 minutos en reconocer una caída.
  Durante ese rato su semáforo está en verde y nuestros usuarios ya están afectados.
- **Son globales, no nuestras.** "Azure operativo" puede convivir con "nuestra región
  degradada". Por eso Microsoft 365 vía Graph (que sí es de nuestro tenant) vale más
  que cualquier página pública.
- **Minimizan.** "Degradación del rendimiento en un subconjunto de usuarios" suele
  significar caída para quien la sufre.

**Mitigación de diseño:** cada servicio tiene hasta tres señales — feed oficial,
sonda propia y reporte manual de un compañero — y la interfaz muestra **la peor de
las tres**, indicando cuál manda. Un servicio en verde oficial pero con sonda roja
se pinta en ámbar con el texto "el proveedor aún no lo reconoce".

## 4. Construir vs. comprar

| Opción | Coste | Cubre nuestro caso | Veredicto |
|---|---|---|---|
| **Comprar** (IsDown, StatusGator y similares) | ~30–100 €/mes por equipo | Agrega cientos de páginas de estado. **No** hace sondas dentro de nuestra red, no ve nuestro tenant de M365, no cubre ISP ni energía | Resuelve la mitad fácil, que es justo la que es barata de construir |
| **Uptime Kuma / Gatus (open source)** | Hosting (~5–10 €/mes) | Excelente en sondas propias. **No** agrega páginas de estado de terceros | Resuelve la mitad difícil. Candidato serio como pieza, no como solución completa |
| **Construir a medida** | ~20–30 días persona + hosting | Cubre las dos mitades y el catálogo exacto nuestro | Recomendado, con reservas (ver abajo) |
| **No hacer nada** | 0 € | — | El coste está oculto: es tiempo de diagnóstico repetido |

### Recomendación

**Construir, pero apoyándose en lo que ya existe y con una puerta de salida en la Fase 1.**

- La agregación de páginas de estado tipo Statuspage es **un adaptador de 100 líneas**
  que cubre docenas de proveedores. Construirla es más barato que la primera factura
  anual de una herramienta comercial.
- Las sondas de red **no las inventamos**: si en la Fase 3 el esfuerzo se dispara,
  se despliega Uptime Kuma al lado y nuestra app consume su API. Esto está
  contemplado en la arquitectura.
- **Puerta de salida:** si al terminar la Fase 1 (MVP, ~2 semanas) el panel no se
  está mirando a diario, se para el proyecto. Se habrán gastado dos semanas, no dos
  meses.

## 5. Esfuerzo y coste estimados

| Concepto | Estimación |
|---|---|
| Desarrollo hasta producto útil (Fases 0–3) | 12–18 días persona |
| Desarrollo hasta producto completo (Fases 0–5) | 20–30 días persona |
| Calendario realista a media jornada | 6–10 semanas |
| Hosting | 5–25 €/mes (o 0 € sobre infraestructura existente) |
| Mantenimiento en régimen | ~2–4 h/mes (adaptadores que cambian) |

La partida de **mantenimiento no es opcional**: los proveedores cambian sus feeds sin
avisar. Un proyecto de este tipo sin dueño asignado deja de ser fiable en unos meses,
y un panel en el que no se confía es peor que no tener panel.

## 6. Veredicto

**Viable y recomendable, con el alcance bien recortado.**

- ✅ Adelante con cloud, IA y SaaS mediante feeds oficiales.
- ✅ Adelante con conectividad propia mediante sondas.
- ⚠️ Energía y telefonía móvil: entran como **estado manual** (un botón para marcar
  "incidencia conocida") y, si hay SAI gestionable, como sensor. No prometer detección
  automática.
- ❌ Descartado el scraping de Downdetector y de webs de operadoras: términos de
  servicio y fragilidad.
