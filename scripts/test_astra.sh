#!/bin/bash

echo "🧪 ASTRA Testing Suite"
echo "======================="
echo ""

BASE_URL="http://127.0.0.1:5050"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
curl -s "$BASE_URL/health" | jq
echo ""

# Test 2: Creator Question (Shortcut)
echo -e "${BLUE}Test 2: Creator Question${NC}"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Who made you?"}' | jq -r '.reply'
echo ""

# Test 3: Technical Question
echo -e "${BLUE}Test 3: Technical Question${NC}"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is gradient descent?"}' | jq -r '.reply'
echo ""

# Test 4: Memory Storage
echo -e "${BLUE}Test 4: Memory Storage${NC}"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"My favorite color is blue"}' | jq -r '.reply'
echo ""

# Test 5: Memory Recall
echo -e "${BLUE}Test 5: Memory Recall${NC}"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is my favorite color?"}' | jq -r '.reply'
echo ""

# Test 6: Emotion Detection
echo -e "${BLUE}Test 6: Emotion Detection${NC}"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"I am so happy today!"}' | jq '.emotion'
echo ""

echo -e "${GREEN}✅ All tests complete!${NC}"