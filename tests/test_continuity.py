from main import build_agent
import uuid

def test_continuity():
    print("Testing Contextual Continuity and Persistence...")
    
    agent = build_agent()
    # Unique thread_id to simulate a fresh session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # query 1: General concept
    print(f"\n--- Turn 1: Initial query ---")
    query1 = "What is a RAG system?"
    state1 = {"query": query1} # history initialized in guard_layer
    
    final_report1 = ""
    for output in agent.stream(state1, config=config):
        for key, value in output.items():
            print(f"✅ Node: {key}")
            if key == "formatter":
                final_report1 = value.get("final_report", "")
    
    # print(f"Report 1: {final_report1[:100]}...")
    
    # query 2: Follow-up (Ambiguous without context)
    print(f"\n--- Turn 2: Follow-up query (should use context) ---")
    query2 = "How to set it up?"
    state2 = {"query": query2}
    
    is_clarified = False
    final_report2 = ""
    execution_path2 = []
    
    for output in agent.stream(state2, config=config):
        for key, value in output.items():
            execution_path2.append(key)
            print(f"✅ Node: {key}")
            if key == "classify":
                is_clarified = value.get("is_clarified")
            if key == "formatter":
                final_report2 = value.get("final_report", "")
    
    print(f"\nExecution Path 2: {execution_path2}")
    print(f"Is Clarified: {is_clarified}")
    
    if "clarify_user" in execution_path2:
        print("❌ FAILED: Agent asked for clarification when context was available.")
    elif is_clarified and "quick_mode" in execution_path2 or "deep_research" in execution_path2:
        print("✅ SUCCESS: Agent recognized follow-up using previous context.")
    else:
        print("❓ UNDETERMINED: Check the execution path.")

if __name__ == "__main__":
    test_continuity()
