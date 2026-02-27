# test_clarification.py
"""
Tests for the Query Clarification feature.

Test 1: Ambiguous/vague query → should route to clarify_user node
Test 2: Clear technical query → should route to planner (skipping clarify_user)
"""
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import build_agent
import sys


PASS = "✅ PASS"
FAIL = "❌ FAIL"


def run_query(app, query: str, label: str):
    """Helper: runs a query through the agent and returns (nodes_executed, final_state)."""
    print(f"\n{'─'*60}")
    print(f"[{label}] Query: {query!r}")
    print(f"{'─'*60}")

    initial_state = {"query": query, "history": []}
    nodes_executed = []
    final_state = {}

    try:
        config = {"configurable": {"thread_id": f"test_{label}"}}
        for output in app.stream(initial_state, config=config):
            for key, value in output.items():
                nodes_executed.append(key)
                print(f"  ✔ Node executed: [{key}]")
                final_state.update(value)  # Accumulate state updates
    except Exception as e:
        print(f"  ❌ Error during execution: {e}")
        sys.exit(1)

    return nodes_executed, final_state


def test_ambiguous_query(app):
    """
    A vague query with no technical context should trigger the clarify_user node
    and should NOT continue to the planner / formatter.
    """
    vague_queries = [
        "fix my code",
        "help",
        "it's broken, what do I do?",
        "make it faster",
    ]

    print("\n" + "="*60)
    print("TEST 1: Ambiguous Query → Clarification Path")
    print("="*60)

    all_passed = True
    for query in vague_queries:
        nodes, state = run_query(app, query, "AMBIGUOUS")

        went_to_clarify = "clarify_user" in nodes
        skipped_planner = "planner" not in nodes
        skipped_formatter = "formatter" not in nodes
        mode_correct = state.get("mode") == "clarification"
        has_report = bool(state.get("final_report", "").strip())

        result = went_to_clarify and skipped_planner and skipped_formatter and has_report

        print(f"\n  clarify_user executed : {PASS if went_to_clarify else FAIL}")
        print(f"  planner skipped       : {PASS if skipped_planner else FAIL}")
        print(f"  formatter skipped     : {PASS if skipped_formatter else FAIL}")
        print(f"  mode='clarification'  : {PASS if mode_correct else FAIL}")
        print(f"  has clarification msg : {PASS if has_report else FAIL}")
        print(f"  → Overall: {'PASS' if result else 'FAIL'}")

        if not result:
            all_passed = False

    return all_passed


def test_clear_query(app):
    """
    A specific, well-formed technical query should skip clarify_user
    and proceed through the normal research pipeline.
    """
    clear_queries = [
        "What are the trade-offs between Redis and Memcached for session storage in a high-traffic Python web app?",
        "Explain how the Linux kernel scheduler implements CFS (Completely Fair Scheduler).",
    ]

    print("\n" + "="*60)
    print("TEST 2: Clear Technical Query → Normal Research Path")
    print("="*60)

    all_passed = True
    for query in clear_queries:
        nodes, state = run_query(app, query, "CLEAR")

        went_to_planner = "planner" in nodes
        skipped_clarify = "clarify_user" not in nodes
        has_report = bool(state.get("final_report", "").strip())

        result = went_to_planner and skipped_clarify and has_report

        print(f"\n  planner executed      : {PASS if went_to_planner else FAIL}")
        print(f"  clarify_user skipped  : {PASS if skipped_clarify else FAIL}")
        print(f"  has final report      : {PASS if has_report else FAIL}")
        print(f"  → Overall: {'PASS' if result else 'FAIL'}")

        if not result:
            all_passed = False

    return all_passed


def test_clarification_fields(app):
    """
    Verify that the intent_classifier properly populates
    clarification_question in state for a vague query.
    """
    print("\n" + "="*60)
    print("TEST 3: State Fields — clarification_question Populated")
    print("="*60)

    query = "help me with the thing"
    initial_state = {"query": query, "history": []}

    # Capture intent_orchestrator node output specifically
    orchestrator_state = {}
    config = {"configurable": {"thread_id": "test_fields"}}
    for output in app.stream(initial_state, config=config):
        for key, value in output.items():
            if key == "intent_orchestrator":
                orchestrator_state = value
                print(f"  ✔ Node: [intent_orchestrator] is_clarified={value.get('is_clarified')}")
            # Stop after clarify_user
            if key == "clarify_user":
                break

    cq = orchestrator_state.get("clarification_question", "")
    is_c = orchestrator_state.get("is_clarified", True)

    print(f"  is_clarified=False      : {PASS if not is_c else FAIL} (got: {is_c})")
    print(f"  clarification_question  : {PASS if cq else FAIL} (got: {cq!r})")

    return (not is_c) and bool(cq)


def main():
    print("🚀 Building agent for clarification tests...")
    try:
        app = build_agent()
    except Exception as e:
        print(f"❌ Failed to build agent: {e}")
        sys.exit(1)

    results = {
        "Ambiguous Query → Clarification": test_ambiguous_query(app),
        "Clear Query → Research Path": test_clear_query(app),
        "State Fields Populated": test_clarification_fields(app),
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

    print()
    if all_pass:
        print("🎉 All clarification tests passed!")
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
