# test_intent_scoring_v2.py
"""
Tests for the Intent Scoring refinement (Concepts).
"""
from unittest.mock import MagicMock
import sys

# Mock memory manager BEFORE importing anything that uses it
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
                final_state = value 
    except Exception as e:
        print(f"  ❌ Error during execution: {e}")

    return nodes_executed, final_state

def test_concept_query(app):
    print("\n" + "="*60)
    print("TEST: Concept Query → Should skip clarification_node")
    print("="*60)
    
    query = "What is cdc?"
    nodes, state = run_query(app, query, "CONCEPT")
    
    intent_scoring_hit = "intent_scoring" in nodes
    clarification_node_skipped = "clarification_node" not in nodes
    score = state.get("confidence_score", 0.0)
    
    print(f"  intent_scoring executed : {PASS if intent_scoring_hit else FAIL}")
    print(f"  clarification_node skipped: {PASS if clarification_node_skipped else FAIL}")
    print(f"  Confidence Score       : {score}")
    
    return intent_scoring_hit and clarification_node_skipped and score >= 0.8

def main():
    print("🚀 Building agent for scoring tests v2...")
    try:
        app = build_agent()
    except Exception as e:
        print(f"❌ Failed to build agent: {e}")
        sys.exit(1)

    results = {
        "Concept Query Path": test_concept_query(app),
    }

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    for test_name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {test_name}")

if __name__ == "__main__":
    main()
