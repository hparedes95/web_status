# 05 — Riesgos

Ordenados por impacto real sobre el proyecto, no por probabilidad.

## R1 — El panel se convierte en decoración 🔴

**El riesgo más probable de todos.** Se construye, se enseña, se usa dos semanas y
luego nadie lo abre.

- **Causa:** no está donde ya se mira (Teams, navegador de inicio) o no aporta nada que
  no diera una pestaña de favoritos.
- **Mitigación:** el punto de decisión de la Fase 1 lo hace explícito y barato de
  cortar. Alertas a Teams en Fase 4 para llevar el dato a donde ya está la gente.
  Ponerlo como página de inicio del navegador en los equipos de sistemas.
- **Señal temprana:** menos de 5 visitas únicas por semana al mes de publicarlo.

## R2 — Falsa sensación de seguridad 🔴

Un adaptador roto devuelve `unknown` o, peor, se queda con el último valor bueno.
Alguien mira el panel, lo ve verde y concluye que no hay incidencia.

- **Mitigación:** `unknown` es un estado visible, con su color propio. Antigüedad del
  dato en cada tarjeta ("hace 3 min"). Alerta interna si un adaptador lleva > 30 min
  sin lectura válida. **Nunca mostrar como bueno un dato viejo.**
- Es un riesgo de diseño, no de operación: si no se resuelve en la Fase 1, no se
  resuelve nunca.

## R3 — Fatiga de alertas 🟠

El canal de Teams se llena de mantenimientos programados de servicios que no usamos y
alguien lo silencia. A partir de ese momento el sistema no avisa de nada.

- **Mitigación:** arrancar la Fase 4 avisando de muy poco y ampliar bajo demanda.
  Antirrebote de 5 minutos. Nunca alertar de `maintenance` ni de criticidad baja.

## R4 — Los proveedores cambian sus feeds sin avisar 🟠

Es cuestión de tiempo. Un endpoint que hoy responde JSON mañana devuelve 404 o cambia
de estructura.

- **Mitigación:** contrato de adaptador que degrada a `unknown` sin lanzar excepción;
  pruebas con respuestas guardadas en disco; el aviso de R2 detecta la rotura.
- **Coste asumido:** ~2–4 h/mes de mantenimiento. Hay que reconocerlo en el
  presupuesto, no descubrirlo después.

## R5 — Bloqueo del proyecto esperando permisos de Entra ID 🟡

El adaptador de Microsoft 365 necesita un registro de aplicación con consentimiento de
administrador. Puede tardar días o semanas según quién lo apruebe.

- **Mitigación:** solicitarlo en la tarea 0.4, el primer día. La Fase 1 no depende de
  ello. Si se deniega, el respaldo es el RSS público de Azure/M365, con menos calidad
  pero sin bloqueo.

## R6 — Desvío de alcance hacia una herramienta de monitorización 🟡

"Ya que tenemos esto, metemos también los servidores, y las copias de seguridad, y
las certificaciones SSL…". El proyecto pasa de 20 a 100 días y no termina.

- **Mitigación:** la sección "Lo que este proyecto NO es" del documento de
  arquitectura. Toda petición nueva se contrasta contra ella.

## R7 — Términos de servicio y límites de tasa 🟡

Sondear demasiado agresivamente puede provocar bloqueos por IP. El scraping de
Downdetector o de webs de operadoras infringe sus términos.

- **Mitigación:** máximo una petición por fuente y minuto, con `User-Agent`
  identificable y respeto de `Retry-After`. Scraping descartado por escrito en el
  catálogo de fuentes.

## R8 — El panel cae con la red que vigila 🟡

Alojarlo dentro de la oficina lo inutiliza justo cuando hace falta.

- **Mitigación:** resuelto por diseño con la arquitectura híbrida (recolector fuera,
  agente dentro). El riesgo reaparece si alguien decide "de momento lo levantamos en
  el servidor de aquí" — **es una decisión de arquitectura, no de comodidad**.

## R9 — Proyecto sin dueño 🟠

Sin alguien responsable, R2 y R4 se combinan: los adaptadores se rompen, nadie lo
nota, el panel miente y acaba abandonado.

- **Mitigación:** asignar un responsable nominal antes de la Fase 1 y dejar los
  2–4 h/mes de mantenimiento reconocidos en su carga.

## Resumen

| ID | Riesgo | Impacto | Prob. | Se aborda en |
|---|---|---|---|---|
| R1 | Panel decorativo | Alto | Alta | Fase 1 (decisión) + Fase 4 |
| R2 | Falsa seguridad | Alto | Media | Fase 1 (diseño) |
| R9 | Sin dueño | Alto | Media | Antes de Fase 1 |
| R3 | Fatiga de alertas | Medio | Alta | Fase 4 |
| R4 | Feeds que cambian | Medio | Alta | Fase 1 + mantenimiento |
| R6 | Desvío de alcance | Medio | Media | Documento de arquitectura |
| R5 | Permisos de Entra ID | Medio | Media | Tarea 0.4 |
| R7 | Términos y tasas | Bajo | Media | Fase 1 |
| R8 | Panel cae con la red | Alto | Baja | Arquitectura |
