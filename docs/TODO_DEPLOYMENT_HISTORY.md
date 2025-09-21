# Deployment History Cleanup TODO

- [x] Remove unused `action_details` and `meta` columns from `deployment_history` via Alembic migration `b5d3f9f3b7f4`.
- [x] Prevent redundant reassignment entries by short-circuiting the assign endpoint when the example version and identifiers are unchanged.
- [x] Update Temporal workflows to log workflow-linked history entries without extra payload bloat.
- [x] Align Pydantic DTOs and generated TypeScript types with the slimmed history schema.
- [ ] Run `alembic upgrade head` in deployed environments and verify workflow IDs appear on new history rows.
