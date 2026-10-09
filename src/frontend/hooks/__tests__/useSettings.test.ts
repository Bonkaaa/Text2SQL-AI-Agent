import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSettings, DEFAULT_SETTINGS } from "../useSettings";

describe("useSettings Hook (TDD Suite 1)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should initialize with default settings", () => {
    const { result } = renderHook(() => useSettings());

    expect(result.current.settings).toEqual({
      readOnly: true,
      defaultRowLimit: 100,
      showTrace: true,
      requireHitlApproval: true,
    });
    expect(result.current.settings).toEqual(DEFAULT_SETTINGS);
  });

  it("should update individual settings and persist to localStorage", () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({
        readOnly: false,
        defaultRowLimit: 250,
      });
    });

    expect(result.current.settings.readOnly).toBe(false);
    expect(result.current.settings.defaultRowLimit).toBe(250);
    expect(result.current.settings.showTrace).toBe(true);
    expect(result.current.settings.requireHitlApproval).toBe(true);

    // Verify persistence
    const saved = JSON.parse(localStorage.getItem("querypilot_settings") || "{}");
    expect(saved.readOnly).toBe(false);
    expect(saved.defaultRowLimit).toBe(250);
  });

  it("should toggle boolean settings and update correctly", () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({
        showTrace: false,
        requireHitlApproval: false,
      });
    });

    expect(result.current.settings.showTrace).toBe(false);
    expect(result.current.settings.requireHitlApproval).toBe(false);
  });

  it("should reset settings to default values", () => {
    const { result } = renderHook(() => useSettings());

    act(() => {
      result.current.updateSettings({
        readOnly: false,
        defaultRowLimit: 500,
        showTrace: false,
        requireHitlApproval: false,
      });
    });

    expect(result.current.settings.readOnly).toBe(false);
    expect(result.current.settings.defaultRowLimit).toBe(500);

    act(() => {
      result.current.resetSettings();
    });

    expect(result.current.settings).toEqual(DEFAULT_SETTINGS);
    const saved = JSON.parse(localStorage.getItem("querypilot_settings") || "{}");
    expect(saved).toEqual(DEFAULT_SETTINGS);
  });
});
