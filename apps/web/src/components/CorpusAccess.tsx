import { useState, type SyntheticEvent } from "react";

export function CorpusAccess({
  siteKey,
  returnTo,
}: {
  siteKey?: string;
  returnTo: string;
}) {
  const [inviteCode, setInviteCode] = useState("");
  const [message, setMessage] = useState("");

  async function enroll(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Checking invitation…");
    const token = new FormData(event.currentTarget).get(
      "cf-turnstile-response",
    );
    const response = await fetch("/api/enrollment/begin", {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ inviteCode, turnstileToken: token, returnTo }),
    });
    const result = (await response.json()) as {
      authorizationUrl?: string;
      error?: string;
    };
    if (!response.ok || !result.authorizationUrl) {
      setMessage(result.error ?? "Enrollment could not be started.");
      return;
    }
    window.location.assign(result.authorizationUrl);
  }

  return (
    <section className="enrollment-card corpus-access">
      <p className="eyebrow">Reviewer access</p>
      <h2>Open the working corpus</h2>
      <p>
        The inventory is public. Draft Arabic, translated text, unresolved
        readings, and editorial decisions are available to active reviewers.
        Enter the shared invitation once, then continue with GitHub.
      </p>
      <form onSubmit={enroll}>
        <label>
          Invitation code
          <input
            value={inviteCode}
            onChange={(event) => setInviteCode(event.target.value)}
            required
            autoComplete="off"
          />
        </label>
        {siteKey ? (
          <div className="cf-turnstile" data-sitekey={siteKey}></div>
        ) : (
          <p className="protected-note">
            Turnstile is not configured in this local build.
          </p>
        )}
        <button type="submit" disabled={!siteKey}>
          Continue with GitHub
        </button>
        {message && <p role="status">{message}</p>}
      </form>
      {siteKey && (
        <script
          src="https://challenges.cloudflare.com/turnstile/v0/api.js"
          async
          defer
        ></script>
      )}
    </section>
  );
}
