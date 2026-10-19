# Design

## Current behavior

`GET /document-libraries` extracts `name` into its filter dependency but calls `DocumentLibraryService.list_libraries`
without passing it. The service delegates directly to the repository, so all libraries are returned and repository
pagination happens before any possible name filtering.

`GET /document-libraries/{library_id}/document-sets` builds nested metadata with `documents.size_bytes`, while
`DocumentLibraryDTO.Document` defines `size`. Pydantic therefore drops the unknown key and the public size is `null`.

## Proposed behavior

The route passes `filters["name"]` to the service as `name_filter`. For a supplied filter, the service loads the ordered
library collection, keeps names containing the filter case-insensitively, and applies the requested offset and limit to
that filtered list. Without a filter, it keeps the existing repository `list_all(limit, offset)` path so current
ordering and pagination behavior remain unchanged.

The document-library route maps `doc_set.total_size_bytes` to the DTO key `size`. A set with zero documents continues to
produce `documents: null` as specified. If a populated set has an unavailable size value, the value remains `null`
through the existing optional DTO field rather than changing storage semantics.

## Boundaries and trade-offs

Filtering in the application service avoids changing the generic repository port or every repository adapter. It also
ensures filtering precedes pagination, at the cost of loading the full library collection for filtered requests. The
existing repository path is retained for unfiltered requests to minimize compatibility risk.

The DTO schema is unchanged; only the route's input mapping is corrected. Filesystem, database, authentication, and
status-code behavior are outside this change.

## Risks and mitigation

- Filter pagination could accidentally page before filtering: regression tests compare a filtered page with the second
  item of the complete filtered result.
- Case handling could be inconsistent: matching is explicitly case-insensitive and tested with mixed-case input.
- Zero-document behavior could regress while fixing size: tests assert `documents` remains `null`.
- Unknown size values could be coerced incorrectly: tests assert an unavailable value remains `null`.
