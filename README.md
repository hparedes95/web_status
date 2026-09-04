# Web Status — Panel de estado de servicios

Aplicación web para ver de un vistazo si los servicios de los que dependemos
están operativos: nube (Azure, Microsoft 365), IA (Claude, ChatGPT, Copilot),
SaaS, conectividad (ISP, telefonía móvil) y suministros (energía).

> **Estado del proyecto: planificación.** Este repositorio contiene, de momento,
> el análisis de viabilidad y el plan de trabajo. No hay código de aplicación.

## Por qué

Cuando algo deja de funcionar, la primera pregunta siempre es la misma:
**¿somos nosotros o es el proveedor?** Hoy esa pregunta se responde abriendo
diez pestañas, preguntando por Teams y mirando Downdetector. El objetivo es
responderla en una pantalla y en menos de 10 segundos.

## Documentación

| Documento | Contenido |
|---|---|
| [01 — Viabilidad](docs/01-viabilidad.md) | Veredicto por familia de servicio, comprar vs. construir, recomendación |
| [02 — Catálogo de fuentes](docs/02-catalogo-fuentes.md) | Qué proveedor expone qué dato, cómo se obtiene y cuánto cuesta |
| [03 — Arquitectura](docs/03-arquitectura.md) | Componentes, modelo de datos, contrato de adaptador, despliegue |
| [04 — Plan por fases](docs/04-plan-fases.md) | Fases, backlog, estimaciones y criterios de aceptación |
| [05 — Riesgos](docs/05-riesgos.md) | Riesgos, probabilidad, impacto y mitigación |
| [06 — Decisiones abiertas](docs/06-decisiones-abiertas.md) | Lo que hay que decidir antes de escribir código |

## Resumen en tres líneas

1. **Es viable y barato** para el 70–80 % del catálogo: la mayoría de proveedores
   grandes publican su estado en JSON o RSS sin autenticación.
2. **No es viable de forma fiable** para ISP doméstico/empresarial, telefonía móvil
   y energía: ahí no hay API y se resuelve con **sondas propias**, no con feeds.
3. El riesgo real no es técnico, es de **mantenimiento y de ruido**: adaptadores que
   se rompen y alertas que nadie lee. El plan lo aborda explícitamente.

## Verificar las fuentes antes de empezar

```bash
./scripts/check-sources.sh
```

Comprueba qué endpoints del catálogo responden hoy. Es el primer entregable de
la Fase 0 y la condición para dar por buena la estimación.
