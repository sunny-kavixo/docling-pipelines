"""Regression tests for document-library filtering and document-set sizes.

The library route and service use the production FastAPI and DuckDB-backed
implementations. The document-set service is a narrow in-memory test double
because these regressions only consume its metadata lookup boundary.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from docpipe.api.dependencies import get_document_library_service, get_document_set_service
from docpipe.api.middleware.error_handler import (
    docpipe_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from docpipe.api.routes.document_libraries import document_libraries_router
from docpipe.core.assets.common.adapters.repositories.duckdb_asset_repository import DuckDBAssetRepository
from docpipe.core.assets.document_libraries.application.services.document_library_service import (
    DocumentLibraryService,
)
from docpipe.core.assets.document_libraries.domain.models.document_library import DocumentLibrary
from docpipe.core.assets.document_sets.domain.models.document_set import DocumentSet
from docpipe.exceptions.docpipe_exceptions import DocpipeException
from docpipe.storage.duck_db.duckdb_key_value_storage import DuckDBKeyValueStorage

_BASE = "/document-libraries"
_SET_KNOWN = "11111111-1111-4111-8111-111111111111"
_SET_ZERO_DOCUMENTS = "22222222-2222-4222-8222-222222222222"
_SET_ZERO_SIZE = "33333333-3333-4333-8333-333333333333"
_SET_UNKNOWN_SIZE = "44444444-4444-4444-8444-444444444444"


class FakeDocumentSetService:
    """Serve production-shaped document-set metadata for route tests."""

    def __init__(self) -> None:
        self._by_id = {
            _SET_KNOWN: DocumentSet(
                asset_id=_SET_KNOWN,
                name="Known set",
                total_documents=3,
                total_size_bytes=4096,
            ),
            _SET_ZERO_DOCUMENTS: DocumentSet(
                asset_id=_SET_ZERO_DOCUMENTS,
                name="Empty set",
                total_documents=0,
                total_size_bytes=0,
            ),
            _SET_ZERO_SIZE: DocumentSet(
                asset_id=_SET_ZERO_SIZE,
                name="Zero size set",
                total_documents=2,
                total_size_bytes=0,
            ),
            _SET_UNKNOWN_SIZE: DocumentSet(
                asset_id=_SET_UNKNOWN_SIZE,
                name="Unknown size set",
                total_documents=1,
                total_size_bytes=None,  # type: ignore[arg-type]
            ),
        }

    def get_document_set(self, *, document_set_id: str) -> DocumentSet:
        """Return the requested test document set."""
        return self._by_id[document_set_id]


@pytest.fixture
def library_service(tmp_path: Path) -> DocumentLibraryService:
    """Create the production library service with an isolated DuckDB file."""
    database_path = str(tmp_path / "libraries.duckdb")
    repository = DuckDBAssetRepository(
        asset_type=DocumentLibrary,
        key_value_storage=DuckDBKeyValueStorage(database_path=database_path),
        database_path=database_path,
    )
    return DocumentLibraryService(repository=repository)


@pytest.fixture
def document_set_service() -> FakeDocumentSetService:
    """Create the metadata-only document-set test double."""
    return FakeDocumentSetService()


@pytest.fixture
def client(library_service: DocumentLibraryService, document_set_service: FakeDocumentSetService) -> TestClient:
    """Build a route-only FastAPI client with production exception handling."""
    app = FastAPI()
    app.include_router(document_libraries_router)
    app.add_exception_handler(DocpipeException, docpipe_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    app.dependency_overrides[get_document_library_service] = lambda: library_service
    app.dependency_overrides[get_document_set_service] = lambda: document_set_service
    return TestClient(app, raise_server_exceptions=False)


def _create(client: TestClient, name: str) -> dict:
    """Create one library through the public route."""
    response = client.post(_BASE, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


class TestListLibraries:
    """GET /document-libraries name-filter behavior."""

    def test_name_filter_returns_only_partial_matches(self, client: TestClient) -> None:
        """Return only libraries containing the requested name text."""
        _create(client, "Research Papers")
        _create(client, "Operations")

        response = client.get(_BASE, params={"name": "research"})

        assert response.status_code == 200
        assert [library["name"] for library in response.json()] == ["Research Papers"]

    def test_name_filter_is_applied_before_pagination(self, client: TestClient) -> None:
        """Paginate the matching collection rather than the unfiltered collection."""
        for name in ("Research Alpha", "Operations", "Research Beta", "Research Gamma"):
            _create(client, name)

        matching = client.get(_BASE, params={"name": "RESEARCH"}).json()
        page = client.get(_BASE, params={"name": "research", "limit": 1, "offset": 1})

        assert page.status_code == 200
        assert page.json() == matching[1:2]

    def test_no_filter_preserves_normal_listing(self, client: TestClient) -> None:
        """An omitted name filter returns the normal unfiltered collection."""
        _create(client, "Research Papers")
        _create(client, "Operations")

        response = client.get(_BASE)

        assert response.status_code == 200
        assert {library["name"] for library in response.json()} == {"Research Papers", "Operations"}

    def test_nonmatching_name_returns_empty_array(self, client: TestClient) -> None:
        """A name filter with no matches returns an empty successful response."""
        _create(client, "Research Papers")

        response = client.get(_BASE, params={"name": "missing"})

        assert response.status_code == 200
        assert response.json() == []


class TestListDocumentSets:
    """GET /document-libraries/{id}/document-sets document metadata behavior."""

    def test_document_size_uses_public_size_field(self, client: TestClient) -> None:
        """Expose a populated set's total size as documents.size."""
        library_id = _create(client, "Research Papers")["library_id"]
        add_response = client.put(
            f"{_BASE}/{library_id}/document-sets",
            params={"document_sets_ids": _SET_KNOWN},
        )

        response = client.get(f"{_BASE}/{library_id}/document-sets")

        assert add_response.status_code == 204
        assert response.status_code == 200
        document = response.json()["document_sets"][0]["documents"]
        assert document == {"count": 3, "size": 4096}
        assert "size_bytes" not in document

    @pytest.mark.parametrize(
        ("document_set_id", "expected_documents"),
        [
            (_SET_ZERO_DOCUMENTS, None),
            (_SET_ZERO_SIZE, {"count": 2, "size": 0}),
            (_SET_UNKNOWN_SIZE, {"count": 1, "size": None}),
        ],
    )
    def test_document_size_boundary_values(
        self,
        client: TestClient,
        document_set_id: str,
        expected_documents: dict | None,
    ) -> None:
        """Preserve null, zero, and unavailable document-size semantics."""
        library_id = _create(client, "Boundary Library")["library_id"]
        add_response = client.put(
            f"{_BASE}/{library_id}/document-sets",
            params={"document_sets_ids": document_set_id},
        )

        response = client.get(f"{_BASE}/{library_id}/document-sets")

        assert add_response.status_code == 204
        assert response.status_code == 200
        assert response.json()["document_sets"][0]["documents"] == expected_documents
