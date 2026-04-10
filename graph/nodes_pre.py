from langchain_ollama import ChatOllama
from state import AgentState, IntentOutput
from config import Config
from memory import memory
from prompts.clarification_prompts import INTENT_ORCHESTRATOR_PROMPT
# Removed unused import: from prompts.analysis_prompts import QUERY_INTEGRITY_PROMPT
import uuid

llm = ChatOllama(model=Config.MODEL_NAME, base_url=Config.OLLAMA_BASE_URL)
structured_llm = llm.with_structured_output(IntentOutput)

def guard_layer(state: AgentState):
    """
    Guard Budget and Token and telemetry.
    Initializes the state if needed.
    """
    return {
        "token_usage": 0,
        "budget_limit": 5000,
        "research_data": [],
        "gaps": [],
        "iterations": 0,
        "clarification_question": "",
        "history": [{"role": "user", "content": state["query"]}],
        "query_id": str(uuid.uuid4())  # Generate unique ID for streaming
    }




def intent_orchestrator(state: AgentState):
    """
    Unified Intent classification, scoring, and clarification orchestration.
    """
    history = state.get("history", [])
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-5:]]) if history else "No history."

    chain = INTENT_ORCHESTRATOR_PROMPT | structured_llm
    
    try:
        response = chain.invoke({"query": state["query"], "history": history_text})
        
        score = response.confidence_score
        is_clarified = response.is_clear
        clarification_question = response.clarification_question
        raw_category = response.category

        category_map = {
            "BUG": "Bug Fix",
            "ARCHITECTURE": "Architecture",
            "CONCEPT": "General Question",
            "COMPARISON": "Research",
            "RESEARCH": "Research",
            "GENERAL": "General Question",
            "NON_TECHNICAL": "Non-Technical",
        }
        intent = category_map.get(raw_category.upper(), "Research")

    except Exception as e:
        print(f"DEBUG [intent_orchestrator] Structured output failed ({e}), using fallback.")
        score = 0.5
        is_clarified = False
        clarification_question = "Could you please provide more context about your query?"
        intent = "Research"

    return {
        "confidence_score": score,
        "intent": intent,
        "is_clarified": is_clarified,
        "clarification_question": clarification_question,
        "token_usage": state.get("token_usage", 0),
    }

def context_retrieval(state: AgentState):
    """
    Memory and context retrieval vector DB.
    """
    query = state["query"]
    print(f"DEBUG: Retrieving context for: {query}")

    context_docs = memory.get_context(query)
    formatted_context = "\n".join(context_docs) if context_docs else "No prior context found."

    return {"context": [formatted_context]}

# Removed intent_classifier as it is merged into intent_orchestrator