# Proposal

## Why

The document-library API accepts a `name` query parameter but currently ignores it, so callers receive unrelated
libraries. The document-set listing route also builds a `size_bytes` mapping while the public `Document` DTO exposes
the contract field `size`, causing known sizes to serialize as `null`.

## What Changes

- Apply the optional document-library name filter as a case-insensitive partial match before pagination.
- Preserve the existing no-filter ordering and pagination behavior.
- Map document-set `total_size_bytes` to the public `documents.size` field.
- Preserve `documents: null` for sets with no stored documents and pass through unavailable sizes as `null` when a set
  has documents.
- Add route and service regression coverage for matching, pagination, empty results, and size boundaries.

## Capabilities

### Modified Capabilities

- `backend/document-libraries-api`: make the documented name filter effective and return document size under the DTO's
  existing field name.

## Impact

Backend-only. The affected REST route and document-library application service remain within the existing DDD layers.
No storage schema, authentication, permission, status-code, frontend, or dependency changes are proposed.

## Non-goals

- Change the three status-code defects assigned to the issue reporter: unknown document set status, removing an
  unassociated set, and rename-conflict status.
- Change document-set storage metrics or internal `total_size_bytes` naming.
- Change unrelated query parameters, repository ordering, or other API endpoints.
- Close the entire multi-defect issue automatically; the remaining status-code work is outside this change.
