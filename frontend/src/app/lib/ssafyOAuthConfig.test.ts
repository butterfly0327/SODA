import test from "node:test";
import assert from "node:assert/strict";

import {
  DEFAULT_SSAFY_AUTHORIZE_URL,
  buildDefaultRedirectUri,
  resolveSsafyOAuthConfig,
} from "./ssafyOAuthConfig.ts";

test("resolveSsafyOAuthConfig reads SSAFY client id and redirect url from env", () => {
  const config = resolveSsafyOAuthConfig(
    {
      SSAFY_CLIENT_ID: "ssafy-client",
      SSAFY_REDIRECT_URL: "http://localhost:5173/auth/callback",
      SSAFY_AUTHORIZE_URL: "https://example.com/custom-authorize",
    },
    {
      basePath: "/",
      origin: "http://localhost:5173",
    },
  );

  assert.deepEqual(config, {
    authorizeBase: "https://example.com/custom-authorize",
    clientId: "ssafy-client",
    redirectUri: "http://localhost:5173/auth/callback",
  });
});

test("resolveSsafyOAuthConfig falls back to defaults when SSAFY env is missing", () => {
  const config = resolveSsafyOAuthConfig(
    {},
    {
      basePath: "/dev/",
      origin: "http://localhost:5173",
    },
  );

  assert.equal(config.authorizeBase, DEFAULT_SSAFY_AUTHORIZE_URL);
  assert.equal(config.clientId, "");
  assert.equal(config.redirectUri, "http://localhost:5173/dev/auth/callback");
});

test("buildDefaultRedirectUri honors the configured base path", () => {
  assert.equal(
    buildDefaultRedirectUri("/dev/", "http://localhost:5173"),
    "http://localhost:5173/dev/auth/callback",
  );
  assert.equal(
    buildDefaultRedirectUri("/", "http://localhost:5173"),
    "http://localhost:5173/auth/callback",
  );
});
