# Repository contract index

This is the canonical discovery surface for policies that govern repository
changes. Before editing a governed path, read every contract selected by the
[machine-readable registry](contracts.registry.json). Pull requests must list
the applicable contract IDs in their `Contracts consulted` section.

The acknowledgement gate maps changed paths to contracts and fails closed when
a required ID is missing. A passing acknowledgement proves that the governing
documents were named; it does not by itself prove that the change complies with
them. Authors, reviewers, tests, and release controls retain their respective
responsibilities.

## Active contracts

| Contract ID                 | Governs                                                                                                                             | Contract                                                       |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `content-source-compliance` | Source acquisition, rights classification, provenance, restricted evidence, comparison, translation lineage, and public eligibility | [`content-source-compliance.md`](content-source-compliance.md) |
| `canonical-book-promotion`  | Promotion of approved scholarly content into canonical book repositories and consumption of pinned releases                         | [`canonical-book-promotion.md`](canonical-book-promotion.md)   |

## Contributor workflow

1. Identify the files the change will touch.
2. Use the registry to find every matching contract ID.
3. Read the corresponding contract documents before editing.
4. Record those IDs in the pull request, one per Markdown list item.
5. Treat a red or missing `contract-ack` check as a merge blocker.

Select `None required` only when no changed path matches the registry. Contract
documents and registry metadata are themselves governed, so changes to this
system require acknowledging both active contracts.
