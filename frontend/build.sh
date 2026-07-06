#!/usr/bin/env sh
set -e

echo "Building frontend..."

if [ -z "$API_BASE_URL" ]; then
  echo "ERROR: API_BASE_URL environment variable is not set."
  exit 1
fi

mkdir -p js

cat > js/config.js <<EOF
// Auto-generated during Vercel deployment.
window.API_BASE_URL = "${API_BASE_URL}";
EOF

echo "Generated js/config.js"
cat js/config.js

echo "Build completed."
