# Spec Delta

## Purpose

Make the existing document-library name filter effective and expose document-set sizes under the existing public DTO
field.

## MODIFIED Requirements

### Requirement: List document libraries with pagination and filtering

`GET /api/v1/document-libraries` SHALL return a list of library responses (not wrapped in a paginated envelope).
Query parameters `limit` (default 100, max 1000), `offset` (default 0), and optional `name` (case-insensitive partial
match) SHALL filter results. Name filtering SHALL occur before offset and limit pagination. When `name` is omitted, the
existing ordering and pagination semantics SHALL be preserved.

#### Scenario: Name filter narrows results before pagination

- **WHEN** `GET /api/v1/document-libraries?name=research&limit=1&offset=1` is called and three libraries contain
  `Research` in their names while another library does not
- **THEN** the response is 200 and contains only the second matching library in the existing list order

#### Scenario: Name matching is case-insensitive and partial

- **WHEN** `GET /api/v1/document-libraries?name=research` is called
- **THEN** only libraries whose names contain `research` without regard to letter case are returned

#### Scenario: Nonmatching name returns an empty array

- **WHEN** `GET /api/v1/document-libraries?name=does-not-exist` is called
- **THEN** the response is 200 with `[]`

#### Scenario: Omitted name preserves normal listing

- **WHEN** `GET /api/v1/document-libraries` is called without `name`
- **THEN** the response uses the existing library ordering and pagination behavior without filtering

### Requirement: List document sets in a library

`GET /api/v1/document-libraries/{library_id}/document-sets` SHALL return a `DocumentSetsRetrieved` response containing
metadata for all document sets associated with the library, or an empty list if none are linked. For a set with stored
documents, `documents.size` SHALL contain its `total_size_bytes` value. A set with no stored documents SHALL continue to
return `documents: null`; an unavailable size for a populated set SHALL remain `null`.

#### Scenario: Known document size is returned under the public field

- **WHEN** a listed document set has `total_documents > 0` and `total_size_bytes = 4096`
- **THEN** its response contains `documents: {"count": ..., "size": 4096}` and does not require a `size_bytes` field

#### Scenario: Zero-size populated set is represented as zero

- **WHEN** a listed document set has `total_documents > 0` and `total_size_bytes = 0`
- **THEN** its response contains `documents.size = 0`

#### Scenario: Missing size remains unavailable

- **WHEN** a listed document set has `total_documents > 0` and no available size value
- **THEN** its response contains `documents.size = null`

#### Scenario: No stored documents retains null documents metadata

- **WHEN** a listed document set has `total_documents = 0`
- **THEN** its response contains `documents: null`
