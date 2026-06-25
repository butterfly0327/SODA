export const DEFAULT_SSAFY_AUTHORIZE_URL =
  "https://project.ssafy.com/oauth/sso-check";

interface SsafyOAuthEnvLike {
  BASE_URL?: string;
  SSAFY_AUTHORIZE_URL?: string;
  SSAFY_CLIENT_ID?: string;
  SSAFY_REDIRECT_URL?: string;
}

interface ResolveSsafyOAuthOptions {
  basePath?: string;
  origin?: string;
}

export function buildDefaultRedirectUri(
  rawBasePath = "/",
  origin = "http://localhost",
) {
  const normalizedBasePath =
    rawBasePath === "/" ? "" : rawBasePath.replace(/\/$/, "");

  return `${origin}${normalizedBasePath}/auth/callback`;
}

export function resolveSsafyOAuthConfig(
  env: SsafyOAuthEnvLike,
  options: ResolveSsafyOAuthOptions = {},
) {
  const basePath = options.basePath ?? env.BASE_URL ?? "/";
  const origin = options.origin ?? "http://localhost";

  return {
    authorizeBase: env.SSAFY_AUTHORIZE_URL || DEFAULT_SSAFY_AUTHORIZE_URL,
    clientId: env.SSAFY_CLIENT_ID || "",
    redirectUri:
      env.SSAFY_REDIRECT_URL || buildDefaultRedirectUri(basePath, origin),
  };
}
