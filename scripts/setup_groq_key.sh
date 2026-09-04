#!/usr/bin/env bash
# One-shot Groq key setup + diagnosis + live Copilot test.
#
# Runs entirely on your machine. The key is read with a hidden prompt
# (never echoed, never sent anywhere except directly to Groq's own API
# to test it), written to a local .env (gitignored, never committed),
# and used to restart the backend and prove /copilot/chat actually works.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

echo "=== FraudLens — Groq key setup ==="
echo ""
read -r -s -p "Paste your Groq API key (input hidden, press Enter when done): " GROQ_KEY
echo ""
echo ""

if [ -z "$GROQ_KEY" ]; then
  echo "No key entered. Aborting."
  exit 1
fi

PREFIX="${GROQ_KEY:0:4}"
echo "Key prefix: $PREFIX (should read 'gsk_' — if it doesn't, the paste likely went wrong)"
echo ""

echo "=== Testing directly against Groq (bypassing our app entirely) ==="
echo "--- llama-3.1-8b-instant ---"
SMALL_STATUS=$(curl -s -o /tmp/groq_test_small.json -w "%{http_code}" https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"hi"}]}')
echo "Status: $SMALL_STATUS"

echo "--- llama-3.3-70b-versatile ---"
BIG_STATUS=$(curl -s -o /tmp/groq_test_big.json -w "%{http_code}" https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hi"}]}')
echo "Status: $BIG_STATUS"
echo ""

GROQ_MODEL_LINE=""
if [ "$SMALL_STATUS" != "200" ] && [ "$BIG_STATUS" != "200" ]; then
  echo "=== Neither model worked. Groq itself is rejecting this key. ==="
  echo "This isn't a bug in the app — the direct test bypasses it entirely."
  echo "Response body from the 70B test, for reference:"
  cat /tmp/groq_test_big.json
  echo ""
  echo "Go to https://console.groq.com -> API Keys, generate a FRESH key"
  echo "(don't reuse this one), and re-run this script."
  rm -f /tmp/groq_test_small.json /tmp/groq_test_big.json
  exit 1
elif [ "$BIG_STATUS" != "200" ]; then
  echo "=== llama-3.3-70b-versatile isn't available on this key/account, but the 8B model works. ==="
  echo "Using llama-3.1-8b-instant instead so Copilot has a working model."
  GROQ_MODEL_LINE="GROQ_MODEL=llama-3.1-8b-instant"
else
  echo "=== Both models work. Key is genuinely valid. ==="
fi
rm -f /tmp/groq_test_small.json /tmp/groq_test_big.json
echo ""

echo "=== Writing to .env (gitignored — stays on this machine) ==="
ENV_FILE="$REPO_ROOT/.env"
touch "$ENV_FILE"
grep -v '^GROQ_' "$ENV_FILE" > "${ENV_FILE}.tmp" 2>/dev/null || true
mv "${ENV_FILE}.tmp" "$ENV_FILE"
echo "GROQ_API_KEY=$GROQ_KEY" >> "$ENV_FILE"
if [ -n "$GROQ_MODEL_LINE" ]; then
  echo "$GROQ_MODEL_LINE" >> "$ENV_FILE"
fi
if ! grep -qxF '.env' "$REPO_ROOT/.gitignore" 2>/dev/null; then
  echo ".env" >> "$REPO_ROOT/.gitignore"
fi
echo "Written."
echo ""

echo "=== Restarting the backend with the confirmed-working key ==="
lsof -ti:8001 | xargs kill 2>/dev/null || true
sleep 1

source "$REPO_ROOT/.venv/bin/activate"
set -a
source "$ENV_FILE"
set +a
nohup uvicorn fraudlens.api.main:app --reload --port 8001 > /tmp/fraudlens_api.log 2>&1 &
SERVER_PID=$!
echo "Server starting (PID $SERVER_PID), waiting..."
sleep 4

echo "=== Testing the real /copilot/chat endpoint, end to end ==="
RESP=$(curl -s http://127.0.0.1:8001/copilot/chat -X POST -H "Content-Type: application/json" \
  -d '{"question":"why was this flagged?","txn_id":"TXN-0001"}')
echo "$RESP"
echo ""

if echo "$RESP" | grep -q '"answer"'; then
  echo "=== SUCCESS — Copilot is live and answering for real. ==="
else
  echo "=== Still not working. Check /tmp/fraudlens_api.log for the actual server traceback. ==="
  echo "Last 20 lines:"
  tail -20 /tmp/fraudlens_api.log
fi
