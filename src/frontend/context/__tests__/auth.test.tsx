import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent, renderHook, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "../AuthContext";

describe("Auth & RBAC Context (TDD Suite 1)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should initialize with default Analyst persona if no stored session", () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    expect(result.current.user.role).toBe("Analyst");
    expect(result.current.user.name).toBe("Alex Chen");
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("should switch persona to Admin with adminToken", () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    act(() => {
      result.current.login("admin");
    });

    expect(result.current.user.role).toBe("Admin");
    expect(result.current.user.name).toContain("Data Lead");
    expect(result.current.user.adminToken).toBeDefined();

    // Check localStorage persistence
    const saved = JSON.parse(localStorage.getItem("querypilot_auth_user") || "{}");
    expect(saved.role).toBe("Admin");
  });

  it("should support switching roles directly", () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    act(() => {
      result.current.switchRole("Business_User");
    });

    expect(result.current.user.role).toBe("Business_User");
  });

  it("should handle logout and restore guest/unauthenticated state", () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user.role).toBe("Analyst");
    expect(localStorage.getItem("querypilot_auth_user")).toBeNull();
  });
});
