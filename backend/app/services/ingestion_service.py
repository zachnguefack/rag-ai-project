class IngestionService:
    def enqueue_document(self, document_id: int) -> dict:
        return {"document_id": document_id, "status": "queued"}
