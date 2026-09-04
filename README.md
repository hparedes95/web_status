# Web Status — Panel de estado de servicios

Una página con **una luz por servicio** y **una alerta cuando alguna se pone en rojo**.

> **Estado: planificación.** Este repositorio contiene el alcance y el plan. Todavía no hay
> código de aplicación.

## Qué vigila

**Automático** (feeds oficiales): Microsoft 365 · Azure · AWS · Claude · ChatGPT · GitHub · GitHub Copilot

**Manual** (no existe API): Telefónica/Movistar · Vodafone · Suministro eléctrico

## Por qué

Cuando algo falla, la primera reacción es abrir diez pestañas de páginas de estado. Esto
las reúne en una. Los tres indicadores manuales son un botón: cuando alguien confirma la
avería con el operador y la marca, el resto deja de llamar al mismo soporte.

## Documentación

| Documento | Contenido |
|---|---|
| [01 — Alcance](docs/01-alcance.md) | Qué entra, qué no, y las tres limitaciones que hay que asumir |
| [02 — Fuentes](docs/02-fuentes.md) | De dónde sale cada dato y la decisión pendiente sobre Microsoft 365 |
| [03 — Implementación](docs/03-implementacion.md) | Cómo funciona, la regla de la alerta y las tareas |
| [referencia/](docs/referencia/) | Análisis previo, con un alcance más amplio que se descartó |

## Antes de escribir código

```bash
./scripts/check-sources.sh
```

Comprueba cuáles de las fuentes responden hoy. Es la tarea 1 del plan y la condición para
dar por buena la estimación de 5 días.

## Esfuerzo

**4–6 días persona**, más 1–2 h/mes de mantenimiento.
