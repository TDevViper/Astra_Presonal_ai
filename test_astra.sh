#!/bin/bash
BASE="http://localhost:5050"
echo "=============================="
echo "🧪 ASTRA FULL FEATURE TEST"
echo "=============================="

run() {
  echo ""
  echo "▶ $1"
  curl -s -X ${3:-GET} $BASE/$2 \
    ${4:+-H "Content-Type: application/json" -d "$4"} | python3 -m json.tool 2>/dev/null || echo "FAILED"
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
