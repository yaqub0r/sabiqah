import { hmacHex, signPayload, timingSafeEqual, verifyPayload } from "./crypto";
import {
  exchangeGitHubCode,
  fetchGitHubUser,
  githubAuthorizationUrl,
} from "./github";
import { cookie, json, parseCookies, safeReturnTo } from "./http";
import { canReadCorpus, corpusJson, corpusObjectKey } from "./corpus";

interface RateLimitBinding {
  limit(input: { key: string }): Promise<{ success: boolean }>;
}

interface Env {
  ASSETS: Fetcher;
  DB: D1Database;
  REVIEW_CORPUS: R2Bucket;
  ENROLLMENT_RATE_LIMITER: RateLimitBinding;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
  INVITE_CODE_DIGEST: string;
  INVITE_CODE_PEPPER: string;
  SESSION_SECRET: string;
  TURNSTILE_SECRET_KEY: string;
}

interface OAuthState {
  purpose: "enrollment" | "decap";
  nonce: string;
  exp: number;
  returnTo?: string;
}

interface SessionState {
  sub: string;
  exp: number;
}

interface MemberRow {
  id: number;
  github_user_id: string;
  github_login: string;
  avatar_url: string | null;
  status: "active" | "limited" | "suspended";
}

const ENROLLMENT_COOKIE = "sabiqah_enrollment";
const DECAP_COOKIE = "sabiqah_decap";
const SESSION_COOKIE = "sabiqah_session";
const OAUTH_TTL_SECONDS = 10 * 60;
const SESSION_TTL_SECONDS = 7 * 24 * 60 * 60;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    try {
      if (url.pathname === "/api/health")
        return json({ ok: true, service: "sabiqah-platform" });
      if (url.pathname === "/api/enrollment/begin" && request.method === "POST")
        return beginEnrollment(request, env);
      if (
        url.pathname === "/api/auth/github/callback" &&
        request.method === "GET"
      )
        return finishEnrollment(request, env);
      if (url.pathname === "/api/session" && request.method === "GET")
        return getSession(request, env);
      if (url.pathname === "/api/reputation/me" && request.method === "GET")
        return getReputation(request, env);
      if (
        url.pathname === "/api/corpus/al-isabah/summary" &&
        request.method === "GET"
      )
        return corpusJson(env.REVIEW_CORPUS, corpusObjectKey("summary"));
      if (
        url.pathname === "/api/corpus/al-isabah/index" &&
        request.method === "GET"
      ) {
        const member = await authenticatedMember(request, env);
        if (!canReadCorpus(member))
          return json(
            { error: "Active reviewer access required" },
            { status: 403 },
          );
        return corpusJson(env.REVIEW_CORPUS, corpusObjectKey("index"));
      }
      const corpusItem = url.pathname.match(
        /^\/api\/corpus\/al-isabah\/items\/([A-Za-z0-9][A-Za-z0-9._:-]{2,199})$/,
      );
      if (corpusItem && request.method === "GET") {
        const member = await authenticatedMember(request, env);
        if (!canReadCorpus(member))
          return json(
            { error: "Active reviewer access required" },
            { status: 403 },
          );
        return corpusJson(
          env.REVIEW_CORPUS,
          corpusObjectKey("item", corpusItem[1]),
        );
      }
      const corpusSection = url.pathname.match(
        /^\/api\/corpus\/al-isabah\/sections\/([A-Za-z0-9][A-Za-z0-9._:-]{2,199})$/,
      );
      if (corpusSection && request.method === "GET") {
        const member = await authenticatedMember(request, env);
        if (!canReadCorpus(member))
          return json(
            { error: "Active reviewer access required" },
            { status: 403 },
          );
        return corpusJson(
          env.REVIEW_CORPUS,
          corpusObjectKey("section", corpusSection[1]),
        );
      }
      if (url.pathname === "/api/logout" && request.method === "POST") {
        return json(
          { ok: true },
          {
            headers: {
              "set-cookie": cookie(SESSION_COOKIE, "", { maxAge: 0 }),
            },
          },
        );
      }
      if (url.pathname === "/api/decap/auth" && request.method === "GET")
        return beginDecap(request, env);
      if (url.pathname === "/api/decap/callback" && request.method === "GET")
        return finishDecap(request, env);
      if (url.pathname.startsWith("/api/"))
        return json({ error: "Not found" }, { status: 404 });
      return env.ASSETS.fetch(request);
    } catch (error) {
      console.error("request_failed", {
        path: url.pathname,
        message: error instanceof Error ? error.message : "unknown",
      });
      return json(
        { error: "The request could not be completed." },
        { status: 500 },
      );
    }
  },
};

async function beginEnrollment(request: Request, env: Env): Promise<Response> {
  const clientIp = request.headers.get("cf-connecting-ip") ?? "local";
  const rate = await env.ENROLLMENT_RATE_LIMITER.limit({ key: clientIp });
  if (!rate.success) return enrollmentFailure(429);

  const body = (await request.json().catch(() => null)) as {
    inviteCode?: unknown;
    turnstileToken?: unknown;
    returnTo?: unknown;
  } | null;
  if (
    !body ||
    typeof body.inviteCode !== "string" ||
    typeof body.turnstileToken !== "string"
  ) {
    return enrollmentFailure();
  }

  const [turnstileValid, suppliedDigest] = await Promise.all([
    verifyTurnstile(body.turnstileToken, clientIp, env.TURNSTILE_SECRET_KEY),
    hmacHex(
      body.inviteCode.trim().toLocaleLowerCase("en-US"),
      env.INVITE_CODE_PEPPER,
    ),
  ]);
  if (
    !turnstileValid ||
    !timingSafeEqual(suppliedDigest, env.INVITE_CODE_DIGEST.toLowerCase())
  ) {
    return enrollmentFailure();
  }

  const state: OAuthState = {
    purpose: "enrollment",
    nonce: crypto.randomUUID(),
    exp: Math.floor(Date.now() / 1000) + OAUTH_TTL_SECONDS,
    returnTo: safeReturnTo(body.returnTo),
  };
  const token = await signPayload(state, env.SESSION_SECRET);
  const redirectUri = `${new URL(request.url).origin}/api/auth/github/callback`;
  return json(
    {
      authorizationUrl: githubAuthorizationUrl(
        env.GITHUB_CLIENT_ID,
        redirectUri,
        token,
        "read:user",
      ),
    },
    {
      headers: {
        "set-cookie": cookie(ENROLLMENT_COOKIE, token, {
          maxAge: OAUTH_TTL_SECONDS,
          path: "/api/auth",
        }),
      },
    },
  );
}

async function finishEnrollment(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stateToken = url.searchParams.get("state");
  const cookieToken = parseCookies(request).get(ENROLLMENT_COOKIE);
  if (
    !code ||
    !stateToken ||
    !cookieToken ||
    !timingSafeEqual(stateToken, cookieToken)
  )
    return oauthFailure();

  const state = await verifyPayload<OAuthState>(stateToken, env.SESSION_SECRET);
  if (!state || state.purpose !== "enrollment" || state.exp < Date.now() / 1000)
    return oauthFailure();

  const redirectUri = `${url.origin}/api/auth/github/callback`;
  const accessToken = await exchangeGitHubCode(
    code,
    redirectUri,
    env.GITHUB_CLIENT_ID,
    env.GITHUB_CLIENT_SECRET,
  );
  const githubUser = await fetchGitHubUser(accessToken);
  const githubUserId = String(githubUser.id);

  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO members (github_user_id, github_login, avatar_url, status)
       VALUES (?, ?, ?, 'active')
       ON CONFLICT(github_user_id) DO UPDATE SET
         github_login = excluded.github_login,
         avatar_url = excluded.avatar_url,
         updated_at = unixepoch()`,
    ).bind(githubUserId, githubUser.login, githubUser.avatar_url),
    env.DB.prepare(
      `INSERT INTO reputation_events (subject_member_id, event_type, repository, external_ref, payload_json)
       SELECT id, 'enrollment.completed', 'yaqub0r/sabiqah', ?, '{}'
       FROM members
       WHERE github_user_id = ?
         AND NOT EXISTS (
           SELECT 1 FROM reputation_events
           WHERE subject_member_id = members.id AND event_type = 'enrollment.completed'
         )`,
    ).bind(`github-user:${githubUserId}`, githubUserId),
  ]);

  const session = await signPayload(
    {
      sub: githubUserId,
      exp: Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS,
    } satisfies SessionState,
    env.SESSION_SECRET,
  );
  const headers = new Headers({ location: safeReturnTo(state.returnTo) });
  headers.append(
    "set-cookie",
    cookie(SESSION_COOKIE, session, { maxAge: SESSION_TTL_SECONDS }),
  );
  headers.append(
    "set-cookie",
    cookie(ENROLLMENT_COOKIE, "", { maxAge: 0, path: "/api/auth" }),
  );
  return new Response(null, { status: 302, headers });
}

async function getSession(request: Request, env: Env): Promise<Response> {
  const member = await authenticatedMember(request, env);
  if (!member)
    return json({ error: "Authentication required" }, { status: 401 });
  return json({
    identity: {
      login: member.github_login,
      avatarUrl: member.avatar_url,
      membershipStatus: member.status,
    },
  });
}

async function getReputation(request: Request, env: Env): Promise<Response> {
  const member = await authenticatedMember(request, env);
  if (!member)
    return json({ error: "Authentication required" }, { status: 401 });
  const events = await env.DB.prepare(
    `SELECT id, event_type, book_slug, repository, external_ref, assessment_label, assessment_model, recorded_at
     FROM reputation_events WHERE subject_member_id = ? ORDER BY id DESC LIMIT 100`,
  )
    .bind(member.id)
    .all();
  return json({ events: events.results });
}

async function beginDecap(request: Request, env: Env): Promise<Response> {
  const member = await authenticatedMember(request, env);
  if (!member || member.status !== "active")
    return json({ error: "Active reviewer access required" }, { status: 403 });
  const state: OAuthState = {
    purpose: "decap",
    nonce: crypto.randomUUID(),
    exp: Math.floor(Date.now() / 1000) + OAUTH_TTL_SECONDS,
  };
  const token = await signPayload(state, env.SESSION_SECRET);
  const redirectUri = `${new URL(request.url).origin}/api/decap/callback`;
  return new Response(null, {
    status: 302,
    headers: {
      location: githubAuthorizationUrl(
        env.GITHUB_CLIENT_ID,
        redirectUri,
        token,
        "public_repo",
      ),
      "set-cookie": cookie(DECAP_COOKIE, token, {
        maxAge: OAUTH_TTL_SECONDS,
        path: "/api/decap",
      }),
    },
  });
}

async function finishDecap(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stateToken = url.searchParams.get("state");
  const cookieToken = parseCookies(request).get(DECAP_COOKIE);
  const state = stateToken
    ? await verifyPayload<OAuthState>(stateToken, env.SESSION_SECRET)
    : null;
  if (
    !code ||
    !stateToken ||
    !cookieToken ||
    !timingSafeEqual(stateToken, cookieToken) ||
    !state ||
    state.purpose !== "decap" ||
    state.exp < Date.now() / 1000
  ) {
    return decapMessage(
      url.origin,
      { error: "OAuth state could not be verified." },
      400,
    );
  }

  const redirectUri = `${url.origin}/api/decap/callback`;
  const accessToken = await exchangeGitHubCode(
    code,
    redirectUri,
    env.GITHUB_CLIENT_ID,
    env.GITHUB_CLIENT_SECRET,
  );
  return decapMessage(url.origin, { token: accessToken, provider: "github" });
}

async function authenticatedMember(
  request: Request,
  env: Env,
): Promise<MemberRow | null> {
  const token = parseCookies(request).get(SESSION_COOKIE);
  if (!token) return null;
  const session = await verifyPayload<SessionState>(token, env.SESSION_SECRET);
  if (!session || session.exp < Date.now() / 1000) return null;
  return env.DB.prepare(
    "SELECT id, github_user_id, github_login, avatar_url, status FROM members WHERE github_user_id = ?",
  )
    .bind(session.sub)
    .first<MemberRow>();
}

async function verifyTurnstile(
  token: string,
  remoteIp: string,
  secret: string,
): Promise<boolean> {
  const form = new FormData();
  form.set("secret", secret);
  form.set("response", token);
  if (remoteIp !== "local") form.set("remoteip", remoteIp);
  const response = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    { method: "POST", body: form },
  );
  const result = (await response.json()) as { success?: boolean };
  return response.ok && result.success === true;
}

function enrollmentFailure(status = 400): Response {
  return json({ error: "The invitation could not be verified." }, { status });
}

function oauthFailure(): Response {
  return json({ error: "OAuth state could not be verified." }, { status: 400 });
}

export function decapMessage(
  origin: string,
  result: { token?: string; provider?: string; error?: string },
  status = 200,
): Response {
  const outcome = result.token ? "success" : "error";
  const message = `authorization:github:${outcome}:${JSON.stringify(result)}`;
  const html = `<!doctype html><meta charset="utf-8"><title>GitHub authorization</title><script>(()=>{const targetOrigin=${JSON.stringify(origin)};const result=${JSON.stringify(message)};const receiveAuthorizationHandshake=(event)=>{if(event.origin!==targetOrigin||event.source!==window.opener||event.data!=="authorizing:github")return;window.removeEventListener("message",receiveAuthorizationHandshake);window.opener.postMessage(result,targetOrigin);window.close();};window.addEventListener("message",receiveAuthorizationHandshake);window.opener?.postMessage("authorizing:github",targetOrigin);})();</script><p>You may close this window.</p>`;
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "set-cookie": cookie(DECAP_COOKIE, "", { maxAge: 0, path: "/api/decap" }),
    },
  });
}
