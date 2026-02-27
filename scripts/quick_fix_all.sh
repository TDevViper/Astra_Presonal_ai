#!/bin/bash

echo "🔧 Applying all fixes..."

# 1. Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "⚠️  Ollama is not running!"
    echo "Starting Ollama in background..."
    ollama serve &
    sleep 2
fi

# 2. Test Ollama
if ollama list > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama failed to start"
    echo "Run manually: ollama serve"
fi

# 3. Check imports in refinement.py
if grep -q "from astra_engine.utils.limiter import limit_words" astra_engine/reflection/refinement.py; then
    echo "✅ refinement.py imports are correct"
else
    echo "⚠️  Missing import in refinement.py"
    echo "Add this line at the top:"
    echo "from astra_engine.utils.limiter import limit_words"
fi

echo ""
echo "Now restart your backend!"
