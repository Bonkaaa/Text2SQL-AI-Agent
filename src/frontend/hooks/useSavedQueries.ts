"use client";

import { useState, useEffect, useCallback } from "react";
import {
  SavedQueryItem,
  getSavedQueries,
  saveQueryItem,
  deleteSavedQuery,
  isQuerySaved,
} from "@/lib/storage";

export function useSavedQueries() {
  const [savedQueries, setSavedQueries] = useState<SavedQueryItem[]>(() => {
    return getSavedQueries();
  });

  const refresh = useCallback(() => {
    setSavedQueries(getSavedQueries());
  }, []);

  const saveQuery = useCallback(
    (item: { title: string; question: string; sql?: string; tag?: string }) => {
      const saved = saveQueryItem(item);
      refresh();
      return saved;
    },
    [refresh]
  );

  const removeQuery = useCallback(
    (id: string) => {
      deleteSavedQuery(id);
      refresh();
    },
    [refresh]
  );

  const isSaved = useCallback(
    (question: string) => {
      return isQuerySaved(question);
    },
    []
  );

  return {
    savedQueries,
    saveQuery,
    removeQuery,
    isSaved,
    refresh,
  };
}
