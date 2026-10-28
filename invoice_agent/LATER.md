# Later

Deferred intentionally to keep the first version focused.

## Extraction and validation
- Add `due_date` validation.
- Decide which additional invoice fields to support.
- Improve handling of ambiguous dates, number formats, and currencies.
- Support multiple invoices in one input.
- Handle credit notes.
- Detect non-invoice input and exit early.
- Strengthen handling of prompt injection in invoice content.

## Workflow and integrations
- Add human-review interrupts and resume handling.
- Add persistent storage with PostgreSQL.
- Explore streaming intermediate progress.
- Support PDF input and text extraction.

## Before implementing
- Add tests for each new behavior.
- Preserve the rule that the extractor must not invent or silently correct supplier-provided values.
- Keep validation deterministic and retain the bounded-retry-to-human-review behavior.
