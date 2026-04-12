"""LLM prompt templates for synthesis and gap analysis."""


def build_synthesis_prompt(
    query: str,
    research_snippets: list[str],
    history_text: str,
    gaps: list[str],
) -> str:
    gap_context = ""
    if gaps:
        gap_context = f"\nFocus especially on filling these identified gaps:\n" + "\n".join(
            f"- {g}" for g in gaps
        )

    sources_block = "\n\n".join(
        f"[Source {i+1}]\n{snippet}" for i, snippet in enumerate(research_snippets)
    )

    return f"""You are a senior technical research analyst. Synthesize the sources below into a
comprehensive, well-structured technical report.

QUERY: {query}
{history_text}{gap_context}

RESEARCH SOURCES:
{sources_block}

INSTRUCTIONS:
- Write an Executive Summary (2-3 sentences)
- Then structured sections with clear headings
- Cite sources inline as [1], [2], ... matching source numbers above
- Be specific, technical, and evidence-based
- Where a diagram would clarify architecture, flow, or relationships, include ONE mermaid diagram
  using a fenced code block: ```mermaid\n<diagram>\n```
  Use flowchart TD or sequenceDiagram as appropriate. Keep it simple (max 10 nodes).
- End with a "Key Takeaways" section (3-5 bullet points)

REPORT:
"""


def build_gap_analysis_prompt(
    query: str,
    research_snippets: list[str],
    iteration: int,
) -> str:
    sources_block = "\n\n".join(
        f"[Source {i+1}]\n{snippet[:500]}" for i, snippet in enumerate(research_snippets)
    )

    return f"""Evaluate whether the research sources below sufficiently answer the query.
Iteration: {iteration + 1}

QUERY: {query}

SOURCES:
{sources_block}

Return ONLY a JSON object:
{{
  "confidence_score": <float 0.0-1.0, how well sources answer the query>,
  "gaps": ["<specific missing topic 1>", "<specific missing topic 2>", ...]
}}

- confidence_score >= 0.8 means sufficient
- gaps should be specific, searchable topics (empty list if sufficient)
- Return ONLY the JSON, no other text
"""
