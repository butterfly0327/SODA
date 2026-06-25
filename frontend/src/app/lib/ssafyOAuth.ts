import { resolveSsafyOAuthConfig } from "./ssafyOAuthConfig";

export function buildSsafyAuthorizeUrl() {
  const { authorizeBase, clientId, redirectUri } = resolveSsafyOAuthConfig(
    import.meta.env,
    {
      basePath: import.meta.env.BASE_URL || "/",
      origin: window.location.origin,
    },
  );

  const url = new URL(authorizeBase, window.location.origin);
  if (clientId) {
    url.searchParams.set("client_id", clientId);
  }
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("response_type", "code");

  return url.toString();
}
