# 06 — Agente de latido

Resuelve lo que ningún feed puede resolver: **si hay luz en la oficina, si la línea está
viva y si el SAI está tirando de batería.**

## Por qué hacía falta

Antes esos tres indicadores eran botones manuales, porque no existe API de operadoras ni
de distribuidoras eléctricas. Eso sigue siendo cierto — pero **teniendo servidores propios
sí hay dónde medir**, y medir desde dentro es mejor que cualquier feed: no informa de lo
que le pasa al operador en general, informa de lo que os pasa a vosotros.

## Cómo funciona

```
   Dentro de la red                          Fuera
   ┌───────────────────────┐                ┌─────────────────────┐
   │ agente/latido.py      │ ── PATCH ────▶ │ issue «latido:…»    │
   │  · ¿hay internet?     │   (solo sale)  └──────────┬──────────┘
   │  · SAI: red o batería │                           │ lee
   │  · autonomía restante │                ┌──────────▼──────────┐
   │  · respaldo móvil     │                │ Panel               │
   └───────────────────────┘                └─────────────────────┘
```

**No abre ningún puerto** ni necesita que nadie entre desde fuera: solo hace una petición
saliente a la API de GitHub. Actualiza el cuerpo de una issue, que el panel lee.

> **El silencio es el dato.** Si el agente deja de reportar, o se ha ido la luz, o se ha
> caído la línea, o la máquina está apagada. Las tres son cosas que hay que mirar, y el
> panel las marca sin que nadie tenga que avisar. Es justo lo que un botón manual no hace.

## Puesta en marcha

### 1. Crear la issue del latido

Abre una issue en el repositorio titulada, por ejemplo, **«Latido — Sede central»**, con la
etiqueta **`latido:sede-central`**. Déjala abierta: no es una incidencia, es el buzón donde
el agente escribe. Apunta su número.

### 2. Crear un token para el agente

**Ajustes de tu cuenta → Developer settings → Personal access tokens → Fine-grained tokens**

- Repositorio: solo `hparedes95/web_status`
- Permiso: **Issues → Read and write**, y nada más

Ese token vive en una máquina de la oficina, así que dale el mínimo alcance posible: con
esos permisos no puede tocar el código ni los secretos.

### 3. Instalar el agente

Copia `agente/latido.py` a una máquina que esté siempre encendida y **enchufada al SAI**
—si no, no puede contarte que se ha ido la luz—. Solo necesita Python 3, sin dependencias.

Configúralo por variables de entorno:

| Variable | Para qué |
|---|---|
| `LATIDO_TOKEN` | El token del paso 2 |
| `LATIDO_ISSUE` | El número de la issue del paso 1 |
| `LATIDO_REPO` | `hparedes95/web_status` (ya es el valor por defecto) |
| `LATIDO_UPS` | Nombre del SAI en NUT (`upsc -l` los lista). Vacío = no se consulta |
| `LATIDO_INTERFAZ_MOVIL` | Interfaz del respaldo móvil, p. ej. `wwan0`. Vacío = no se prueba |

Comprueba qué recogería, sin enviar nada:

```bash
python3 agente/latido.py --probar
```

Y prográmalo cada minuto:

```cron
* * * * * LATIDO_TOKEN=... LATIDO_ISSUE=12 LATIDO_UPS=sai01 /usr/bin/python3 /opt/latido.py
```

### 4. Encender los indicadores

En `services.yaml` hay tres bloques comentados listos: sede, suministro eléctrico y
respaldo móvil. Descoméntalos y borra los botones manuales, que ya no hacen falta.

## Sobre el SAI

El agente lee el SAI a través de **NUT** (`upsc`), que es lo habitual en Linux y habla con
la mayoría de SAIs gestionables (APC, Eaton, Riello, Salicru). De ahí saca tres cosas:

| Dato | Qué significa |
|---|---|
| `ups.status` | `OL` hay corriente · `OB` está tirando de batería → **corte de luz** |
| `battery.runtime` | Minutos de autonomía restantes: **el número que decide si hay que apagar** |
| `battery.charge` | Salud de la carga. Una batería al 60 % da la mitad de autonomía de la que crees |

Si el SAI no es gestionable o NUT no está instalado, el agente sigue sirviendo para la sede
y para el respaldo móvil, y el indicador de energía queda en «sin datos» — que es lo
honesto, en vez de darlo por bueno.

## Sobre la telefonía móvil

La sonda sale por la interfaz del respaldo (`curl --interface`). Es **la única forma real**
de saber si la red del operador funciona: no hay API que lo diga.

Dos avisos que siguen en pie:

- Movistar es la marca comercial de Telefónica: un indicador, no dos.
- **Comprueba sobre qué red circula tu respaldo.** Varios operadores usan la red de otro, y
  un respaldo que va por la misma red que la línea principal no es un respaldo. Eso solo se
  descubre el día que hace falta.

## Varias sedes

Un agente por sede, cada uno con su issue y su etiqueta (`latido:sede-norte`…). Con dos o
más aparece gratis el mejor indicador de todos: **si varias sedes del mismo operador callan
a la vez, es del operador; si calla una sola, es vuestra.** Esa es la pregunta que abre
toda incidencia.
