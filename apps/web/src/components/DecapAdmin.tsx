import { useEffect, useState } from "react";

interface DecapValue {
  toJS?: () => unknown;
}

function displayValue(value: DecapValue | string | undefined): string {
  if (!value) return "No validated proposal has been imported yet.";
  const plainValue =
    typeof value === "string" ? value : (value.toJS?.() ?? value);
  if (typeof plainValue !== "string") {
    return JSON.stringify(plainValue, null, 2);
  }

  try {
    return JSON.stringify(JSON.parse(plainValue), null, 2);
  } catch {
    return plainValue;
  }
}

export function parsePendingProposal(pending: string): string {
  JSON.parse(pending);
  return pending;
}

export const proposalFormat = {
  fromFile(file: string): Record<string, unknown> {
    const parsed = JSON.parse(file) as Record<string, unknown>;
    return { ...parsed, proposal: JSON.stringify(parsed.proposal) };
  },
  toFile(value: Record<string, unknown>): string {
    const proposal =
      typeof value.proposal === "string"
        ? JSON.parse(value.proposal)
        : value.proposal;
    return `${JSON.stringify({ ...value, proposal }, null, 2)}\n`;
  },
};

export function DecapAdmin() {
  const [error, setError] = useState("");

  useEffect(() => {
    window.CMS_MANUAL_INIT = true;
    import("decap-cms-app")
      .then(({ default: CMS }) => {
        CMS.registerCustomFormat(
          "sabiqah-proposal-json",
          "json",
          proposalFormat,
        );
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
