#!/bin/bash

BASE_URL="http://127.0.0.1:5050"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🧪 ASTRA Detailed Testing Suite"
echo "================================"
echo ""

# Helper function
test_chat() {
    local test_name=$1
    local message=$2
    local expected=$3
    
    echo -e "${BLUE}Test: $test_name${NC}"
    echo "Input: $message"
    
    response=$(curl -s -X POST "$BASE_URL/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\":\"$message\"}")
    
    reply=$(echo $response | jq -r '.reply')
    emotion=$(echo $response | jq -r '.emotion')
    
    echo "Reply: $reply"
    echo "Emotion: $emotion"
    
    if [ ! -z "$expected" ]; then
        if [[ "$reply" == *"$expected"* ]]; then
            echo -e "${GREEN}✓ PASSED${NC}"
        else
            echo -e "${RED}✗ FAILED - Expected: $expected${NC}"
        fi
    fi
    echo "---"
    echo ""
}

# Clear memory first
echo "Clearing memory..."
curl -s -X DELETE "$BASE_URL/memory" > /dev/null
echo ""

# Test 1: Health
echo -e "${BLUE}Test 1: Health Check${NC}"
curl -s "$BASE_URL/health" | jq
echo ""

# Test 2: Creator (Shortcut)
test_chat "Creator Question" "Who made you?" "Arnav"

# Test 3: Store favorite color
test_chat "Store Favorite Color" "My favorite color is blue" ""

# Test 4: Recall favorite color
test_chat "Recall Favorite Color" "What is my favorite color?" "blue"

# Test 5: Store location
test_chat "Store Location" "I live in Delhi" ""

# Test 6: Recall location
test_chat "Recall Location" "Where do I live?" "Delhi"

# Test 7: Emotion - Happy
test_chat "Emotion Detection (Happy)" "I am so happy today!" ""

# Test 8: Technical question
test_chat "Technical Question" "What is machine learning?" ""

# Test 9: General memory
test_chat "General Memory Recall" "What do you know about me?" ""

# Check memory
echo -e "${BLUE}Final Memory State:${NC}"
curl -s "$BASE_URL/memory" | jq '.user_facts'

echo ""
echo -e "${GREEN}✅ All tests complete!${NC}"