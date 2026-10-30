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

## Retry design
- Classify validation errors as extraction-fixable vs document-inherent.
  Skip retries for document-inherent errors (e.g. supplier's wrong total).
  Sample 04 currently spends 3 LLM calls and always ends in review.
- Keep the last good extraction when a later attempt fails (API error,
  parse error). Currently `invoice` becomes None and the earlier result is lost.
- On a failed attempt, keep the previous validation feedback for the next
  prompt instead of replacing it with the API error.
- Check the openai docs for finish-reason errors (length, content filter)
  and decide whether they belong in the "parse failure" branch.

## Validation rules
- Decide how to handle line items with no quantity or unit price
  (e.g. "Consulting — 500"). Rule 5 currently sends these to review every time.
- Use [0-9] or re.ASCII in the date regex so non-ASCII digits get the
  right error message.

## Testing
- Cover the untested `extract_fields` branches: 4xx re-raise,
  429/5xx recorded, parse-error recorded.