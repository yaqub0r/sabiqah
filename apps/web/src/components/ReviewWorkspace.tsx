import type { BookEntry, ReviewProposal } from "@sabiqah/release-model";
import { ReviewEditor } from "@sabiqah/editor";
import { useState } from "react";

export function ReviewWorkspace({
  bookSlug,
  releaseId,
  entry,
}: {
  bookSlug: string;
  releaseId: string;
  entry: BookEntry;
}) {
  const [ready, setReady] = useState(false);

  function saveProposal(proposal: ReviewProposal) {
    window.localStorage.setItem(
      "sabiqah.pendingProposal",
      JSON.stringify(proposal),
    );
    setReady(true);
  }

  return (
    <>
      <ReviewEditor
        bookSlug={bookSlug}
        baseReleaseId={releaseId}
        entry={entry}
        onProposal={saveProposal}
      />
      {ready && (
        <p className="proposal-ready">
          The proposal is saved in this browser.{" "}
          <a className="button" href="/admin/cms/">
            Open the pull-request workflow
          </a>
        </p>
      )}
    </>
  );
}
