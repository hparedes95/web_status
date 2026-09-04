#!/usr/bin/env bash
# Comprueba qué fuentes del catálogo (docs/02-catalogo-fuentes.md) responden hoy.
# Es el entregable 0.2 del plan: NO estimar ninguna fase sin haber pasado esto.
#
#   ./scripts/check-sources.sh            # todo el catálogo
#   ./scripts/check-sources.sh anthropic  # solo lo que case con el patrón
#
# Salida: OK (responde y parece JSON/RSS válido) | HTTP nnn | SIN RESPUESTA

set -uo pipefail

FILTRO="${1:-}"
TIMEOUT=12
UA="web-status-check/1.0 (comprobacion de disponibilidad de feed)"
ok=0; ko=0

# Páginas que siguen el patrón Statuspage: basta el dominio.
STATUSPAGE=(
  "Anthropic / Claude|status.anthropic.com"
  "OpenAI / ChatGPT|status.openai.com"
  "GitHub + Copilot|www.githubstatus.com"
  "Cloudflare|www.cloudflarestatus.com"
  "Atlassian|status.atlassian.com"
  "Zoom|status.zoom.us"
  "Dropbox|status.dropbox.com"
  "Twilio|status.twilio.com"
)

# Fuentes con formato propio: nombre|url|tipo
OTRAS=(
  "Slack|https://slack-status.com/api/v2.0.0/current|json"
  "Google Cloud|https://status.cloud.google.com/incidents.json|json"
  "Google Workspace|https://www.google.com/appsstatus/dashboard/incidents.json|json"
  "AWS Health|https://health.aws.amazon.com/public/currentevents|json"
  "Azure (RSS)|https://azure.status.microsoft/en-us/status/feed/|rss"
  "Microsoft 365 (RSS)|https://status.cloud.microsoft/api/feed|rss"
)

probar() { # nombre url tipo_esperado
  local nombre="$1" url="$2" tipo="${3:-json}" cuerpo code
  cuerpo="$(mktemp)"
  code=$(curl -sSL -o "$cuerpo" -w '%{http_code}' --max-time "$TIMEOUT" \
              -H "User-Agent: $UA" -H 'Accept: application/json, application/rss+xml, */*' \
              "$url" 2>/dev/null) || code=000

  local veredicto
  if [ "$code" = "000" ]; then
    veredicto="SIN RESPUESTA (red, DNS o bloqueo de salida)"; ko=$((ko+1))
  elif [ "$code" != "200" ]; then
    veredicto="HTTP $code"; ko=$((ko+1))
  else
    local ini; ini=$(head -c 400 "$cuerpo" | tr -d '\r\n[:space:]' | cut -c1-1)
    case "$tipo:$ini" in
      json:'{'|json:'[') veredicto="OK  (JSON)"; ok=$((ok+1)) ;;
      rss:'<')           veredicto="OK  (XML/RSS)"; ok=$((ok+1)) ;;
      *)                 veredicto="200 pero el cuerpo no parece $tipo (¿HTML de error?)"; ko=$((ko+1)) ;;
    esac
  fi
  printf '  %-26s %s\n' "$nombre" "$veredicto"
  rm -f "$cuerpo"
}

casa() { [ -z "$FILTRO" ] && return 0; printf '%s' "$1" | grep -qi -- "$FILTRO"; }

echo
echo "=== Patrón Statuspage (/api/v2/summary.json) ==="
for e in "${STATUSPAGE[@]}"; do
  nombre="${e%%|*}"; dominio="${e##*|}"
  casa "$nombre$dominio" || continue
  probar "$nombre" "https://$dominio/api/v2/summary.json" json
done

echo
echo "=== Formato propio ==="
for e in "${OTRAS[@]}"; do
  IFS='|' read -r nombre url tipo <<< "$e"
  casa "$nombre$url" || continue
  probar "$nombre" "$url" "$tipo"
done

echo
echo "=== Resultado: $ok correctas, $ko con problemas ==="
echo "Actualiza docs/02-catalogo-fuentes.md con lo que responda de verdad."
echo "Recuerda: Azure Resource Health y Microsoft Graph NO se comprueban aquí,"
echo "necesitan autenticación (ver tarea 0.4 del plan)."
echo
[ "$ko" -eq 0 ]
