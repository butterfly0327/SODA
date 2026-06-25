import { create } from "zustand";

type ResourceBookmarkType = "DATASET" | "OPEN_API";

export type ResourceBookmarkEntry = {
  resourceId: number;
  resourceType: ResourceBookmarkType;
  isBookmarked: boolean;
  bookmarkId?: number | null;
};

type ResourceBookmarkState = {
  entries: Record<string, ResourceBookmarkEntry>;
  primeBookmarkState: (entry: ResourceBookmarkEntry) => void;
  setBookmarkState: (entry: ResourceBookmarkEntry) => void;
  seedBookmarks: (
    items: Array<{
      bookmarkId: number;
      type: ResourceBookmarkType;
      id: number;
    }>,
  ) => void;
  clearBookmarkState: (resourceType: ResourceBookmarkType, resourceId: number) => void;
};

export function buildResourceBookmarkKey(
  resourceType: ResourceBookmarkType,
  resourceId: number,
) {
  return `${resourceType}:${resourceId}`;
}

export const useResourceBookmarkStore = create<ResourceBookmarkState>((set) => ({
  entries: {},
  primeBookmarkState: (entry) =>
    set((state) => {
      const key = buildResourceBookmarkKey(entry.resourceType, entry.resourceId);
      if (state.entries[key]) {
        return state;
      }

      return {
        entries: {
          ...state.entries,
          [key]: entry,
        },
      };
    }),
  setBookmarkState: (entry) =>
    set((state) => ({
      entries: {
        ...state.entries,
        [buildResourceBookmarkKey(entry.resourceType, entry.resourceId)]: entry,
      },
    })),
  seedBookmarks: (items) =>
    set((state) => {
      const nextEntries = { ...state.entries };

      for (const item of items) {
        nextEntries[buildResourceBookmarkKey(item.type, item.id)] = {
          resourceId: item.id,
          resourceType: item.type,
          isBookmarked: true,
          bookmarkId: item.bookmarkId,
        };
      }

      return { entries: nextEntries };
    }),
  clearBookmarkState: (resourceType, resourceId) =>
    set((state) => ({
      entries: {
        ...state.entries,
        [buildResourceBookmarkKey(resourceType, resourceId)]: {
          resourceId,
          resourceType,
          isBookmarked: false,
          bookmarkId: null,
        },
      },
    })),
}));
