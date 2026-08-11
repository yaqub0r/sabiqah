import { useEffect, useState } from "react";

export function DecapAdmin() {
  const [error, setError] = useState("");

  useEffect(() => {
    window.CMS_MANUAL_INIT = true;
    import("decap-cms-app")
      .then(({ default: CMS }) => {
        CMS.registerWidget(
          "sabiqah-proposal",
          ({
            value,
            onChange,
          }: {
            value?: string;
            onChange: (value: string) => void;
          }) => {
            const pending = window.localStorage.getItem(
              "sabiqah.pendingProposal",
            );
            const displayed = value || pending || "";
            return (
              <div>
                <p>
                  Sabiqah supplies a validated proposal; Decap supplies the fork
                  and pull-request workflow.
                </p>
                <textarea
                  rows={18}
                  value={displayed}
                  onChange={(event) => onChange(event.target.value)}
                  aria-label="Validated Sabiqah proposal JSON"
                />
                {!value && pending && (
                  <button type="button" onClick={() => onChange(pending)}>
                    Import prepared proposal
                  </button>
                )}
              </div>
            );
          },
          ({ value }: { value?: string }) => <pre>{value}</pre>,
        );
        CMS.init();
      })
      .catch((caught: unknown) =>
        setError(
          caught instanceof Error ? caught.message : "Decap failed to start.",
        ),
      );
  }, []);

  return error ? (
    <p className="issue-banner">{error}</p>
  ) : (
    <div id="decap-root">
      <p>Loading pull-request workflow…</p>
    </div>
  );
}

declare global {
  interface Window {
    CMS_MANUAL_INIT?: boolean;
  }
}
