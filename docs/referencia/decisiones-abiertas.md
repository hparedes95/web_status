# 06 — Decisiones abiertas

Lo que hay que responder antes de escribir código. Ninguna bloquea la Fase 0.

## D1 — ¿Cuál es el inventario real? 🔴 bloquea Fase 1

El plan asume ~20 servicios en la primera tanda. Hace falta la lista de verdad, con
criticidad (alta/media/baja) y responsable de cada uno. Sin esto, el panel enseña lo
que el desarrollador supone que importa.

**Propuesta:** una hoja con Servicio · Categoría · Criticidad · ¿Quién lo nota si cae?

## D2 — ¿Dónde se aloja? 🔴 bloquea Fase 1

Condiciona el despliegue y, según el documento de riesgos (R8), la utilidad del
sistema. Debe estar **fuera** de la red que vigila.

**Opciones:** VPS externo (~5 €/mes, control total) · Azure Container Apps (encaja si
ya hay suscripción, ~10–25 €/mes) · Azure Static Web Apps + Functions (más barato,
menos flexible para el poller).

**Recomendación:** VPS externo por simplicidad y precio. Azure si hay política de
"todo en nuestra suscripción".

## D3 — ¿Se pide ya la aplicación de Entra ID? 🟠 bloquea Fase 2

Es la vía al Service Health de nuestro tenant, el dato de mayor calidad del proyecto.
Requiere permiso de aplicación `ServiceHealth.Read.All` con consentimiento de
administrador.

**Recomendación:** solicitarlo el primer día aunque el proyecto se pare después. El
plazo es externo y no cuesta nada tenerlo aprobado.

## D4 — ¿Quién es el dueño? 🟠 riesgo R9

Alguien tiene que asumir los 2–4 h/mes de mantenimiento. Si nadie los asume, la
recomendación honesta cambia: **comprar una herramienta comercial** para la mitad
fácil del catálogo y olvidarse de la mitad difícil.

## D5 — ¿Alertas o solo panel? 🟡

Si no hay apetito por alertas en Teams, la Fase 4 se cae y el proyecto queda en 22
días. Conviene saberlo antes, porque cambia bastante el diseño del notificador.

## D6 — ¿Público interno o también móvil desde fuera? 🟡

Si se quiere consultar desde el móvil sin VPN (que es lo lógico: la red está caída),
hay que exponerlo a internet, y entonces la autenticación de la Fase 5 deja de ser
opcional. Merece la pena decidirlo pronto porque afecta al despliegue.

## D7 — ¿Se reutiliza Uptime Kuma para las sondas? 🟡

Reduce la Fase 3 de 3–5 días a 1–2, a cambio de operar un servicio más.

**Recomendación:** decidirlo al empezar la Fase 3, con el MVP ya funcionando.

---

## Lo primero que haría yo

1. Cerrar **D1** (el inventario) — es media hora y desbloquea todo.
2. Lanzar la solicitud de **D3** el mismo día.
3. Ejecutar `scripts/check-sources.sh` con el inventario real.
4. Con eso encima de la mesa, decidir si se hacen los 8 días de la Fase 1.
