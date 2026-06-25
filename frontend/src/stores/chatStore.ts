import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { SearchResultData } from '@/types/recommendation';
import { getAuthStorageKeys, getScopedStorageKey } from '@/app/lib/authNavigation';

const CHAT_STORAGE_BASE_KEY = getScopedStorageKey('chat-storage');
const CHAT_STORAGE_GUEST_KEY = `${CHAT_STORAGE_BASE_KEY}::guest`;
const CHAT_STORAGE_USER_PREFIX = `${CHAT_STORAGE_BASE_KEY}::user:`;
const CHAT_STORAGE_LEGACY_KEY = CHAT_STORAGE_BASE_KEY;

const { accessToken: CHAT_ACCESS_TOKEN_KEY } = getAuthStorageKeys();

let activeChatStorageKey = resolveActiveChatStorageKey();
let suppressChatPersistWrites = false;

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padding = normalized.length % 4;
  const withPadding = padding === 0 ? normalized : `${normalized}${'='.repeat(4 - padding)}`;
  return globalThis.atob(withPadding);
}

function readActiveUserIdFromToken() {
  if (typeof localStorage === 'undefined') {
    return null;
  }

  const token = localStorage.getItem(CHAT_ACCESS_TOKEN_KEY);
  if (!token) {
    return null;
  }

  const [, payload] = token.split('.');
  if (!payload) {
    return null;
  }

  try {
    const parsed = JSON.parse(decodeBase64Url(payload)) as { sub?: string | number };
    if (parsed.sub === undefined || parsed.sub === null) {
      return null;
    }
    return String(parsed.sub);
  } catch {
    return null;
  }
}

function buildChatStorageKeyForUser(userId: string | null) {
  if (!userId) {
    return CHAT_STORAGE_GUEST_KEY;
  }

  return `${CHAT_STORAGE_USER_PREFIX}${userId}`;
}

function resolveActiveChatStorageKey() {
  return buildChatStorageKeyForUser(readActiveUserIdFromToken());
}

function isUserScopedChatKey(key: string) {
  return key.startsWith(CHAT_STORAGE_USER_PREFIX);
}

function migrateLegacyChatStorageIfNeeded(scopeKey: string) {
  if (typeof localStorage === 'undefined') {
    return;
  }

  if (!isUserScopedChatKey(scopeKey)) {
    return;
  }

  if (localStorage.getItem(scopeKey) !== null) {
    return;
  }

  const legacyValue = localStorage.getItem(CHAT_STORAGE_LEGACY_KEY);
  if (!legacyValue) {
    return;
  }

  localStorage.setItem(scopeKey, legacyValue);
  localStorage.removeItem(CHAT_STORAGE_LEGACY_KEY);
}

function getChatPersistStorage() {
  return {
    getItem: () => {
      if (typeof localStorage === 'undefined') {
        return null;
      }

      return localStorage.getItem(activeChatStorageKey);
    },
    setItem: (_name: string, value: string) => {
      if (typeof localStorage === 'undefined' || suppressChatPersistWrites) {
        return;
      }

      localStorage.setItem(activeChatStorageKey, value);
    },
    removeItem: () => {
      if (typeof localStorage === 'undefined' || suppressChatPersistWrites) {
        return;
      }

      localStorage.removeItem(activeChatStorageKey);
    },
  };
}

type PersistedChatSnapshot = typeof baseChatState;

function readPersistedChatSnapshot(storageKey: string): PersistedChatSnapshot | null {
  if (typeof localStorage === 'undefined') {
    return null;
  }

  const raw = localStorage.getItem(storageKey);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as { state?: Partial<PersistedChatSnapshot> };
    const state = parsed?.state;
    if (!state) {
      return null;
    }

    return {
      ...initialChatState,
      ...state,
    };
  } catch {
    return null;
  }
}

function normalizeResourceName(name: string) {
  return name.trim().toLowerCase();
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  searchResult?: SearchResultData;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  isPinned?: boolean;
  projectId?: string | null; // 프로젝트 ID, null이면 "내 채팅"
}

export interface Project {
  id: string;
  name: string;
  createdAt: number;
  recentSearches?: string[];
  savedResources?: { name: string; type: 'dataset' | 'api' }[];
  comparisons?: Array<ComparisonItem | string>;
}

export interface ComparisonItem {
  id: string;
  name: string;
  type: 'dataset' | 'api';
  addedAt: number;
}

interface ChatState {
  conversations: Conversation[];
  projects: Project[];
  currentConversationId: string | null;
  currentProjectId: string | null;
  isSidebarOpen: boolean;
  isLoading: boolean;
  
  // Actions
  addConversation: (conversation: Conversation) => void;
  upsertConversation: (conversation: Conversation) => void;
  deleteConversation: (id: string) => void;
  setCurrentConversation: (id: string | null) => void;
  selectConversation: (id: string | null) => void;
  replaceConversationId: (previousId: string, nextId: string) => void;
  addMessage: (conversationId: string, message: Message) => void;
  updateConversationTitle: (id: string, title: string) => void;
  togglePinConversation: (id: string) => void;
  addProject: (project: Project) => void;
  deleteProject: (id: string) => void;
  setCurrentProject: (id: string | null) => void;
  updateProjectName: (id: string, name: string) => void;
  toggleProjectSavedResource: (projectId: string, item: { name: string; type: 'dataset' | 'api' }) => void;
  addProjectComparison: (projectId: string, item: Omit<ComparisonItem, 'id' | 'addedAt'>) => void;
  removeProjectComparison: (projectId: string, comparisonId: string) => void;
  toggleSidebar: () => void;
  setLoading: (loading: boolean) => void;
  getCurrentConversation: () => Conversation | null;
  getCurrentProject: () => Project | null;
  addConversationToProject: (projectId: string) => void;
  resetState: () => void;
}

const baseChatState = {
  conversations: [] as Conversation[],
  projects: [] as Project[],
  currentConversationId: null as string | null,
  currentProjectId: null as string | null,
  isSidebarOpen: false,
  isLoading: false,
};

const initialChatState =
  readPersistedChatSnapshot(activeChatStorageKey) ?? baseChatState;

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
  ...initialChatState,

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
      currentConversationId: conversation.id,
      currentProjectId: conversation.projectId ?? null,
    })),

  upsertConversation: (conversation) =>
    set((state) => {
      const existingConversation = state.conversations.find((item) => item.id === conversation.id);

      if (existingConversation) {
        return {
          conversations: state.conversations.map((item) =>
            item.id === conversation.id
              ? {
                  ...conversation,
                  projectId: existingConversation.projectId ?? conversation.projectId ?? null,
                  isPinned: existingConversation.isPinned ?? conversation.isPinned,
                }
              : item,
          ),
        };
      }

      return {
        conversations: [conversation, ...state.conversations],
      };
    }),

  deleteConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((conv) => conv.id !== id),
      currentConversationId: state.currentConversationId === id ? null : state.currentConversationId,
    })),

  setCurrentConversation: (id) =>
    set({ currentConversationId: id }),

  selectConversation: (id) =>
    set((state) => {
      if (id === null) {
        return { currentConversationId: null };
      }

      const conversation = state.conversations.find((conv) => conv.id === id);
      if (!conversation) {
        return { currentConversationId: id };
      }

      return {
        currentConversationId: id,
        currentProjectId: conversation.projectId ?? null,
      };
    }),

  replaceConversationId: (previousId, nextId) =>
    set((state) => ({
      conversations: state.conversations.map((conversation) =>
        conversation.id === previousId ? { ...conversation, id: nextId } : conversation,
      ),
      currentConversationId: state.currentConversationId === previousId ? nextId : state.currentConversationId,
    })),

  addMessage: (conversationId, message) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id === conversationId
          ? {
              ...conv,
              messages: [...conv.messages, message],
              updatedAt: Date.now(),
            }
          : conv
      ),
    })),

  updateConversationTitle: (id, title) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id === id ? { ...conv, title } : conv
      ),
    })),

  togglePinConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id === id ? { ...conv, isPinned: !conv.isPinned } : conv
      ),
    })),

  addProject: (project) =>
    set((state) => ({
      projects: [project, ...state.projects],
      currentProjectId: project.id,
    })),

  deleteProject: (id) =>
    set((state) => ({
      projects: state.projects.filter((proj) => proj.id !== id),
      currentProjectId: state.currentProjectId === id ? null : state.currentProjectId,
    })),

  setCurrentProject: (id) =>
    set({ currentProjectId: id }),

  updateProjectName: (id, name) =>
    set((state) => ({
      projects: state.projects.map((proj) =>
        proj.id === id ? { ...proj, name } : proj
      ),
    })),

  toggleProjectSavedResource: (projectId, item) =>
    set((state) => ({
      projects: state.projects.map((proj) => {
        if (proj.id !== projectId) {
          return proj;
        }

        const normalizedItemName = normalizeResourceName(item.name);
        const savedResources = proj.savedResources ?? [];
        const exists = savedResources.some(
          (resource) =>
            normalizeResourceName(resource.name) === normalizedItemName && resource.type === item.type,
        );

        if (exists) {
          return {
            ...proj,
            savedResources: savedResources.filter(
              (resource) =>
                !(
                  normalizeResourceName(resource.name) === normalizedItemName &&
                  resource.type === item.type
                ),
            ),
          };
        }

        return {
          ...proj,
          savedResources: [{ ...item, name: item.name.trim() }, ...savedResources],
        };
      }),
    })),

  addProjectComparison: (projectId, item) =>
    set((state) => ({
      projects: state.projects.map((proj) => {
        if (proj.id !== projectId) {
          return proj;
        }

        const currentComparisons = proj.comparisons ?? [];
        const alreadyExists = currentComparisons.some((comparison) => {
          if (typeof comparison === 'string') {
            return comparison === item.name;
          }

          return comparison.name === item.name && comparison.type === item.type;
        });

        if (alreadyExists) {
          return proj;
        }

        const nextItem: ComparisonItem = {
          id: `cmp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          name: item.name,
          type: item.type,
          addedAt: Date.now(),
        };

        return {
          ...proj,
          comparisons: [nextItem, ...currentComparisons],
        };
      }),
    })),

  removeProjectComparison: (projectId, comparisonId) =>
    set((state) => ({
      projects: state.projects.map((proj) => {
        if (proj.id !== projectId) {
          return proj;
        }

        const currentComparisons = proj.comparisons ?? [];
        return {
          ...proj,
          comparisons: currentComparisons.filter((comparison, index) => {
            if (typeof comparison === 'string') {
              return `legacy-${proj.id}-${index}` !== comparisonId;
            }

            return comparison.id !== comparisonId;
          }),
        };
      }),
    })),

  toggleSidebar: () =>
    set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  setLoading: (loading) =>
    set({ isLoading: loading }),

  getCurrentConversation: () => {
    const { conversations, currentConversationId } = get();
    return conversations.find((conv) => conv.id === currentConversationId) || null;
  },

  getCurrentProject: () => {
    const { projects, currentProjectId } = get();
    return projects.find((proj) => proj.id === currentProjectId) || null;
  },

  addConversationToProject: (projectId) => {
    const { conversations, currentConversationId } = get();
    const currentConversation = conversations.find((conv) => conv.id === currentConversationId);
    if (currentConversation) {
      set((state) => ({
        conversations: state.conversations.map((conv) =>
          conv.id === currentConversationId ? { ...conv, projectId } : conv
        ),
      }));
    }
  },
  resetState: () =>
    set({
      ...baseChatState,
    }),
    }),
    {
      name: CHAT_STORAGE_BASE_KEY,
      storage: createJSONStorage(getChatPersistStorage),
      partialize: (state) => ({
        conversations: state.conversations,
        projects: state.projects,
        currentConversationId: state.currentConversationId,
        currentProjectId: state.currentProjectId,
        isSidebarOpen: state.isSidebarOpen,
      }),
    }
  )
);

export function resetChatStore() {
  useChatStore.getState().resetState();
}

export async function syncChatStoreToCurrentSession() {
  const nextStorageKey = resolveActiveChatStorageKey();
  migrateLegacyChatStorageIfNeeded(nextStorageKey);

  if (nextStorageKey === CHAT_STORAGE_GUEST_KEY && typeof localStorage !== 'undefined') {
    localStorage.removeItem(CHAT_STORAGE_GUEST_KEY);
  }

  activeChatStorageKey = nextStorageKey;
  const nextState = readPersistedChatSnapshot(nextStorageKey) ?? baseChatState;

  suppressChatPersistWrites = true;
  try {
    useChatStore.setState({
      ...nextState,
    });
  } finally {
    suppressChatPersistWrites = false;
  }
}
