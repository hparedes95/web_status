# 04 — Plan por fases

Estimación en **días persona** (jornadas efectivas de trabajo, no de calendario). A
media jornada, multiplicar por dos para obtener el calendario.

Cada fase termina en algo **usable**. No hay fase cuyo entregable sea "infraestructura
preparada": si el proyecto se para al terminar cualquier fase, lo construido sigue
sirviendo para algo.

---

## Fase 0 — Validación · 2–3 días

**Objetivo:** saber si el plan se sostiene antes de escribir la aplicación.

| # | Tarea | Días |
|---|---|---|
| 0.1 | Inventario cerrado de servicios con criticidad y responsable | 0,5 |
| 0.2 | Ejecutar `scripts/check-sources.sh` y **corregir el catálogo con lo que responda de verdad** | 0,5 |
| 0.3 | Prueba de concepto: leer y normalizar 3 fuentes distintas (Statuspage, RSS de Azure, JSON de GCP) en un script suelto | 1 |
| 0.4 | Solicitar el registro de aplicación en Entra ID (permiso `ServiceHealth.Read.All`) — **lanzarlo ya, el consentimiento de administrador tarda** | 0,5 |

**Criterio de salida:** ≥ 80 % de las fuentes del inventario responden y devuelven un
estado legible. Si no se cumple, se replantea el alcance antes de seguir.

> ⚠️ 0.4 es la tarea con más plazo externo de todo el proyecto. Depende de terceros
> (administración de Entra ID) y bloquea la Fase 2. **Lanzarla el primer día.**

---

## Fase 1 — MVP usable · 5–8 días

**Objetivo:** una pantalla que se pueda dejar abierta y que ya ahorre tiempo.

| # | Tarea | Días |
|---|---|---|
| 1.1 | Esqueleto: FastAPI + SQLite + modelo de datos + `services.yaml` | 1 |
| 1.2 | Adaptador **Statuspage** genérico + normalización de estados | 1 |
| 1.3 | Poller con APScheduler, tolerante a fallos, registrando transiciones | 1 |
| 1.4 | Panel: rejilla por categoría, semáforo, autorefresco, enlace a la página oficial | 2 |
| 1.5 | Vista de detalle: últimas 24 h e histórico de un servicio | 1 |
| 1.6 | Docker + despliegue en el entorno externo | 1 |
| 1.7 | Alta de 15–20 servicios reales en el YAML | 0,5 |

**Entregable:** URL funcionando con los servicios que cubre Statuspage (Claude, ChatGPT,
Copilot/GitHub, Cloudflare, Zoom, Atlassian…).

**🚦 Punto de decisión.** Dos semanas después de publicar el MVP se mira una sola cosa:
**¿lo abre alguien a diario?** Si no, se para el proyecto. Coste total asumido: ~8 días.

---

## Fase 2 — Fuentes que importan de verdad · 4–6 días

| # | Tarea | Días |
|---|---|---|
| 2.1 | Adaptador **Microsoft Graph** (Service Health de nuestro tenant) | 2 |
| 2.2 | Adaptador **RSS** genérico (Azure público, AWS) | 1 |
| 2.3 | Adaptador **Google** (`incidents.json` de GCP y Workspace) | 1 |
| 2.4 | Adaptador **Azure Resource Health** de nuestra suscripción (si aporta sobre 2.1) | 1 |
| 2.5 | Filtrado por componente (que "GitHub" no se ponga rojo si solo falla Pages) | 1 |

**Entregable:** el panel distingue "Microsoft tiene un problema" de **"Microsoft tiene
un problema que nos afecta a nosotros"**. Es el salto de calidad del proyecto.

---

## Fase 3 — Sondas propias · 3–5 días

| # | Tarea | Días |
|---|---|---|
| 3.1 | Agente local: sonda por saltos (gateway → DNS → externo), empuje al recolector | 2 |
| 3.2 | Detección de agente mudo = sede sin conectividad | 0,5 |
| 3.3 | Sondas sintéticas a las APIs de IA que consumimos (latencia y errores reales) | 1 |
| 3.4 | Estado manual: botón para marcar/desmarcar incidencia conocida (energía, móvil) con autor y hora | 1 |
| 3.5 | Reglas de agregación feed + sonda (§5 de arquitectura) | 0,5 |

**Entregable:** el panel responde a "¿somos nosotros o son ellos?", que es la pregunta
original del proyecto. **Aquí se cumple el objetivo real; lo demás es refinamiento.**

---

## Fase 4 — Alertas sin ruido · 3–4 días

| # | Tarea | Días |
|---|---|---|
| 4.1 | Notificador a Teams por webhook | 1 |
| 4.2 | Reglas: solo criticidad alta, solo transición a peor, ventana antirrebote de 5 min | 1 |
| 4.3 | Silencios y mantenimientos programados | 0,5 |
| 4.4 | Aviso de recuperación ("resuelto tras 34 min") | 0,5 |
| 4.5 | Ajuste con datos reales de una semana | 1 |

> **El riesgo de esta fase no es técnico.** Un canal de Teams que avisa de todo se
> silencia en tres días y a partir de ahí el sistema no sirve. Empezar avisando de
> **muy poco** (solo `major` en servicios de criticidad alta) y ampliar solo si alguien
> lo echa en falta. Es mucho más fácil añadir alertas que recuperar la atención perdida.

---

## Fase 5 — Consolidación · 3–5 días

| # | Tarea | Días |
|---|---|---|
| 5.1 | Informe semanal (incidencias, duración, proveedores peores) | 1,5 |
| 5.2 | Métricas: disponibilidad por servicio y mes, para negociar con proveedores | 1 |
| 5.3 | Modo pantalla grande para la sala/monitor de sistemas | 0,5 |
| 5.4 | Documentación de operación: cómo dar de alta un servicio, cómo depurar un adaptador | 1 |
| 5.5 | Autenticación (SSO) si el panel se publica fuera de la red | 1 |

---

## Resumen

| Fase | Días | Acumulado | Se puede parar aquí |
|---|---|---|---|
| 0 — Validación | 2–3 | 3 | Sí (se sabe si es viable) |
| 1 — MVP | 5–8 | 11 | **Sí — punto de decisión** |
| 2 — Fuentes clave | 4–6 | 17 | Sí (ya es útil de verdad) |
| 3 — Sondas | 3–5 | 22 | Sí (objetivo cumplido) |
| 4 — Alertas | 3–4 | 26 | Sí |
| 5 — Consolidación | 3–5 | 31 | — |

**Mínimo útil: 11 días. Producto que cumple el objetivo: 22 días.**

## Cómo medir si esto ha servido para algo

Definirlo **antes** de empezar, o al final cada uno recordará lo que le convenga:

| Indicador | Cómo se mide | Objetivo |
|---|---|---|
| Uso | Visitas únicas al panel por semana | ≥ 5 personas/semana al mes de publicarlo |
| Adelanto | Minutos entre nuestra detección y el aviso del proveedor | > 0 en la mitad de las incidencias |
| Tiempo ahorrado | Encuesta de una pregunta al mes 2 | "Me ahorra tiempo": mayoría de síes |
| Fiabilidad | % de tiempo con adaptadores en `unknown` | < 2 % |
