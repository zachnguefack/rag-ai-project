from app.rag_engine.ingestion.chunkers import chunk_text
from app.rag_engine.ingestion.cleaners import clean_text


class IngestionPipeline:
    def run(self, content: str) -> list[str]:
        return chunk_text(clean_text(content))
