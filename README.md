# Web Status — Panel de estado de servicios

Una página con **una luz por servicio** y **una alerta cuando alguna se pone en rojo**.

**Panel:** https://hparedes95.github.io/web_status/ · **Avisos:** Telegram

> **Estado: construido, pendiente de puesta en marcha.** Faltan cinco pasos de
> configuración que solo puede dar el dueño del repositorio: ver
> [04 — Puesta en marcha](docs/04-arranque.md).

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
| [03 — Implementación](docs/03-implementacion.md) | Cómo funciona por dentro: adaptadores, estados y la regla de la alerta |
| [04 — Puesta en marcha](docs/04-arranque.md) | Los cinco pasos que faltan: bot de Telegram, secretos, Pages, etiquetas y primer ciclo |
| [referencia/](docs/referencia/) | Análisis previo, con un alcance más amplio que se descartó |

## Cómo funciona

Sin servidor: un workflow de GitHub Actions lee las fuentes cada 10 minutos, publica el
panel en GitHub Pages y avisa por Telegram cuando algo se cae. Las tres luces sin API
(telefonía y energía) se encienden abriendo una issue con la etiqueta `caida:<id>`.

Detalle en [03 — Implementación](docs/03-implementacion.md).

## Desarrollo

```bash
pip install -r requirements.txt
python tests/test_poller.py      # pruebas, sin red
python src/poller.py             # un ciclo completo, escribe site/status.json
./scripts/check-sources.sh       # ¿qué fuentes responden hoy?
```

Para ver el panel en local: `python -m http.server -d site` y abrir
<http://localhost:8000>.

## Mantenimiento

**1–2 h/mes.** Los proveedores cambian sus feeds sin avisar; cuando pasa, esa luz se pone
en blanco (`desconocido`) en lugar de mentir.
