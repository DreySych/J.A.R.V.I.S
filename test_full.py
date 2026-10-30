import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "brain"))

from jarvis_agent import ask_jarvis

print("Test 1: simple greeting")
try:
    result = ask_jarvis("Привет")
    print("RESULT:", result[:200] if result else "(empty)")
except Exception as e:
    print("FAIL:", e)

print("\nTest 2: light control")
try:
    result = ask_jarvis("Джарвис, сделай освещение синим")
    print("RESULT:", result[:200] if result else "(empty)")
except Exception as e:
    print("FAIL:", e)

print("\nTest 3: web_search")
try:
    result = ask_jarvis("Какой курс доллара сегодня")
    print("RESULT:", result[:200] if result else "(empty)")
except Exception as e:
    print("FAIL:", e)
