"""Synthesis domain service."""
import re
from collections.abc import AsyncIterator

from .models import SynthesisInput, SynthesisOutput, GapAnalysisInput, GapAnalysisOutput
from .ports import ILLMPort, ISynthesisService
from ..prompts.templates import build_synthesis_prompt, build_gap_analysis_prompt


class SynthesisDomainService(ISynthesisService):
    def __init__(self, llm_port: ILLMPort) -> None:
        self._llm = llm_port

    async def synthesize(self, input_: SynthesisInput) -> SynthesisOutput:
        prompt = self._build_prompt(input_)
        report, token_usage = await self._llm.synthesize(prompt)
        citations = self._extract_citations(input_.research_data, report)
        report = self._inject_citation_links(report, citations)
        return SynthesisOutput(report=report, citations=citations, token_usage=token_usage)

    async def synthesize_stream(self, input_: SynthesisInput) -> AsyncIterator[str]:
        prompt = self._build_prompt(input_)
        async for chunk in self._llm.synthesize_stream(prompt):
            yield chunk

    async def analyze_gaps(self, input_: GapAnalysisInput) -> GapAnalysisOutput:
        snippets = [item.content[:500] for item in input_.research_data]
        prompt = build_gap_analysis_prompt(
            query=input_.query,
            research_snippets=snippets,
            iteration=input_.iteration,
        )
        raw = await self._llm.analyze_gaps(prompt)
        return GapAnalysisOutput(
            confidence_score=float(raw.get("confidence_score", 0.5)),
            gaps=list(raw.get("gaps", [])),
        )

    def _build_prompt(self, input_: SynthesisInput) -> str:
        history_text = ""
        if input_.history:
            lines = [f"{m['role'].upper()}: {m['content']}" for m in input_.history[-4:]]
            history_text = "\nConversation context:\n" + "\n".join(lines) + "\n"
        snippets = [
            f"[{item.source}] {item.url}\n{item.content}"
            for item in input_.research_data
        ]
        return build_synthesis_prompt(
            query=input_.query,
            research_snippets=snippets,
            history_text=history_text,
            gaps=input_.gaps,
        )

    def _extract_citations(self, items, report: str) -> list[str]:
        cited_indices: set[int] = set()
        for match in re.finditer(r"\[(\d+)\]", report):
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(items):
                cited_indices.add(idx)
        return [items[i].url for i in range(len(items))]

    def _inject_citation_links(self, report: str, citations: list[str]) -> str:
        def replace(m: re.Match) -> str:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(citations):
                return f"[[{m.group(1)}]]({citations[idx]})"
            return m.group(0)
        return re.sub(r"\[(\d+)\]", replace, report)
