import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { LanguageProvider, useLanguage } from "../LanguageContext";

describe("LanguageContext & Bilingual Support (Ponytail i18n)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should provide default English locale and correct translation keys", () => {
    const { result } = renderHook(() => useLanguage(), {
      wrapper: ({ children }) => <LanguageProvider>{children}</LanguageProvider>,
    });

    expect(result.current.locale).toBe("en");
    expect(result.current.t("nav.workspace")).toBe("Workspace");
    expect(result.current.t("workspace.tabAnswer")).toBe("Answer");
    expect(result.current.t("workspace.tabTable")).toBe("Table");
    expect(result.current.t("workspace.tabChart")).toBe("Chart");
    expect(result.current.t("workspace.tabSql")).toBe("SQL");
    expect(result.current.t("workspace.tabTrace")).toBe("Trace");
    expect(result.current.t("settings.title")).toBe("Workspace Settings");
  });

  it("should switch to Vietnamese locale and return Vietnamese translations across all tabs", () => {
    const { result } = renderHook(() => useLanguage(), {
      wrapper: ({ children }) => <LanguageProvider>{children}</LanguageProvider>,
    });

    act(() => {
      result.current.setLocale("vi");
    });

    expect(result.current.locale).toBe("vi");
    expect(result.current.t("nav.workspace")).toBe("Không gian làm việc");
    // Workspace tabs
    expect(result.current.t("workspace.tabAnswer")).toBe("Câu trả lời");
    expect(result.current.t("workspace.tabTable")).toBe("Bảng dữ liệu");
    expect(result.current.t("workspace.tabChart")).toBe("Biểu đồ");
    expect(result.current.t("workspace.tabSql")).toBe("Mã SQL");
    expect(result.current.t("workspace.tabTrace")).toBe("Tiến trình");
    // Inner view content
    expect(result.current.t("workspace.executiveSummary")).toBe("Tóm tắt điều hành");
    expect(result.current.t("workspace.astVerified")).toBe("Đã kiểm duyệt AST");
    expect(result.current.t("workspace.provenanceTitle")).toBe("Tiến trình thực thi & Truy vết Agent");
    expect(result.current.t("sources.columnsAndTypes")).toBe("Cột & Kiểu dữ liệu");
    expect(result.current.t("settings.title")).toBe("Cài đặt không gian làm việc");
    expect(localStorage.getItem("querypilot_locale")).toBe("vi");
  });

  it("should toggle between en and vi using toggleLocale", () => {
    const { result } = renderHook(() => useLanguage(), {
      wrapper: ({ children }) => <LanguageProvider initialLocale="en">{children}</LanguageProvider>,
    });

    expect(result.current.locale).toBe("en");

    act(() => {
      result.current.toggleLocale();
    });
    expect(result.current.locale).toBe("vi");

    act(() => {
      result.current.toggleLocale();
    });
    expect(result.current.locale).toBe("en");
  });

  it("should gracefully fallback to English or fallback string when key is unknown", () => {
    const { result } = renderHook(() => useLanguage(), {
      wrapper: ({ children }) => <LanguageProvider>{children}</LanguageProvider>,
    });

    expect(result.current.t("non.existent.key", "Custom Fallback")).toBe("Custom Fallback");
  });

  it("should not crash if used outside LanguageProvider and provide safe defaults", () => {
    const { result } = renderHook(() => useLanguage());

    expect(result.current.locale).toBe("en");
    expect(result.current.t("nav.workspace")).toBe("Workspace");
  });
});
