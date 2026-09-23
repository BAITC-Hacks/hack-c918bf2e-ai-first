#!/bin/sh
# Writes runtime config so one image works against any backend address.
set -eu
escaped=$(printf '%s' "${API_BASE:-}" | sed 's/\\/\\\\/g; s/"/\\"/g')
printf 'window.__APP_CONFIG__ = { API_BASE: "%s" }\n' "$escaped" > /usr/share/nginx/html/config.js
echo "app-config: API_BASE=${API_BASE:-<empty>}"
