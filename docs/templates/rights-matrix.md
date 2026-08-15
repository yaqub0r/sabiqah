# Rights matrix: [work title]

Use one matrix per book or independently released content set. Replace every
placeholder before promotion. Add rows when one release contains materials
with different rights; do not combine them under the broadest license.

## Release identity

| Field                  | Value                                 |
| ---------------------- | ------------------------------------- |
| Work or content-set ID | `[stable-id]`                         |
| Canonical repository   | `[repository URL]`                    |
| Release or manifest    | `[tag, release ID, or manifest path]` |
| Rights review date     | `YYYY-MM-DD`                          |
| Rights reviewer        | `[role or accountable reviewer]`      |
| Tracking issue         | `[issue URL]`                         |

## Material rights

| Material                               | Creator or source        | Role in release                 | Rights holder          | Rights basis                             | License or status           | Attribution required                                                  | Publication classification                                                                                            | Exact scope or location              | Provenance record                     | Restrictions or open questions |
| -------------------------------------- | ------------------------ | ------------------------------- | ---------------------- | ---------------------------------------- | --------------------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------- | ------------------------------ |
| `[e.g., source transcription]`         | `[provider and edition]` | `[base / comparison / display]` | `[known holder]`       | `[license / public domain / permission]` | `[SPDX ID, URL, or status]` | `[exact credit and link]`                                             | `[approved-for-publication / external-reference / private-reference / permission-required / unresolved / prohibited]` | `[files, record IDs, or page range]` | `[manifest or source-authority path]` | `[limitations]`                |
| `[e.g., Sabiqah-authored translation]` | `Sabiqah contributors`   | `published translation`         | `Sabiqah contributors` | `Sabiqah authorship`                     | `CC-BY-NC-SA-4.0`           | `Sabiqah contributors; release link; license link; changes indicated` | `approved-for-publication`                                                                                            | `[exact files or record IDs]`        | `[promotion manifest]`                | `[none or limitations]`        |

## Required review

- [ ] Every displayed or distributed component has its own row.
- [ ] Sabiqah authorship is distinguished from third-party expression.
- [ ] The translation or transcription base is distinguished from comparison
      witnesses.
- [ ] The rights basis is affirmative; public availability or a URL alone is
      not treated as permission.
- [ ] License compatibility, attribution, share-alike, and modification-notice
      obligations are recorded.
- [ ] Private evidence and restricted witnesses are marked non-public and are
      excluded from repositories, manifests, and deployment artifacts.
- [ ] Unresolved or permission-required material is blocked from promotion.
- [ ] The promotion manifest binds the decision to exact content hashes or
      stable release identities.
- [ ] A qualified reviewer has considered any source-specific legal question
      that this operational matrix cannot decide.

## Public notice text

Record the exact attribution and license statement that the reader, download,
or release must carry:

`[Attribution, source link, license link, modification notice, and any
source-specific wording]`

## Decision record

Summarize the publication decision, unresolved limitations, and the evidence
used to reach it without copying restricted expression or exposing private
locations or access details.
