# 04 — Puesta en marcha

El código está listo. Faltan cinco cosas que solo puedes hacer tú, porque requieren acceso
a la configuración del repositorio o a cuentas.

## 1. Crear el bot de Telegram

1. Habla con **@BotFather** en Telegram → `/newbot` → te da un **token**.
2. Escribe algo al bot (o añádelo al grupo donde queráis los avisos).
3. Saca el **chat id**: abre `https://api.telegram.org/bot<TOKEN>/getUpdates` y busca
   `"chat":{"id":...}`. En un grupo el id es negativo, con el signo incluido.

> Si el bot va a escribir en un grupo, tiene que ser miembro. Y si el grupo tiene el modo
> de privacidad activado, dale permiso de administrador o desactiva la privacidad con
> `/setprivacy` en BotFather.

## 2. Guardar los secretos

**Ajustes del repositorio → Secrets and variables → Actions → New repository secret**

| Nombre | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | El token de BotFather |
| `TELEGRAM_CHAT_ID` | El id del chat o grupo |

⚠️ **El repositorio es público.** Estos valores no pueden acabar en ningún fichero, ni
siquiera en un ejemplo. El código los lee solo de las variables de entorno.

## 3. Activar GitHub Pages

**Ajustes del repositorio → Pages → Source: GitHub Actions**

No hace falta elegir rama: el propio workflow publica el contenido de `site/`. La URL
quedará en `https://hparedes95.github.io/web_status/`.

> Al ser un repositorio público, **la página será visible desde internet**. No muestra
> datos internos —son estados de proveedores que ya son públicos uno a uno—, pero sí deja
> ver qué proveedores usáis y el nombre de quien marque una avería manual.

## 4. Crear las tres etiquetas

**Issues → Labels → New label**, tres etiquetas con estos nombres exactos:

```
caida:telefonica
caida:vodafone
caida:energia
```

Son las que encienden las luces sin feed. Solo quien tiene permiso de escritura puede
aplicarlas, así que nadie de fuera puede tocar el panel.

## 5. Lanzar el primer ciclo

**Actions → Estado de servicios → Run workflow**

Ese primer ciclo hace tres cosas a la vez: comprueba qué fuentes responden de verdad,
publica la página y deja el estado inicial guardado.

**Mira su salida con atención.** Cada línea dice qué devolvió cada fuente:

```
  microsoft-365    desconocido  La fuente respondió HTTP 404
  azure            operativo    Sin avisos recientes
  claude           operativo    All Systems Operational
```

Todo lo que salga `desconocido` es una URL que hay que corregir en `services.yaml`. Las
URLs se escribieron sin poder verificarlas —el entorno donde se redactó el plan tenía
bloqueada la salida a esos dominios—, así que **es de esperar que alguna falle en el primer
intento**. Es exactamente lo que este ciclo sirve para descubrir.

La más probable es **Microsoft 365**: su feed público es el menos fiable de los seis. Si
falla, la alternativa es Microsoft Graph, que además da el estado de *vuestro* tenant en
lugar del global. Requiere una aplicación en Entra ID con el permiso
`ServiceHealth.Read.All` y consentimiento de administrador; el trámite depende de terceros,
así que conviene pedirlo cuanto antes si se va por ahí.

## Después

| Qué | Dónde |
|---|---|
| Añadir un servicio con página de estado | `services.yaml`, un bloque más |
| Activar la alerta de un servicio | `alerta: true` en `services.yaml` |
| Cambiar la cadencia | El `cron` de `.github/workflows/status.yml` |
| Marcar una avería de telefonía o luz | Abrir una issue con la etiqueta `caida:<id>` |
| Probar cambios sin desplegar | `python tests/test_poller.py` |
