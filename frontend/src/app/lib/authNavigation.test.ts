import test from "node:test";
import assert from "node:assert/strict";

import {
  buildAppPath,
  buildLoginPath,
  consumeLoginRedirectTarget,
  getAuthStorageKeys,
  getScopedStorageKey,
  rememberLoginRedirectTarget,
  toAppRelativePath,
} from "./authNavigation.ts";

test("buildAppPath prefixes the configured base path", () => {
  assert.equal(buildAppPath("/login", "/dev/"), "/dev/login");
  assert.equal(buildAppPath("/search", "/"), "/search");
});

test("toAppRelativePath strips the configured base path", () => {
  assert.equal(
    toAppRelativePath("/dev/search?type=api#detail", "/dev/"),
    "/search?type=api#detail",
  );
  assert.equal(toAppRelativePath("/search?type=api", "/"), "/search?type=api");
});

test("buildLoginPath keeps users inside the current app base path", () => {
  assert.equal(
    buildLoginPath("/search?type=api", "/dev/"),
    "/dev/login?next=%2Fsearch%3Ftype%3Dapi",
  );
  assert.equal(buildLoginPath("/", "/"), "/login");
});

test("auth storage keys are scoped by app base path", () => {
  assert.deepEqual(getAuthStorageKeys("/"), {
    accessToken: "auth-access-token",
    refreshToken: "auth-refresh-token",
    redirectTarget: "auth-login-redirect-target",
    storage: "auth-storage",
  });

  assert.deepEqual(getAuthStorageKeys("/dev/"), {
    accessToken: "auth-access-token::dev",
    refreshToken: "auth-refresh-token::dev",
    redirectTarget: "auth-login-redirect-target::dev",
    storage: "auth-storage::dev",
  });
});

test("generic storage keys are scoped by app base path", () => {
  assert.equal(getScopedStorageKey("chat-storage", "/"), "chat-storage");
  assert.equal(getScopedStorageKey("chat-storage", "/dev/"), "chat-storage::dev");
  assert.equal(
    getScopedStorageKey("community-storage", "/dev/admin/"),
    "community-storage::dev:admin",
  );
});

test("login redirect target is stored per app base path and consumed once", () => {
  const storage = new Map<string, string>();
  const sessionStorage = {
    getItem(key: string) {
      return storage.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      storage.set(key, value);
    },
    removeItem(key: string) {
      storage.delete(key);
    },
  };

  rememberLoginRedirectTarget("/dev/search?tab=api", "/dev/", sessionStorage);

  assert.equal(
    consumeLoginRedirectTarget("/dev/", sessionStorage),
    "/search?tab=api",
  );
  assert.equal(consumeLoginRedirectTarget("/dev/", sessionStorage), null);
});
