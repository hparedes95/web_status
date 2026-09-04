#!/usr/bin/env bash
# Comprueba cuáles de las seis fuentes automáticas del panel responden hoy.
# Es la tarea 1 del plan: NO dar por buena la estimación sin haber pasado esto.
#
#   ./scripts/check-sources.sh
#
# Salida: OK | HTTP nnn | SIN RESPUESTA

set -uo pipefail

TIMEOUT=12
UA="web-status-check/1.0 (comprobacion de disponibilidad de feed)"
ok=0; ko=0

# nombre|url|tipo esperado
FUENTES=(
  "Claude|https://status.anthropic.com/api/v2/summary.json|json"
  "ChatGPT|https://status.openai.com/api/v2/summary.json|json"
  "GitHub Copilot|https://www.githubstatus.com/api/v2/summary.json|json"
  "Azure|https://azure.status.microsoft/en-us/status/feed/|rss"
  "AWS|https://health.aws.amazon.com/public/currentevents|json"
  "Microsoft 365|https://status.cloud.microsoft/api/feed|rss"
)

for entrada in "${FUENTES[@]}"; do
  IFS='|' read -r nombre url tipo <<< "$entrada"
  cuerpo="$(mktemp)"
  code=$(curl -sSL -o "$cuerpo" -w '%{http_code}' --max-time "$TIMEOUT" \
              -H "User-Agent: $UA" -H 'Accept: application/json, application/rss+xml, */*' \
              "$url" 2>/dev/null) || code=000

  if [ "$code" = "000" ]; then
    veredicto="SIN RESPUESTA (red, DNS o bloqueo de salida)"; ko=$((ko+1))
  elif [ "$code" != "200" ]; then
    veredicto="HTTP $code"; ko=$((ko+1))
  else
    ini=$(head -c 400 "$cuerpo" | tr -d '\r\n[:space:]' | cut -c1-1)
    case "$tipo:$ini" in
      json:'{'|json:'[') veredicto="OK  (JSON)"; ok=$((ok+1)) ;;
      rss:'<')           veredicto="OK  (XML/RSS)"; ok=$((ok+1)) ;;
      *)                 veredicto="200 pero el cuerpo no parece $tipo"; ko=$((ko+1)) ;;
    esac
  fi
  printf '  %-18s %s\n' "$nombre" "$veredicto"
  rm -f "$cuerpo"
done

echo
echo "  $ok de 6 fuentes correctas."
echo
echo "  Actualiza docs/02-fuentes.md con lo que responda de verdad."
echo "  Si falla Microsoft 365, hay que decidir la opcion B (Graph): ver docs/02-fuentes.md."
echo "  Telefonica, Vodafone y energia no se comprueban: no tienen API, son botones manuales."
echo
[ "$ko" -eq 0 ]
