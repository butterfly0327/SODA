type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function getRuntimeBasePath() {
  return import.meta.env.BASE_URL || "/";
}

export function normalizeBasePath(rawBasePath = getRuntimeBasePath()) {
  const trimmed = rawBasePath.trim();
  if (!trimmed || trimmed === "/") {
    return "";
  }

  const prefixed = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return prefixed.replace(/\/+$/, "");
}

function normalizeRoutePath(path: string) {
  if (!path) {
    return "/";
  }

  return path.startsWith("/") ? path : `/${path}`;
}

export function buildAppPath(path: string, rawBasePath = getRuntimeBasePath()) {
  const basePath = normalizeBasePath(rawBasePath);
  const routePath = normalizeRoutePath(path);
  return `${basePath}${routePath}` || "/";
}

function splitPathParts(input: string) {
  if (/^https?:\/\//.test(input)) {
    const url = new URL(input);
    return {
      pathname: url.pathname,
      search: url.search,
      hash: url.hash,
    };
  }

  const hashIndex = input.indexOf("#");
  const hash = hashIndex >= 0 ? input.slice(hashIndex) : "";
  const pathWithSearch = hashIndex >= 0 ? input.slice(0, hashIndex) : input;
  const searchIndex = pathWithSearch.indexOf("?");

  return {
    pathname: searchIndex >= 0 ? pathWithSearch.slice(0, searchIndex) : pathWithSearch,
    search: searchIndex >= 0 ? pathWithSearch.slice(searchIndex) : "",
    hash,
  };
}

export function toAppRelativePath(input: string, rawBasePath = getRuntimeBasePath()) {
  const { pathname, search, hash } = splitPathParts(input);
  const basePath = normalizeBasePath(rawBasePath);
  const normalizedPathname = normalizeRoutePath(pathname || "/");

  if (!basePath) {
    return `${normalizedPathname}${search}${hash}`;
  }

  if (normalizedPathname === basePath) {
    return `/${search}${hash}`.replace(/^\/(?=[?#])/, "/");
  }

  if (normalizedPathname.startsWith(`${basePath}/`)) {
    return `${normalizedPathname.slice(basePath.length)}${search}${hash}`;
  }

  return `${normalizedPathname}${search}${hash}`;
}

function buildScopedKey(baseKey: string, rawBasePath = getRuntimeBasePath()) {
  const scope = normalizeBasePath(rawBasePath).replace(/^\//, "").replace(/\//g, ":");
  if (!scope) {
    return baseKey;
  }

  return `${baseKey}::${scope}`;
}

export function getScopedStorageKey(baseKey: string, rawBasePath = getRuntimeBasePath()) {
  return buildScopedKey(baseKey, rawBasePath);
}

export function getAuthStorageKeys(rawBasePath = getRuntimeBasePath()) {
  return {
    accessToken: buildScopedKey("auth-access-token", rawBasePath),
    refreshToken: buildScopedKey("auth-refresh-token", rawBasePath),
    redirectTarget: buildScopedKey("auth-login-redirect-target", rawBasePath),
    storage: buildScopedKey("auth-storage", rawBasePath),
  };
}

export function buildLoginPath(nextPath?: string | null, rawBasePath = getRuntimeBasePath()) {
  const loginPath = buildAppPath("/login", rawBasePath);
  if (!nextPath) {
    return loginPath;
  }

  const normalizedNextPath = toAppRelativePath(nextPath, rawBasePath);
  if (normalizedNextPath === "/" || normalizedNextPath.startsWith("/login")) {
    return loginPath;
  }

  const url = new URL(loginPath, "http://local.test");
  url.searchParams.set("next", normalizedNextPath);
  return `${url.pathname}${url.search}`;
}

function getSessionStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.sessionStorage;
}

export function rememberLoginRedirectTarget(
  nextPath: string,
  rawBasePath = getRuntimeBasePath(),
  storage: StorageLike | null = getSessionStorage(),
) {
  if (!storage) {
    return;
  }

  const normalizedNextPath = toAppRelativePath(nextPath, rawBasePath);
  const { redirectTarget } = getAuthStorageKeys(rawBasePath);

  if (
    !normalizedNextPath ||
    normalizedNextPath === "/" ||
    normalizedNextPath.startsWith("/auth/callback")
  ) {
    storage.removeItem(redirectTarget);
    return;
  }

  storage.setItem(redirectTarget, normalizedNextPath);
}

export function consumeLoginRedirectTarget(
  rawBasePath = getRuntimeBasePath(),
  storage: StorageLike | null = getSessionStorage(),
) {
  if (!storage) {
    return null;
  }

  const { redirectTarget } = getAuthStorageKeys(rawBasePath);
  const nextPath = storage.getItem(redirectTarget);
  if (!nextPath) {
    return null;
  }

  storage.removeItem(redirectTarget);
  return nextPath;
}
