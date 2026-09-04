# 04 — Puesta en marcha

El código está construido, probado y ejecutándose. Faltan cosas que solo puedes hacer tú,
porque requieren permisos de administrador del repositorio o cuentas externas.

## Estado actual

El workflow ya se ha ejecutado y lee correctamente **nueve de los diez indicadores**:

```
azure           operativo    Sin avisos recientes
aws             operativo    Sin eventos recientes en nuestras regiones
claude          operativo    All Systems Operational
chatgpt         operativo    All Systems Operational
github          operativo    Todos los componentes operativos
copilot         operativo    Todos los componentes operativos
telefonica      operativo    Sin incidencia marcada
vodafone        operativo    Sin incidencia marcada
energia         operativo    Sin incidencia marcada
microsoft-365   operativo    Sonda propia (ver más abajo)
```

---

## 1. Activar GitHub Pages ← **lo único que bloquea la web**

**Ajustes del repositorio → Pages → Source: `GitHub Actions`**

No hace falta elegir rama. Esto **no se puede automatizar**: se intentó, y el token del
workflow no tiene permiso para crear el sitio (`Resource not accessible by integration`).
Hasta que se active, cada ciclo termina en rojo con ese aviso — aunque el estado se lee y
se guarda igualmente, así que el historial ya se está acumulando.

En cuanto lo actives, el siguiente ciclo publica el panel en:

**https://hparedes95.github.io/web_status/**

Para no esperar: **Actions → Estado de servicios → Run workflow**.

## 2. Telegram

1. Habla con **@BotFather** → `/newbot` → te da un **token**.
2. Escribe algo al bot, o añádelo al grupo donde queráis los avisos.
3. Saca el **chat id** en `https://api.telegram.org/bot<TOKEN>/getUpdates`, buscando
   `"chat":{"id":...}`. En un grupo el id es negativo, con el signo.

Luego, en **Ajustes → Secrets and variables → Actions → New repository secret**:

| Secreto | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token de BotFather |
| `TELEGRAM_CHAT_ID` | El id del chat o grupo |

Sin estos secretos el panel funciona igual; simplemente no manda avisos.

> Si el bot va a escribir en un grupo tiene que ser miembro, y si el grupo tiene el modo
> de privacidad activo, dale administrador o desactívalo con `/setprivacy` en BotFather.

## 3. Las tres etiquetas

**Issues → Labels → New label**, con estos nombres exactos:

```
caida:telefonica
caida:vodafone
caida:energia
```

Son las que encienden las luces sin feed. Solo quien tiene permiso de escritura puede
aplicarlas, así que nadie de fuera puede tocar el panel aunque el repositorio sea público.

## 4. Microsoft 365, para que el dato sea de verdad

Ese indicador ya da señal, pero es una **sonda propia**: comprueba que responden los
endpoints públicos de Microsoft. Detecta una caída total del inicio de sesión; no ve que
Teams vaya lento. Por eso la fila lleva la etiqueta `sonda`.

Para tener el estado oficial —y además el de *vuestro* tenant, no el global— hace falta
Microsoft Graph. **Microsoft no publica ningún feed** (comprobado, ver
[`02-fuentes.md`](02-fuentes.md)), así que no hay más caminos.

1. **Entra ID → Registros de aplicaciones → Nuevo registro.**
2. **Permisos de API →** Microsoft Graph → **Permisos de aplicación** →
   `ServiceHealth.Read.All` → **Conceder consentimiento de administrador**.
3. **Certificados y secretos →** nuevo secreto de cliente.
4. Guarda tres secretos más en el repositorio:

| Secreto | De dónde sale |
|---|---|
| `M365_TENANT_ID` | Id. de directorio (inquilino) |
| `M365_CLIENT_ID` | Id. de aplicación (cliente) |
| `M365_CLIENT_SECRET` | El **valor** del secreto de cliente, no su id. |

El adaptador ya está escrito. En cuanto existan los tres secretos, esa luz se enciende, y
con mejor dato que el resto: Graph informa del estado de **vuestro tenant**, no del global.

Mientras tanto la luz queda en «sin datos» con el motivo escrito. Es deliberado: nunca
poner en verde lo que no se ha podido comprobar.

---

## Después

| Qué | Dónde |
|---|---|
| Añadir un servicio con página de estado | `services.yaml`, un bloque más |
| Activar la alerta de un servicio | `alerta: true` en `services.yaml` |
| Cambiar la cadencia | El `cron` de `.github/workflows/status.yml` |
| Marcar una avería de telefonía o luz | Abrir una issue con la etiqueta `caida:<id>` |
| Averiguar por qué una luz está en blanco | Actions → **Comprobar fuentes** → Run workflow |
| Probar cambios sin desplegar | `python tests/test_poller.py` |

## Si algún día se pone el repositorio en privado

Poner el repositorio en privado **no hace privado el panel**: Pages pasa a requerir plan de
pago y el sitio publicado sigue siendo visible desde internet salvo con Enterprise Cloud.
Además los minutos de Actions dejan de ser gratis, y cada ejecución ronda los 2 minutos
facturados, así que habría que subir el intervalo de 10 min a 30 min o a 1 hora.

Para un panel realmente privado: **Cloudflare Pages + Cloudflare Access** (gratis hasta 50
usuarios, el poller no cambia, solo el destino del despliegue) o un contenedor en un VPS
por ~5 €/mes.
