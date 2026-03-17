#!/bin/bash
BASE="http://localhost:5050"

# Load API key (without printing it).
# Priority: env var ASTRA_API_KEY, then backend/.env if present.
API_KEY="${ASTRA_API_KEY:-}"
if [ -z "$API_KEY" ] && [ -f "backend/.env" ]; then
  while IFS= read -r line; do
    case "$line" in
      ASTRA_API_KEY=*)
        API_KEY="${line#ASTRA_API_KEY=}"
        ;;
    esac
  done < "backend/.env"
fi

# Build curl auth args only if key exists.
CURL_AUTH_ARGS=()
if [ -n "$API_KEY" ]; then
  CURL_AUTH_ARGS=(-H "X-API-Key: $API_KEY")
fi

# #region agent log
# Log to debug ingest endpoint (never log secrets).
HAS_API_KEY=0
if [ -n "$API_KEY" ]; then HAS_API_KEY=1; fi
BACKEND_UP=0
if curl -sf "$BASE/health" >/dev/null 2>&1; then BACKEND_UP=1; fi
curl -s 'http://127.0.0.1:7482/ingest/9b816707-b54b-4d01-ae5f-e94ebab7cde8' \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Session-Id: 4c1d8e' \
  --data "{\"sessionId\":\"4c1d8e\",\"runId\":\"pre-fix\",\"hypothesisId\":\"H1-auth-header-missing\",\"location\":\"test_astra.sh:auth\",\"message\":\"Loaded ASTRA_API_KEY for smoke test\",\"data\":{\"hasApiKey\":$HAS_API_KEY},\"timestamp\":$(date +%s000)}" \
  >/dev/null 2>&1 || true
curl -s 'http://127.0.0.1:7482/ingest/9b816707-b54b-4d01-ae5f-e94ebab7cde8' \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Session-Id: 4c1d8e' \
  --data "{\"sessionId\":\"4c1d8e\",\"runId\":\"pre-fix\",\"hypothesisId\":\"H2-backend-down\",\"location\":\"test_astra.sh:reachability\",\"message\":\"Backend reachability check before smoke run\",\"data\":{\"healthReachable\":$BACKEND_UP},\"timestamp\":$(date +%s000)}" \
  >/dev/null 2>&1 || true
# #endregion agent log

if [ "$BACKEND_UP" -ne 1 ]; then
  echo ""
  echo "❌ Backend not reachable at $BASE"
  echo "Start the backend (port 5050) and re-run: bash ./test_astra.sh"
  exit 1
fi

echo "=============================="
echo "🧪 ASTRA FULL FEATURE TEST"
echo "=============================="

run() {
  echo ""
  echo "▶ $1"
  curl -s -X ${3:-GET} "${CURL_AUTH_ARGS[@]}" "$BASE/$2" \
    ${4:+-H "Content-Type: application/json" -d "$4"} \
    | python3 -m json.tool 2>/dev/null || echo "FAILED"
}

run "Health"          "health"
run "System Stats"    "system/stats"
run "Model Info"      "model/info"
run "Model List"      "model/list"
run "Mode Current"    "mode/current"
run "Mode List"       "mode/list"
run "Capabilities"    "capabilities"
run "Memory"          "memory"
run "Memory Facts"    "memory/facts"
run "Knowledge Stats" "knowledge/stats"
run "Vision Status"   "vision/status"
run "Realtime Status" "realtime/status"
run "Chat Casual"     "chat" "POST" '{"message":"hey what is up"}'
run "Chat Technical"  "chat" "POST" '{"message":"what is a REST API"}'
run "Chat Reasoning"  "chat" "POST" '{"message":"why is recursion sometimes bad"}'
run "Chat Coding"     "chat" "POST" '{"message":"write a fibonacci function in python"}'
run "Memory Store"    "chat" "POST" '{"message":"my name is Alex and I love coding"}'
run "Memory Recall"   "chat" "POST" '{"message":"what is my name"}'

echo ""
echo "=============================="
echo "✅ TEST COMPLETE"
echo "=============================="
