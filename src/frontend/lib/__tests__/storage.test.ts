import { describe, it, expect, beforeEach } from "vitest";
import {
  getSavedQueries,
  saveQueryItem,
  deleteSavedQuery,
  isQuerySaved,
  getHistoryItems,
  addHistoryItem,
} from "../storage";

describe("Client Storage Repository Layer (TDD Suite 1)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("Saved Queries Storage", () => {
    it("should return preset queries if storage is empty", () => {
      const initial = getSavedQueries();
      expect(initial.length).toBeGreaterThanOrEqual(1);
      expect(initial.some((q) => q.question.includes("revenue"))).toBe(true);
    });

    it("should save a new query and avoid duplicate questions", () => {
      const newItem = saveQueryItem({
        title: "Test Top Customers",
        question: "Which customers generated the most revenue in 2003?",
        sql: "SELECT * FROM customer LIMIT 10;",
        tag: "Customer",
      });

      expect(newItem.id).toBeDefined();
      expect(isQuerySaved("Which customers generated the most revenue in 2003?")).toBe(true);

      const all = getSavedQueries();
      expect(all.some((q) => q.id === newItem.id)).toBe(true);

      // Duplication check: saving same question returns existing or doesn't add duplicate
      const duplicate = saveQueryItem({
        title: "Duplicate",
        question: "Which customers generated the most revenue in 2003?",
      });
      expect(duplicate.id).toBe(newItem.id);
    });

    it("should delete a saved query by id", () => {
      const item = saveQueryItem({
        title: "To be deleted",
        question: "Question to delete?",
      });

      deleteSavedQuery(item.id);
      const after = getSavedQueries();
      expect(after.some((q) => q.id === item.id)).toBe(false);
    });
  });

  describe("Query History Storage", () => {
    it("should record a history execution item", () => {
      const historyItem = addHistoryItem({
        question: "Store sales quarterly 2002",
        sql: "SELECT * FROM store_sales LIMIT 5;",
        status: "SUCCESS",
        rowCount: 5,
        executionTimeMs: 142,
        timestamp: "2026-10-09 10:15",
      });

      expect(historyItem.id).toBeDefined();
      const allHistory = getHistoryItems();
      expect(allHistory.some((h) => h.id === historyItem.id)).toBe(true);
    });
  });
});
