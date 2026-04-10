# graph/nodes_exec.py
from langchain_ollama import ChatOllama
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState, GapAnalysisOutput
from config import Config
import os
import re
from prompts.research_prompts import GAP_ANALYSIS_PROMPT, RESEARCH_SYNTHESIS_PROMPT
from utils.streaming import get_streaming_buffer

llm = ChatOllama(model=Config.MODEL_NAME, base_url=Config.OLLAMA_BASE_URL)
structured_llm_gap = llm.with_structured_output(GapAnalysisOutput)

# Custom DDG Tool to bypass langchain-community import issues
from duckduckgo_search import DDGS

class CustomDuckDuckGoSearch:
    def invoke(self, query):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                return str(results)
        except Exception as e:
            return f"Search error: {e}"

# Initialize Search Tools
tavily_api_key = os.getenv("TAVILY_API_KEY")
if tavily_api_key:
    search_tool = TavilySearchResults(max_results=3)
else:
    search_tool = CustomDuckDuckGoSearch()


def planner_router(state: AgentState):
    """
    Planner and router. Decides between 'quick' and 'deep' mode.
    """
    history = state.get("history", [])
    history_text = ""
    if history:
        history_text = "\n\nPrevious conversation:\n" + "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in history[-4:]
        ]) + "\n"

    prompt = ChatPromptTemplate.from_template(
        "Analyze the query complexity. "
        "If it requires simple fact checking or a short code snippet, choose 'quick'. "
        "If it requires extensive research, comparison, or architectural design, choose 'deep'. "
        "Return ONLY the single word: 'quick' or 'deep'.\n\n"
        "{history_context}"
        "Current Query: {query}"
    )
    chain = prompt | llm
    response = chain.invoke({"query": state["query"], "history_context": history_text})
    mode_raw = response.content.strip().lower()

    tokens_used = 0
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        tokens_used = response.usage_metadata.get('total_tokens', 0)

    mode = "deep" if "deep" in mode_raw else "quick"
    return {"mode": mode, "token_usage": state.get("token_usage", 0) + tokens_used}


def identify_authoritative_domains(query: str) -> list:
    """
    Identifies upstream official documentation domains using LLM guidance
    to avoid vendor-specific mirrors.
    """
    # 1. Specialized prompt for domain discovery
    prompt = f"""Identify the SINGLE official upstream project documentation domain for: "{query}".
    EXCLUDE vendor-specific sites like redhat.com, confluent.io, cloudera.com, microsoft.com.
    ONLY return the clean domain name (e.g., debezium.io, postgresql.org).
    If multiple apply, return comma-separated. If unknown, return NONE.
    """
    
    try:
        response = llm.invoke([SystemMessage(content=prompt)]).content.strip()
        if "NONE" in response.upper():
            return []
        
        # Clean response
        discovered = [d.strip() for d in response.split(",") if "." in d]
        
        # 2. Add fallback for common tech if discovery is weak
        COMMON_FALLBACKS = {
            "debezium": "debezium.io",
            "flink": "flink.apache.org",
            "kafka": "kafka.apache.org",
            "spark": "spark.apache.org",
            "kubernetes": "kubernetes.io",
            "postgresql": "postgresql.org"
        }
        
        query_lower = query.lower()
        for tech, domain in COMMON_FALLBACKS.items():
            if tech in query_lower and domain not in discovered:
                discovered.append(domain)
                
        return discovered
    except Exception as e:
        print(f"DEBUG: Domain discovery failed: {e}")
        return []


def quick_mode_executor(state: AgentState):
    """
    Quick mode executor with token-by-token streaming.
    """
    query_id = state.get("query_id", "")
    buffer = get_streaming_buffer(query_id) if query_id else None

    full_response = ""

    # Build conversation history for context
    history = state.get("history", [])
    messages = []

    # Add conversation history (skip the very last user message — it's the current query)
    for msg in history[-6:]:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            messages.append(SystemMessage(content=msg['content']))

    # Add current query if not already last in history
    if not messages or not isinstance(messages[-1], HumanMessage) or messages[-1].content != state["query"]:
        messages.append(HumanMessage(content=state["query"]))

    # Stream response
    for chunk in llm.stream(messages):
        token = chunk.content
        full_response += token
        if buffer:
            buffer.add_chunk(token)

    if buffer:
        buffer.mark_complete()

    tokens_used = len(full_response.split()) * 2  # Rough estimate

    # Basic cleaning
    full_response = full_response.strip()
    # If the LLM still wrapped it in markdown code block, strip it
    full_response = re.sub(r'^```(?:markdown|text)?\s*\n?', '', full_response, flags=re.IGNORECASE)
    full_response = re.sub(r'\n?```\s*$', '', full_response)

    return {
        "research_data": [{"content": full_response, "source": "LLM Knowledge"}],
        "final_report": full_response.strip(),
        "token_usage": state.get("token_usage", 0) + tokens_used,
        "confidence_score": 0.9,  # Quick mode is always confident
    }


def deep_mode_orchestrator(state: AgentState):
    """
    Two-Pass Domain-Authoritative Search:
    1. Phase 1: Search ONLY official domains.
    2. Phase 2: If gaps remain, search general web.
    """
    query = state["query"]
    iteration = state.get("iterations", 0)
    existing_data = state.get("research_data", [])

    # Identify authoritative domains
    official_domains = identify_authoritative_domains(query)
    
    print(f"DEBUG [deep_mode]: Authoritative domains identified: {official_domains}")

    new_research_data = []

    try:
        if isinstance(search_tool, TavilySearchResults):
            # STAGE 1: Deep Reference Scouting (Official First)
            if official_domains:
                # We do a VERY targeted search for documentation/reference pages
                scout_query = f"{query} site:{official_domains[0]} documentation reference"
                print(f"DEBUG [deep_mode]: Stage 1 (Scouting) - Query: {scout_query!r}")
                
                results = search_tool.invoke({
                    "query": scout_query,
                    "include_domains": official_domains,
                    "search_depth": "advanced"
                })
                
                if isinstance(results, list):
                    for r in results:
                        if isinstance(r, dict):
                            new_research_data.append({
                                "content": r.get('content', r.get('snippet', '')),
                                "source": f"[OFFICIAL DOCS] {r.get('title', 'Untitled')}",
                                "url": r.get('url', '')
                            })

            # STAGE 2: Qualitative Evidence Scouting (Experiences & Case Studies)
            if len(new_research_data) < 4:
                print(f"DEBUG [deep_mode]: Stage 2 - Searching for developer experiences...")
                experience_query = f"{query} implementation guide case study production experience troubleshooting"
                results = search_tool.invoke({
                    "query": experience_query,
                    "exclude_domains": ["redhat.com", "medium.com", "stackoverflow.com", "freecodecamp.org"],
                    "search_depth": "advanced"
                })
                
                if isinstance(results, list):
                    for r in results:
                        if isinstance(r, dict):
                            # Label as COMMUNITY for the qualitative section
                            new_research_data.append({
                                "content": r.get('content', r.get('snippet', '')),
                                "source": f"[COMMUNITY EXPERIENCES] {r.get('title', 'Developer Blog')}",
                                "url": r.get('url', '')
                            })
        else:
            # Fallback for DDG
            content = search_tool.invoke(f"site:{official_domains[0]} {query}" if official_domains else query)
            new_research_data = [{"content": content, "source": "[DOCS] Official", "url": ""}]

    except Exception as e:
        print(f"ERROR [deep_mode]: Search failed: {e}")
        new_research_data = [{"content": f"Search failed: {e}", "source": "Error", "url": ""}]

    return {
        "research_data": existing_data + new_research_data,
        "iterations": iteration + 1,
    }


def gap_analysis_node(state: AgentState):
    """
    Gap analysis: checks research quality and identifies what's still missing.
    """
    data = state.get("research_data", [])
    combined_content = "\n".join([d["content"] for d in data])

    history = state.get("history", [])
    history_text = ""
    if history:
        history_text = "\nConversation context: " + "; ".join([
            f"{msg['role']}: {msg['content'][:100]}" for msg in history[-3:]
        ])

    chain = GAP_ANALYSIS_PROMPT | structured_llm_gap
    
    try:
        response = chain.invoke({
            "query": state["query"] + history_text,
            "research_data": combined_content[:5000]
        })
        score = response.confidence_score
        gaps = response.gaps
    except Exception as e:
        print(f"DEBUG [gap_analysis] Structured output failed ({e}), using fallback.")
        score = 0.5
        gaps = []

    # Clamp score
    score = max(0.0, min(1.0, score))

    print(f"DEBUG [gap_analysis]: Parsed score={score}, gaps={gaps}")

    return {
        "confidence_score": score,
        "research_confidence_score": score,
        "gaps": gaps,
        "token_usage": state.get("token_usage", 0),
    }


def inject_verified_links(llm_report, url_map):
    """
    Phase 4: Post-Processing (The "Truth Layer")
    Finds [1], [2] in text and replaces them with [[Source N]](url).
    """
    import re
    
    def replacement(match):
        ref_id_str = match.group(1)
        try:
            ref_id = int(ref_id_str)
            if ref_id in url_map:
                url = url_map[ref_id]
                return f"[[Source {ref_id}]]({url})"
        except ValueError:
            pass
        return match.group(0) # Keep as is if ID not valid

    # Pattern to find [1], [2], etc.
    return re.sub(r'\[(\d+)\]', replacement, llm_report)


def structured_synthesis_node(state: AgentState):
    """
    Structured synthesis (Phase 2 & Phase 4):
    1. Phase 2: Creates Citation Map [N] -> URL
    2. Synthesis: LLM uses [N] instead of raw URLs
    3. Phase 4: Re-injects verified links using Python
    """
    query_id = state.get("query_id", "")
    buffer = get_streaming_buffer(query_id) if query_id else None

    data = state.get("research_data", [])

    # Phase 2: Deduplicate URLs and Create Citation Map
    unique_urls = []
    seen_urls = set()
    url_map = {} # int -> {"url": URL, "type": "Official"/"Community"/"Web"}

    for item in data:
        url = item.get("url")
        source_label = item.get("source", "")
        if url:
            # Simple normalization
            clean_url = url.strip().rstrip('/')
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                
                # Determine type
                src_type = "Web"
                if "[OFFICIAL DOCS]" in source_label:
                    src_type = "Official"
                elif "[COMMUNITY EXPERIENCES]" in source_label:
                    src_type = "Community"
                
                unique_urls.append(url)
                url_map[len(unique_urls)] = {"url": url, "type": src_type}

    # Prepare Clean Context with Source IDs
    content_parts = []
    for i, item in enumerate(data):
        content = item.get("content", "")
        source = item.get("source", "Unknown")
        url = item.get("url", "")
        
        # Find ID for this URL
        src_id = 0
        src_type = "Web"
        if url:
            clean_url = url.strip().rstrip('/')
            for idx, u_data in url_map.items():
                if u_data["url"].strip().rstrip('/') == clean_url:
                    src_id = idx
                    src_type = u_data["type"]
                    break
        
        content_parts.append(f"[Source {src_id if src_id > 0 else 'Unknown'} ({src_type}): {source}]\n{content}")

    combined_content = "\n\n---\n\n".join(content_parts)

    # Append Citation Map to context for LLM guidance (IDs only)
    if url_map:
        cit_table = "\n\nCITATION MAP (Use these IDs: [N]):\n"
        cit_table += "\n".join(f"- [{idx}] : {data['url']} ({data['type']})" for idx, data in url_map.items())
        combined_content += cit_table


    history = state.get("history", [])
    history_context = ""
    if history:
        history_context = "\n\nConversation context:\n" + "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in history[-4:]
        ]) + "\n"

    chain = RESEARCH_SYNTHESIS_PROMPT | llm
    query_with_context = state["query"] + history_context

    full_response = ""
    for chunk in chain.stream({"query": query_with_context, "context": combined_content[:9000]}):
        token = chunk.content
        full_response += token
        if buffer:
            buffer.add_chunk(token)

    if buffer:
        buffer.mark_complete()

    cleaned_report = full_response.strip()

    cleaned_report = full_response.strip()

    # Phase 4: Post-Processing (The "Truth Layer")
    # Resolve url_map to simple int->url for the injector
    simple_url_map = {idx: data["url"] for idx, data in url_map.items()}
    validated_report = inject_verified_links(cleaned_report, simple_url_map)

    tokens_used = len(validated_report.split()) * 2

    return {
        "final_report": validated_report,
        "token_usage": state.get("token_usage", 0) + tokens_used,
        "url_map": url_map, # Pass for Phase 5 Evidence Trace sync
    }
