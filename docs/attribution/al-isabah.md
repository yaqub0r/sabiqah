# Al-Isabah sources, attribution, and reuse

The public working translation of _al-Isabah fi Tamyiz al-Sahabah_ is a
remediated research edition. Public readability does not mean that its English
has completed human scholarly review or canonical promotion.

## Arabic publication base

The structured Arabic is derived from OpenITI's transcription of Ibn Hajar's
_al-Isabah_, edition of Ali Muhammad al-Bijawi (Dar al-Jil, Beirut, 1412/1992),
pinned to commit
[`5835c183`](https://github.com/OpenITI/0875AH/blob/5835c183b8bbf4ea454d5c1be2b168b669403771/data/0852IbnHajarCasqalani/0852IbnHajarCasqalani.IsabaFiTamyiz/0852IbnHajarCasqalani.IsabaFiTamyiz.JK000533-ara1.mARkdown).
OpenITI distributes its text releases under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Sabiqah removes OpenITI markup, preserves its entry and page references as
metadata, and applies only the reversible honorific typography documented in
the pinned
[Al-Isabah governance reference](../architecture/al-isabah-governance-compatibility.md).

The resulting Arabic-derived corpus must be attributed, used
noncommercially, and shared under the same license. No broader permission for
independent source material is implied.

## Independent facsimile witness

Arabic Collections Online provides a four-volume Cairo printing by Matba'at
al-Sa'adah (1323-1325/1905-1907) through the
[NYU viewer](https://sites.dlib.nyu.edu/viewer/books/uaena_aco000081/1).
ACO states that it believes the materials displayed by the project are in the
public domain. Sabiqah uses these scans as an independent visual witness; it
does not claim that their pagination is identical to the OpenITI source
edition. No reusable facsimile of OpenITI's 1992 source edition is approved, so
OpenITI page markers are source metadata rather than scan-verified citations.

The exact item identifiers, permanent links, hashes, and operational rights
assessment are recorded in
[`evidence/source-authorities/al-isabah.v1.json`](../../evidence/source-authorities/al-isabah.v1.json).

## English and review status

The English is Sabiqah-authored work reconstructed against the approved Arabic
base. Modern footnotes, introductions, critical apparatus, private object
locations, and restricted comparison expression are excluded. When a legacy
translation cannot pass the public-output checks, its aligned book entry remains
readable in approved Arabic and the English is withheld with a visible
translation gap. Legacy contextual passages that do not yet have an approved
public-source alignment remain excluded and are listed by stable identifier in
the [public exclusion report](https://dev.sabiqah.org/api/corpus/al-isabah/exclusions)
instead of being silently exposed or mislabeled as failed book records.

The earlier reader's `isabah-passage-945134c508e2`, titled **Abu Bakr**, is one
such contextual passage. It was preserved from an edition-specific research
result, but it has no approved OpenITI entry identity and includes apparatus
that cannot be carried into the public working edition. The underlying research
work remains preserved under Sabiqah's private-evidence rules. It may return to
public reading only after its medieval text is aligned to an approved public
source and the English is accepted under Al-Isabah's pinned policy and issued
in a new immutable upstream release.

Each visible record reports its machine and human-review state. Corrections and
approvals are append-only review evidence; they do not alter the applicable
source license, change release class, update upstream per-record metadata, or
make a working record canonical by themselves. Al-Isabah owns translation
policy, scholarly review metadata, corrections, and release decisions;
Sabiqah displays the pinned release plus its separate operational review
overlay.

Questions about attribution, source status, or removal should be raised in the
[Sabiqah issue tracker](https://github.com/yaqub0r/sabiqah/issues).
