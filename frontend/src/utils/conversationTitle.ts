const GENERIC_TITLES = new Set(['새로운 대화', '새 대화']);

function normalize(input: string) {
  return input.replace(/\s+/g, ' ').trim();
}

export function buildConversationTitle(input: string, maxLength = 28) {
  const normalized = normalize(input);

  if (!normalized) {
    return '새 대화';
  }

  if (normalized.length <= maxLength) {
    return normalized;
  }

  return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

export function isGenericConversationTitle(title: string) {
  return GENERIC_TITLES.has(normalize(title));
}
