import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSavedQueries } from "../useSavedQueries";

describe("useSavedQueries Hook (TDD Suite 2)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should initialize with list of saved queries", () => {
    const { result } = renderHook(() => useSavedQueries());
    expect(result.current.savedQueries.length).toBeGreaterThan(0);
  });

  it("should add a new saved query and update list", () => {
    const { result } = renderHook(() => useSavedQueries());

    act(() => {
      result.current.saveQuery({
        title: "Web returns monthly",
        question: "Monthly return rates for web channel?",
        tag: "Returns",
      });
    });

    expect(result.current.isSaved("Monthly return rates for web channel?")).toBe(true);
    expect(
      result.current.savedQueries.some((q) => q.title === "Web returns monthly")
    ).toBe(true);
  });

  it("should remove query by id", () => {
    const { result } = renderHook(() => useSavedQueries());

    let targetId = "";
    act(() => {
      const added = result.current.saveQuery({
        title: "Query to delete",
        question: "Will be removed?",
      });
      targetId = added.id;
    });

    expect(result.current.savedQueries.some((q) => q.id === targetId)).toBe(true);

    act(() => {
      result.current.removeQuery(targetId);
    });

    expect(result.current.savedQueries.some((q) => q.id === targetId)).toBe(false);
  });
});
