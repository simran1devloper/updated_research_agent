# test_intent_scoring_final.py
"""
Comprehensive tests for Intent Scoring (Clear vs Vague).
"""
from unittest.mock import MagicMock
import sys

# Mock memory manager
mock_memory = MagicMock()
mock_memory.get_context.return_value = ["Mocked context"]
sys.modules["memory"] = MagicMock(memory=mock_memory)

from main import build_agent

PASS = "✅ PASS"
FAIL = "❌ FAIL"

def run_query(app, query: str, label: str):
    print(f"\n{'─'*60}")
    print(f"[{label}] Query: {query!r}")
    print(f"{'─'*60}")

    initial_state = {"query": query, "history": []}
    nodes_executed = []
    final_state = {}

    try:
        config = {"configurable": {"thread_id": f"test_{label}_{query[:10]}"}}
        for output in app.stream(initial_state, config=config):
            for key, value in output.items():
                nodes_executed.append(key)
                print(f"  ✔ Node executed: [{key}]")
                final_state.update(value) 
    except Exception as e:
        print(f"  ❌ Error during execution: {e}")

    return nodes_executed, final_state

def test_concept_query(app):
    print("\n" + "="*60)
    print("TEST 1: Concept Query (Simple) → Should skip clarification_node")
    print("="*60)
    
    query = "What is cdc?"
    nodes, state = run_query(app, query, "CONCEPT")
    
    intent_orchestrator_hit = "intent_orchestrator" in nodes
    score = state.get("confidence_score", 0.0)
    
    print(f"  intent_orchestrator hit : {PASS if intent_orchestrator_hit else FAIL}")
    print(f"  Confidence Score       : {score}")
    
    return intent_orchestrator_hit and "planner" in nodes and score >= 0.8

def test_vague_query(app):
    print("\n" + "="*60)
    print("TEST 2: Vague Query → Should hit clarification_node")
    print("="*60)
    
    query = "help me with my code"
    nodes, state = run_query(app, query, "VAGUE")
    
    intent_orchestrator_hit = "intent_orchestrator" in nodes
    clarify_user_hit = "clarify_user" in nodes
    score = state.get("confidence_score", 0.0)
    
    print(f"  intent_orchestrator hit : {PASS if intent_orchestrator_hit else FAIL}")
    print(f"  clarify_user hit        : {PASS if clarify_user_hit else FAIL}")
    print(f"  Confidence Score       : {score}")
    
    return intent_orchestrator_hit and clarify_user_hit and score < 0.8

def main():
    print("🚀 Building agent for final scoring tests...")
    try:
        app = build_agent()
    except Exception as e:
        print(f"❌ Failed to build agent: {e}")
        sys.exit(1)

    results = {
        "Concept Query Path": test_concept_query(app),
        "Vague Query Path": test_vague_query(app),
    }

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    all_pass = True
    for test_name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {test_name}")
        if not passed:
            all_pass = False
    
    if not all_pass:
        sys.exit(1)

if __name__ == "__main__":
    main()
