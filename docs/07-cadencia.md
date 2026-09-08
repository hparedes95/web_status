# 07 — Cadencia: por qué había huecos y cómo se han quitado

## El problema, medido

El workflow pedía ejecutarse **cada 10 minutos**. GitHub no lo cumplía. Medido sobre 70
horas reales (26 ejecuciones programadas, del 4 al 7 de septiembre):

| | Configurado | Real |
|---|---|---|
| Ciclos lanzados | 423 | **25** — un 5,9 % |
| Intervalo entre ciclos | 10 min | **mediana 2,1 h**; el más corto 95 min, el peor 6,4 h |
| Horas con lectura | 100 % | **39 %** (29 de 75) |

Ni una sola vez se acercó a los 10 minutos pedidos. Tampoco arrancaba en los minutos que
pedía el cron: los minutos de arranque salían repartidos por todo el reloj (:04, :09, :14,
:28, :35, :52…), señal de que no se ejecutaba cuando tocaba sino cuando había hueco.

No es un fallo del código: los `schedule` de GitHub Actions son *best effort*. Se
descartan bajo carga, y cuanto más a menudo se piden, más se descartan. Pedir cada 10
minutos no consigue cada 10 minutos: consigue lo que sobra.

## Qué rompía

**El panel** aguantaba: cada fila dice «comprobado hace X», así que nunca mentía sobre su
propia frescura. Simplemente era menos fresco de lo prometido.

**Las alertas no.** La regla pide dos lecturas seguidas en rojo antes de avisar. Con dos
horas entre lecturas, eso eran de **cuatro a diez horas** hasta que sonara Telegram. Para
lo que sirve una alerta, lo mismo que no tenerla.

## La solución: que cada ciclo pida el siguiente

En vez de esperar a que GitHub respete un calendario que no respeta, **cada ejecución
encadena la siguiente** con `repository_dispatch` justo antes de terminar. La cadencia deja
de depender de la cola de `schedule` de GitHub y pasa a depender solo de que el ciclo
anterior haya llegado al final.

Además, cada ciclo **sondea cinco veces** con dos minutos de separación, no una. Eso da:

| | Antes | Ahora |
|---|---|---|
| Lecturas por hora | ~0,5 | **~30** |
| Horas sin cobertura | 61 % | **0** |
| Retardo de una alerta | 4–10 h | **~2 min** |
| Publicaciones de la página | ~0,5/h | 6/h |

Las piezas que lo sostienen, y por qué cada una:

- **`cancel-in-progress: true`** — impide que la cadena se duplique. Si mientras un ciclo
  corre llega el cron, una issue o un disparo externo, ese ciclo se cancela y el nuevo toma
  el relevo: siempre hay exactamente uno vivo. Con `false` se encolarían y cada disparo
  doblaría el número de cadenas hasta reventar.
- **`if: always()` en el eslabón** — si el sondeo o el despliegue fallan, la cadena sigue
  viva igualmente. Un ciclo malo no puede dejar el panel congelado.
- **El cron horario** — se queda como red de seguridad, no como motor. Si la cadena se
  rompe (token caducado, incidencia de GitHub), esto la reanuda.
- **`Cobertura 24 h` en la cabecera del panel** — de las últimas 24 horas, en cuántas hubo
  alguna lectura. Tiene que poner **100 %**. Si baja, la cadena está rota y se ve sin
  entrar en los registros de Actions.

### Lo único que hay que hacer a mano: el token

GitHub **bloquea a propósito** que un workflow se dispare a sí mismo con el `GITHUB_TOKEN`
del propio workflow, precisamente para evitar bucles infinitos. Así que la cadena necesita
un token propio. Es lo único manual, y se hace una vez:

**1. Crear el token**
Ajustes de tu cuenta → Developer settings → Personal access tokens → **Fine-grained tokens**

- Repository access: **Only select repositories** → `hparedes95/web_status`
- Permissions → Repository permissions → **Contents: Read and write** (es lo que exige
  `repository_dispatch`)
- Expiración: la más larga que te deje. Cuando caduque, la cadena se para y la cobertura
  del panel empezará a bajar — que es exactamente el aviso que quieres.

**2. Guardarlo como secreto**
Repositorio → Settings → Secrets and variables → Actions → New repository secret

- Name: **`CADENA_TOKEN`**
- Secret: el token

**3. Arrancar la cadena**
Actions → «Estado de servicios» → Run workflow. A partir de ahí se automantiene.

Sin ese secreto no se rompe nada: el workflow avisa en los registros y la cadencia vuelve a
depender del cron, es decir, al 39 % de antes.

## Ajustar el ritmo

En `.github/workflows/status.yml`:

```yaml
env:
  SONDEOS: "5"    # lecturas por ciclo
  PAUSA: "120"    # segundos entre lecturas
```

`SONDEOS × PAUSA` es la duración del ciclo, y por tanto cada cuánto se publica la página.
Diez minutos es un punto sensato: seis publicaciones por hora deja margen de sobra frente
a los límites de GitHub Pages, y ninguna hora se queda sin lectura ni aunque se pierdan
cinco ciclos seguidos.

## Empujar además desde fuera (opcional)

El workflow sigue aceptando `repository_dispatch` con `event_type: comprobar`. Si queréis
un segundo motor independiente de GitHub, una línea en el crontab de cualquier máquina
vuestra, con el mismo token:

```cron
*/10 * * * * curl -s -X POST \
  -H "Authorization: Bearer $CADENA_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/hparedes95/web_status/dispatches \
  -d '{"event_type":"comprobar"}'
```

No hace falta para que funcione: es redundancia. Cubre el caso de que GitHub Actions esté
teniendo un mal día entero, que es el único escenario que la cadena por sí sola no cubre.

## Lo que sigue sin poder garantizarse

La cadena se apoya en GitHub Actions. Si Actions se cae, se cae el panel — no hay forma de
evitarlo mientras el panel viva dentro de GitHub. Lo que sí está resuelto es que **el panel
no mienta sobre ello**: el sello dice «comprobado hace X» y la cobertura dice qué
porcentaje de las últimas 24 horas se miró de verdad.

La independencia real sería mover el sondeo a un servidor vuestro y dejar GitHub solo para
publicar la página. Es la siguiente parada si esto no llega a ser suficiente.
