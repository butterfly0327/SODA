function normalizeUserId(userId?: string | null) {
  const trimmed = userId?.trim();
  return trimmed ? trimmed : null;
}

export function shouldResetUiStateForAuthTransition(
  previousUserId?: string | null,
  nextUserId?: string | null,
) {
  return normalizeUserId(previousUserId) !== normalizeUserId(nextUserId);
}
