#!/usr/bin/env bash
# Instala el agente de latido en esta máquina: lo copia, programa el cron y lo prueba.
#
#   sudo ./instalar.sh
#
# Antes de ejecutarlo hacen falta dos cosas:
#   · un token de GitHub (fine-grained, solo este repo, permiso Issues: read & write)
#   · el número de la issue del latido — es la #1
#
# Ejecútalo en una máquina que esté SIEMPRE ENCENDIDA y ENCHUFADA AL SAI. Si no
# está en el SAI, se apagará con el corte de luz antes de poder contarlo — aunque
# en ese caso el panel también lo detecta, por el silencio.

set -euo pipefail

DESTINO="${DESTINO:-/opt/web-status}"
REPO="${LATIDO_REPO:-hparedes95/web_status}"
ISSUE="${LATIDO_ISSUE:-1}"

leer() {  # leer <mensaje> <variable> [oculto]
  local mensaje="$1" var="$2" oculto="${3:-}"
  if [ -n "${!var:-}" ]; then return; fi
  if [ -n "$oculto" ]; then read -rsp "$mensaje: " valor; echo; else read -rp "$mensaje: " valor; fi
  printf -v "$var" '%s' "$valor"
}

echo "== Agente de latido — instalación =="
echo "   repositorio : $REPO"
echo "   issue       : #$ISSUE"
echo

leer "Token de GitHub (no se muestra)" LATIDO_TOKEN oculto
leer "Nombre del SAI en NUT (vacío = no leer el SAI; 'upsc -l' los lista)" LATIDO_UPS
leer "Interfaz del respaldo móvil (vacío = no probar; p. ej. wwan0)" LATIDO_INTERFAZ_MOVIL

install -d -m 755 "$DESTINO"
install -m 755 "$(dirname "$0")/latido.py" "$DESTINO/latido.py"

# El token vive en un fichero solo legible por root, no en el crontab, donde
# cualquiera que liste los procesos podría verlo.
umask 077
cat > "$DESTINO/latido.env" <<EOF
LATIDO_REPO=$REPO
LATIDO_ISSUE=$ISSUE
LATIDO_TOKEN=$LATIDO_TOKEN
LATIDO_UPS=${LATIDO_UPS:-}
LATIDO_INTERFAZ_MOVIL=${LATIDO_INTERFAZ_MOVIL:-}
EOF
chmod 600 "$DESTINO/latido.env"
umask 022

echo
echo "-- Prueba en seco: esto es lo que se enviaría --"
set -a; . "$DESTINO/latido.env"; set +a
python3 "$DESTINO/latido.py" --probar
echo

read -rp "¿Programar el cron cada minuto? [s/N] " responder
if [ "${responder,,}" = "s" ]; then
  LINEA="* * * * * set -a; . $DESTINO/latido.env; set +a; /usr/bin/python3 $DESTINO/latido.py >/dev/null 2>&1"
  ( crontab -l 2>/dev/null | grep -v "$DESTINO/latido.py" ; echo "$LINEA" ) | crontab -
  echo "Cron programado. Compruébalo con: crontab -l"
  echo
  echo "En un par de minutos la luz «Sede central» del panel debería pasar a verde:"
  echo "  https://hparedes95.github.io/web_status/"
else
  echo "No se ha tocado el cron. Para hacerlo a mano:"
  echo "  * * * * * set -a; . $DESTINO/latido.env; set +a; /usr/bin/python3 $DESTINO/latido.py"
fi
