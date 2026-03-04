from app.rag_engine.generation.prompts import build_prompt
from app.rag_engine.providers.llm_provider import LLMProvider


class AnswerBuilder:
    def __init__(self) -> None:
        self.llm = LLMProvider()

    def build(self, question: str, contexts: list[dict]) -> str:
        prompt = build_prompt(question, contexts)
        return self.llm.generate(prompt)
