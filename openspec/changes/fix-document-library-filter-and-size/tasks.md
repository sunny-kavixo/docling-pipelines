# Tasks

## 1. Reproduce and specify

- [x] 1.1 [backend] Review issue #296 discussion and confirm the reporter's split: name filtering and size mapping are
  independent of the three status-code defects.
- [x] 1.2 [backend] Review the canonical document-libraries API specification, route, service, DTO, repository, and
  existing route-test work.
- [x] 1.3 [backend] Record pre-fix reproductions for the ignored route filter and `size_bytes` mapping.
- [x] 1.4 [backend] Write and locally review the proposal, design, spec delta, and implementation tasks before code.

## 2. Implement and verify

- [x] 2.1 [backend] Pass the route name filter to the service and apply partial matching before pagination.
- [x] 2.2 [backend] Map document-set `total_size_bytes` to the public `documents.size` field without changing zero-set
  semantics.
- [x] 2.3 [backend] Add focused FastAPI route regressions using an isolated temporary library database and service test
  coverage for filtered pagination.
- [x] 2.4 [backend] Run focused tests, related asset tests, formatting, typing, security, hygiene, and strict OpenSpec
  validation where the environment provides the required tools. The strict OpenSpec CLI was unavailable in this
  environment.
- [x] 2.5 [backend] Review the final diff and prepare a PR description without publishing it.
