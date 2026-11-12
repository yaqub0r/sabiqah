# Sahih al-Bukhari working release

Issue: [#166](https://github.com/yaqub0r/sabiqah/issues/166).

Sabiqah consumes `bukhari-opening-faith-working-1` from the immutable
[upstream release](https://github.com/yaqub0r/sahih-al-bukhari/releases/tag/public-working-969117cec0806973024e5cfad03583107db537de).
The reviewed pin and byte-preserved upstream manifest are under `evidence/releases/`.
The archive SHA-256 is
`27e731febdbc3c38d4c828096644ce1997b4c01515241456b58d5941c95748ca`.
Do not reformat the byte-preserved manifest; its raw digest is part of the pin.

## Material rights matrix

The scope is exactly 110 records: Beginning of Revelation and Book of Faith,
numbered reports 1–58, all intervening headings/comments, and 49 disclosures.
All records are human-unreviewed. This is an eligible public working edition;
canonical promotion is unused. Review date: 2026-11-11. Source-specific external
publication authority is the upstream owner's
[recorded decision](https://github.com/yaqub0r/sahih-al-bukhari/blob/969117cec0806973024e5cfad03583107db537de/docs/decisions/bukhari-working-release-1.md).
Sabiqah preserves that scoped decision and its limitations; it does not expand it.

| Material                                                                           | Creator / role                                                        | Basis and classification                                                                                                                   | Obligations and limits                                                                                                                                         |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| English and project-authored structure/notes                                       | Sahih al-Bukhari project, original translation and annotation         | Authorship; CC BY 4.0; approved-for-publication for the pinned release                                                                     | Credit the project, link license/release, indicate presentation changes; no claim of human scholarly approval                                                  |
| Displayed classical Arabic                                                         | Muhammad ibn Ismail al-Bukhari; pinned OpenITI JK000110 transcription | Upstream scoped classical-text rationale and owner-approved external distribution; approved-for-publication only within this exact release | Preserve OpenITI CC BY-NC-SA 4.0 provenance notice, source revision and edition; no commercial permission from OpenITI or third-party rights waiver is claimed |
| Modern introductions, footnotes, editorial discussion, indices, corpus annotations | Third-party modern material                                           | Excluded; not admitted for publication                                                                                                     | Never acquire through this integration or include in public output                                                                                             |
| Private translation/review/execution evidence and restricted English witnesses     | Non-public research                                                   | Private-reference; excluded                                                                                                                | Never enter Git or deployment artifacts                                                                                                                        |

Arabic source revision: `44e1c36738a2bf5c14dafa232a6ae1891e6171cd`;
source artifact SHA-256:
`69e95684acfde24171d29dd7ba43ff2c8f9b54ade5e3ab0a73899c06671082b7`.
Edition: Mustafa Dib al-Bugha; Dar Ibn Kathir / al-Yamama, Beirut;
third edition, 1407 AH / 1987 CE; six volumes. Text-only, not scan-verified.
The owner accepts disclosed residual modern-editorial/database-rights risks.
This is an operational record of the upstream decision, not legal clearance.

## Public notice and presentation

The reader displays the upstream attribution, Arabic basis, residual-risk
statement, edition, exclusions and all source limitations. English and original
structure retain [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/);
OpenITI's [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
notice remains visible and is not represented as commercial permission.
Neither is replaced by Sabiqah's software/content licenses.

Sabiqah renders unchanged text into bilingual sections and expandable source
details. Ordered transmission paths describe textual order, not historical
contact or hadith authentication. Every source uncertainty remains visible.

## Reproducible ingestion and rollback

`pnpm build` and `pnpm dev` run `pnpm ingest:bukhari` first. Python 3.11+ and
the standard library verify the exact archive, safe five-member inventory,
closure, manifest, proposal, pinned closed record schema, Arabic spans, ordered
path references, source identities, report coverage, review totals and disclosures.
The downloaded archive and generated reader data stay in ignored `.runtime/`;
upstream HTML is verified but never executed or served. Astro emits static pages.
No R2 pointer, D1 schema, review ledger or Al-Isabah adapter changes.

The input is a reviewed immutable release/tag/commit pin, not "latest". Normal
builds need network access only when that exact archive is absent. Cached bytes
are revalidated every time; corruption fails rather than silently redownloading.
Future releases require a reviewed pin/manifest update and consumer validation.
Rollback restores the previous reviewed application deployment/pin. It never
overwrites upstream assets or scholarly content.
