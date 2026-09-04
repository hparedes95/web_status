# 01 — Alcance

## Lo que se construye

Una página web con **una luz por servicio** y **una alerta cuando alguna se pone en rojo**.
Nada más.

| # | Indicador | Cómo se obtiene | Automático |
|---|---|---|---|
| 1 | **Microsoft 365** (correo, Teams, SharePoint, Copilot) | Feed de estado de Microsoft | ✅ |
| 2 | **Azure** | Feed RSS de estado de Azure | ✅ |
| 3 | **AWS** | Health Dashboard público | ✅ |
| 4 | **Claude** (Anthropic) | Página de estado (JSON) | ✅ |
| 5 | **ChatGPT / OpenAI** | Página de estado (JSON) | ✅ |
| 6 | **GitHub Copilot** | Página de estado (JSON) | ✅ |
| 7 | **Telefónica / Movistar** | Botón manual | ❌ |
| 8 | **Vodafone** | Botón manual | ❌ |
| 9 | **Suministro eléctrico** | Botón manual | ❌ |

Añadir un servicio más que tenga página de estado pública es **una línea de configuración**,
no desarrollo. Añadir uno que no la tenga es otro botón manual.

## Lo que NO se construye

Descartado a propósito para que el proyecto quepa en una semana:

- Sondas propias de red (no se responde a «¿es nuestro o del proveedor?»)
- Agente dentro de la red
- Certificados, dominios, DNS, listas negras
- Métricas, informes y estadísticas de disponibilidad
- Autenticación de usuarios
- Cualquier cosa que monitorice **nuestros** servidores o aplicaciones

Todo eso está catalogado en [`docs/referencia/`](referencia/) por si algún día se retoma.

## Las tres limitaciones que hay que asumir

Ninguna se puede arreglar sin ampliar el alcance. Es mejor saberlas ahora que descubrirlas
en la primera incidencia.

**1. Telefonía y energía no se detectan solas.** No existe API de operadoras ni de
distribuidoras eléctricas. El botón manual sigue siendo útil —cuando alguien confirma la
avería y la marca, el resto deja de llamar al soporte por lo mismo y se ve desde cuándo
está caído— pero **alguien tiene que pulsarlo**. Si nadie lo pulsa, esas tres luces se
quedan en verde durante la avería.

**2. Los feeds llegan tarde.** Un proveedor tarda entre 10 y 45 minutos en reconocer una
caída. Durante ese rato su semáforo está en verde y los usuarios ya están afectados. Sin
sondas propias no hay forma de adelantarse: el panel dirá lo mismo que la página oficial,
solo que todas juntas en una pantalla.

**3. El estado es global, no nuestro.** «Azure operativo» puede convivir con «nuestra
suscripción degradada». La excepción es Microsoft 365 si se usa la vía autenticada (ver
[`02-fuentes.md`](02-fuentes.md)), que sí da el estado de nuestro tenant.

Con esto, el panel responde a **«¿está caído algo de lo que dependemos?»** y ahorra el
paseo por diez pestañas. No responde a «¿somos nosotros o son ellos?».

## Esfuerzo

**4–6 días persona.** Detalle en [`03-implementacion.md`](03-implementacion.md).
