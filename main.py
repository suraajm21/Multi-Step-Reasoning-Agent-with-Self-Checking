import json
from agent import ReasoningAgent

def run_tests():
    print("Initializing Agent with Llama 3.1:8b (Local)...")
    agent = ReasoningAgent()

    # Required: 5-10 Easy, 3-5 Tricky [cite: 102-103]
    test_questions = [
        # --- EASY CASES ---
        "1. Alice has 3 red apples and twice as many green apples as red. How many apples total?",
        "2. If a train leaves at 14:30 and arrives at 18:05, how long is the journey?",
        "3. What is 25 multiplied by 4, plus 10?",
        "4. A rectangular garden is 10 meters long and 5 meters wide. What is its perimeter?",
        "5. If I have 100 dollars and spend 45, how much do I have left?",
        
        # --- TRICKY CASES ---
        "6. A meeting needs 60 minutes. There are free slots: 09:00-09:30, 09:45-10:30, 11:00-12:00. Which slots can fit the meeting?",
        "7. I have 5 items. I add 2, then double the total, then subtract 4. What is the final number?",
        "8. (Ambiguous) John runs faster than Bob. Bob runs faster than Mike. Who runs the slowest?"
    ]

    print(f"{'='*20} RUNNING TEST SUITE {'='*20}")

    for q in test_questions:
        print(f"\nProcessing: {q}")
        result = agent.solve(q)
        
        # Printing Requirement [cite: 111]
        print(json.dumps(result, indent=2))
        
        if result['status'] == 'success':
            print("✅ PASSED")
        else:
            print("❌ FAILED")

if __name__ == "__main__":
    run_tests()