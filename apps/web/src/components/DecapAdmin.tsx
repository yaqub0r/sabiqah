import { useEffect, useState } from "react";

interface DecapValue {
  toJS?: () => unknown;
}

function displayValue(value: DecapValue | string | undefined): string {
  if (!value) return "No validated proposal has been imported yet.";
  const plainValue =
    typeof value === "string" ? value : (value.toJS?.() ?? value);
  return typeof plainValue === "string"
    ? plainValue
    : JSON.stringify(plainValue, null, 2);
}

export function parsePendingProposal(pending: string): unknown {
  return JSON.parse(pending);
}

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
            value?: DecapValue | string;
            onChange: (value: unknown) => void;
          }) => {
            const pending = window.localStorage.getItem(
              "sabiqah.pendingProposal",
            );
            return (
              <div>
                <p>
                  Sabiqah supplies a validated proposal; Decap supplies the fork
                  and pull-request workflow.
                </p>
                <pre aria-label="Validated Sabiqah proposal JSON">
                  {displayValue(value)}
                </pre>
                {!value && pending && (
                  <button
                    type="button"
                    onClick={() => onChange(parsePendingProposal(pending))}
                  >
                    Import prepared proposal
                  </button>
                )}
              </div>
            );
          },
          ({ value }: { value?: DecapValue | string }) => (
            <pre>{displayValue(value)}</pre>
          ),
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
