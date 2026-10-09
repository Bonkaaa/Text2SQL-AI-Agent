import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import LoginPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("SaaS Login Page & Persona Switcher (TDD Suite 4)", () => {
  beforeEach(() => {
    mockPush.mockClear();
    localStorage.clear();
  });

  it("should render split-screen branding and quick persona options", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    expect(screen.getAllByText(/QueryPilot/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Welcome to QueryPilot/i)).toBeInTheDocument();
    expect(screen.getByText(/Alex Chen/i)).toBeInTheDocument();
    expect(screen.getByText(/Sarah Data Lead/i)).toBeInTheDocument();
  });

  it("should log in with Analyst persona and redirect to workspace", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const analystBtn = screen.getByRole("button", { name: /Alex Chen/i });
    fireEvent.click(analystBtn);

    const submitBtn = screen.getByRole("button", { name: /Sign in to Workspace/i });
    fireEvent.click(submitBtn);

    expect(mockPush).toHaveBeenCalledWith("/workspace");

    const saved = JSON.parse(localStorage.getItem("querypilot_auth_user") || "{}");
    expect(saved.role).toBe("Analyst");
  });

  it("should select Admin persona, update preview, and save Admin role", () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const adminBtn = screen.getByRole("button", { name: /Sarah Data Lead/i });
    fireEvent.click(adminBtn);

    const submitBtn = screen.getByRole("button", { name: /Sign in to Workspace/i });
    fireEvent.click(submitBtn);

    expect(mockPush).toHaveBeenCalledWith("/workspace");

    const saved = JSON.parse(localStorage.getItem("querypilot_auth_user") || "{}");
    expect(saved.role).toBe("Admin");
  });
});
