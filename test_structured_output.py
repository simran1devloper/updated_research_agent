from graph.nodes_pre import intent_orchestrator
from graph.nodes_exec import gap_analysis_node
from state import AgentState
import json

def test_intent_orchestrator():
    print("\n--- Testing intent_orchestrator ---")
    state: AgentState = {
        "query": "How do I fix a bug in my React app?",
        "history": [],
        "token_usage": 0
    }
    result = intent_orchestrator(state)
    print(f"Result: {json.dumps(result, indent=2)}")
    assert "intent" in result
    assert "confidence_score" in result
    assert "is_clarified" in result

def test_gap_analysis():
    print("\n--- Testing gap_analysis_node ---")
    state: AgentState = {
        "query": "Compare React and Vue performance",
        "research_data": [{"content": "React uses a virtual DOM. Vue also uses a virtual DOM but with a different reactivity system.", "source": "Web Search"}],
        "history": [],
        "token_usage": 0
    }
    result = gap_analysis_node(state)
    print(f"Result: {json.dumps(result, indent=2)}")
    assert "confidence_score" in result
    assert "gaps" in result

if __name__ == "__main__":
    try:
        test_intent_orchestrator()
        test_gap_analysis()
        print("\n✅ All structured output tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
