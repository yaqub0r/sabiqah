interface GitHubTokenResponse {
  access_token?: string;
  error?: string;
}

export interface GitHubUser {
  id: number;
  login: string;
  avatar_url: string | null;
}

export function githubAuthorizationUrl(
  clientId: string,
  redirectUri: string,
  state: string,
  scope: "read:user" | "public_repo",
): string {
  const url = new URL("https://github.com/login/oauth/authorize");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("scope", scope);
  return url.toString();
}

export async function exchangeGitHubCode(
  code: string,
  redirectUri: string,
  clientId: string,
  clientSecret: string,
): Promise<string> {
  const response = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
      "user-agent": "sabiqah-worker",
    },
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
      code,
      redirect_uri: redirectUri,
    }),
  });
  const result = (await response.json()) as GitHubTokenResponse;
  if (!response.ok || !result.access_token)
    throw new Error(result.error ?? "GitHub token exchange failed");
  return result.access_token;
}

export async function fetchGitHubUser(token: string): Promise<GitHubUser> {
  const response = await fetch("https://api.github.com/user", {
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${token}`,
      "user-agent": "sabiqah-worker",
      "x-github-api-version": "2022-11-28",
    },
  });
  if (!response.ok) throw new Error("GitHub identity lookup failed");
  return (await response.json()) as GitHubUser;
}
