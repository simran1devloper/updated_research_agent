from main import build_agent
import uuid

def test_persistence():
    print("Testing Persistent Multi-Session Context...")
    
    agent = build_agent()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Step 1: Initial query
    print(f"\n--- Step 1: Sending initial query with thread_id: {thread_id} ---")
    query1 = "What is the capital of France?"
    state1 = {"query": query1, "history": []}
    
    final_report1 = ""
    for output in agent.stream(state1, config=config):
        for key, value in output.items():
            print(f"Node completed: {key}")
            if key == "formatter":
                final_report1 = value.get("final_report", "")
    
    print(f"Report 1: {final_report1[:50]}...")
    
    # Step 2: Resume with same thread_id
    print(f"\n--- Step 2: Resuming with same thread_id: {thread_id} ---")
    query2 = "And what is its largest museum?"
    state2 = {"query": query2, "history": []} # History should be pulled from checkpointer
    
    final_report2 = ""
    for output in agent.stream(state2, config=config):
        for key, value in output.items():
            print(f"Node completed: {key}")
            if key == "formatter":
                final_report2 = value.get("final_report", "")
    
    print(f"Report 2: {final_report2[:50]}...")
    
    # Step 3: Check memory (should contain query1/report1 context)
    # This is partially verified by the agent's ability to answer query2 correctly.
    
    print("\nPersistence test completed successfully if the agent correctly followed up.")

if __name__ == "__main__":
    test_persistence()
