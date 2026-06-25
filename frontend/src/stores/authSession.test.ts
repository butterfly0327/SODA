import test from "node:test";
import assert from "node:assert/strict";

import {
  resolveAuthSnapshot,
  resolveStoredSession,
} from "./authSession.ts";

function createToken(exp: number) {
  const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify({ exp })).toString("base64url");
  return `${header}.${payload}.signature`;
}

test("stored auth session exists only when access token is present and not expired", () => {
  const validToken = createToken(Math.floor(Date.now() / 1000) + 3600);
  const expiredToken = createToken(Math.floor(Date.now() / 1000) - 3600);

  assert.equal(resolveStoredSession(validToken, null), true);
  assert.equal(resolveStoredSession(null, "refresh-token"), false);
  assert.equal(resolveStoredSession(expiredToken, "refresh-token"), false);
});

test("persisted unauthenticated state is ignored when tokens already exist", () => {
  const snapshot = resolveAuthSnapshot(
    {
      isAuthenticated: false,
      status: "unauthenticated",
      user: null,
    },
    true,
  );

  assert.equal(snapshot.isAuthenticated, true);
  assert.equal(snapshot.status, "authenticated");
});

test("persisted authenticated state is ignored when there is no stored session", () => {
  const snapshot = resolveAuthSnapshot(
    {
      isAuthenticated: true,
      status: "authenticated",
      user: {
        id: "user-1",
        email: "test@example.com",
        name: "tester",
      },
    },
    false,
  );

  assert.equal(snapshot.isAuthenticated, false);
  assert.equal(snapshot.status, "unauthenticated");
  assert.equal(snapshot.user, null);
});
