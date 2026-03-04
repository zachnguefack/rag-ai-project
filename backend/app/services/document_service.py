from app.models.schema.document import DocumentCreateRequest, DocumentResponse


class DocumentService:
    _documents: list[DocumentResponse] = []

    def create_document(self, payload: DocumentCreateRequest) -> DocumentResponse:
        doc = DocumentResponse(id=len(self._documents) + 1, title=payload.title, content=payload.content)
        self._documents.append(doc)
        return doc

    def list_documents(self) -> list[DocumentResponse]:
        return self._documents
