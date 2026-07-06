#!/usr/bin/env sh
set -e

if [ -z "$API_BASE_URL" ]; then
  echo "ERROR: Set API_BASE_URL in Vercel project settings (your Render backend URL, e.g. https://your-api.onrender.com)."
  exit 1
fi

cat > js/config.js << EOF
// Auto-generated at deploy time from the API_BASE_URL environment variable.
const API_BASE_URL = "${API_BASE_URL}";
EOF

echo "Wrote js/config.js with API_BASE_URL=${API_BASE_URL}"
