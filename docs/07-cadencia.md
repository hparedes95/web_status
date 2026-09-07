# 07 — Cadencia real y cómo arreglarla

## El problema, medido

El workflow pide ejecutarse **cada 10 minutos**. GitHub no lo cumple. Sobre tres días de
funcionamiento real:

| | Configurado | Real |
|---|---|---|
| Intervalo entre ciclos | 10 min | **mediana 2,1 h**, picos de 5 h |
| Horas con lectura | 100 % | **39 %** |

No es un fallo del código: los `schedule` de GitHub Actions son *best effort*. Se
descartan bajo carga, y cuanto más a menudo se piden, más se descartan. Pedir cada 10
minutos no consigue cada 10 minutos: consigue lo que sobra.

## Qué rompe esto

**El panel** aguanta: cada tarjeta dice «comprobado hace X», así que nunca miente sobre su
propia frescura. Simplemente es menos fresco de lo prometido.

**Las alertas no aguantan.** La regla pide dos lecturas seguidas en rojo antes de avisar.
Con dos horas entre lecturas, eso son de **cuatro a diez horas** hasta que suena Telegram.
Para lo que sirve una alerta, es lo mismo que no tenerla.

## La solución: empujar desde fuera

El workflow acepta ahora `repository_dispatch`. Como **tenéis servidores propios**, no hace
falta ningún servicio de terceros: una línea en un cron vuestro.

### 1. Un token para disparar

**Ajustes de tu cuenta → Developer settings → Personal access tokens → Fine-grained tokens**

- Repositorio: solo `hparedes95/web_status`
- Permiso: **Contents → Read and write** (es lo que exige `repository_dispatch`)

### 2. Una línea en el crontab

```cron
*/10 * * * * curl -s -X POST \
  -H "Authorization: Bearer $TOKEN_DISPARO" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/hparedes95/web_status/dispatches \
  -d '{"event_type":"comprobar"}'
```

Y ya está. El cron de GitHub se queda como red de seguridad por si esa máquina se apaga.

### Alternativa sin servidor propio

Un servicio gratuito de cron (cron-job.org y similares) haciendo esa misma petición. Añade
una dependencia externa y hay que dejarle un token, así que teniendo servidores propios no
compensa.

## Si os quedáis con el cron de GitHub

Entonces hay que ajustar las expectativas y la configuración:

- Tratar el panel como **consulta**, no como aviso: se mira cuando algo huele mal.
- Bajar `lecturas_para_avisar` a 1 en `services.yaml`. Se pierde el antirrebote —habrá algún
  falso positivo— pero al menos el aviso llega en horas y no en medio día.
- Y saberlo: un panel que dice «comprobado hace 3 h» durante una caída no está mintiendo,
  pero tampoco está avisando.
