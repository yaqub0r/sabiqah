import {
  useEffect,
  useState,
  type ReactNode,
  type SyntheticEvent,
} from "react";

interface SessionIdentity {
  login: string;
  avatarUrl: string | null;
  membershipStatus: "active" | "limited" | "suspended";
}

interface ReviewerGateProps {
  siteKey?: string;
  returnTo: string;
  children: ReactNode;
}

export function ReviewerGate({
  siteKey,
  returnTo,
  children,
}: ReviewerGateProps) {
  const [status, setStatus] = useState<
    "loading" | "anonymous" | "authenticated"
  >("loading");
  const [identity, setIdentity] = useState<SessionIdentity>();
  const [inviteCode, setInviteCode] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/session", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) throw new Error("anonymous");
        return (await response.json()) as { identity: SessionIdentity };
      })
      .then(({ identity: nextIdentity }) => {
        setIdentity(nextIdentity);
        setStatus("authenticated");
      })
      .catch(() => setStatus("anonymous"));
  }, []);

  async function enroll(event: SyntheticEvent<HTMLFormElement, SubmitEvent>) {
    event.preventDefault();
    setMessage("Checking invitation…");
    const form = event.currentTarget;
    const token = new FormData(form).get("cf-turnstile-response");
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

  if (status === "loading") return <p>Checking reviewer access…</p>;
  if (status === "authenticated") {
    if (identity?.membershipStatus !== "active") {
      return (
        <p className="issue-banner">
          This membership cannot submit reviews. Contact a project administrator
          to request review.
        </p>
      );
    }
    return (
      <>
        <p className="badge">Reviewing as @{identity?.login}</p>
        {children}
      </>
    );
  }

  return (
    <section className="enrollment-card">
      <p className="eyebrow">Reviewer enrollment</p>
      <h2>Enter the community invitation</h2>
      <p>
        The shared code proves you were invited. GitHub then supplies your
        durable reviewer identity; it does not grant merge or infrastructure
        access.
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
