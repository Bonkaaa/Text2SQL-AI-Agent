"use client";

import { useState, useCallback } from "react";
import {
  HistoryItem,
  getHistoryItems,
  addHistoryItem,
  clearHistory,
} from "@/lib/storage";

export function useQueryHistory() {
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>(() => {
    return getHistoryItems();
  });

  const refresh = useCallback(() => {
    setHistoryItems(getHistoryItems());
  }, []);

  const addHistory = useCallback(
    (item: Omit<HistoryItem, "id">) => {
      const added = addHistoryItem(item);
      refresh();
      return added;
    },
    [refresh]
  );

  const clearAll = useCallback(() => {
    clearHistory();
    refresh();
  }, [refresh]);

  return {
    historyItems,
    addHistory,
    clearAll,
    refresh,
  };
}
