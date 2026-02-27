from memory import memory
import time

def test_memory():
    print("🚀 Starting Memory Verification...")
    
    # 1. Add a specific memory
    test_fact = "User prefers explanations in Python with type hints."
    print(f"📝 Adding valid memory: '{test_fact}'")
    memory.add_memory(test_fact, metadata={"source": "test_script"})
    
    # Allow some time for persistence (though Qdrant is usually instant locally)
    time.sleep(1)
    
    # 2. Query for that memory
    print("🔍 Querying memory...")
    results = memory.get_context("What are the user's coding preferences?")
    
    print(f"📊 Results: {results}")
    
    found = any(test_fact in doc for doc in results)
    
    if found:
        print("✅ SUCCESS: Memory was retrieved correctly.")
    else:
        print("❌ FAILURE: Memory was text not found in results.")

if __name__ == "__main__":
    test_memory()
