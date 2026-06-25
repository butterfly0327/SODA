import assert from "node:assert/strict";
import test from "node:test";

import { shouldResetUiStateForAuthTransition } from "./uiStateIsolation.ts";

test("auth transition resets UI state when user changes", () => {
  assert.equal(shouldResetUiStateForAuthTransition("user-1", "user-2"), true);
  assert.equal(shouldResetUiStateForAuthTransition(null, "user-2"), true);
  assert.equal(shouldResetUiStateForAuthTransition("user-1", null), true);
});

test("auth transition keeps UI state for the same user", () => {
  assert.equal(shouldResetUiStateForAuthTransition("user-1", "user-1"), false);
  assert.equal(shouldResetUiStateForAuthTransition(" user-1 ", "user-1"), false);
  assert.equal(shouldResetUiStateForAuthTransition(undefined, undefined), false);
});
