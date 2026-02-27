from astra_engine.memory.memory_extractor import extract_user_fact

tests = [
    "My favorite color is blue",
    "My favourite color is blue", 
    "I like blue",
    "My favorite food is pizza",
]

print("Testing memory extractor:\n")
for test in tests:
    result = extract_user_fact(test)
    print(f"Input: '{test}'")
    print(f"Result: {result}")
    print("-" * 50)