import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SettingsPage from "../page";
import { AuthProvider } from "@/context/AuthContext";

describe("Workspace Settings Page (TDD Suite 4)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should display current user profile from useAuth", () => {
    render(
      <AuthProvider>
        <SettingsPage />
      </AuthProvider>
    );

    expect(
      screen.getByRole("heading", { name: /Analyst Profile/i })
    ).toBeInTheDocument();
    // Default preset persona is Alex Chen / Analyst
    expect(screen.getByDisplayValue("Alex Chen")).toBeInTheDocument();
    expect(screen.getByDisplayValue("alex.chen@enterprise.ai")).toBeInTheDocument();
    expect(screen.getByText("Analyst")).toBeInTheDocument();
  });

  it("should toggle governance safety settings and developer telemetry", () => {
    render(
      <AuthProvider>
        <SettingsPage />
      </AuthProvider>
    );

    const readOnlyToggle = screen.getByRole("switch", {
      name: /Strict Read-Only SELECT Mode/i,
    });
    expect(readOnlyToggle).toHaveAttribute("aria-checked", "true");

    fireEvent.click(readOnlyToggle);
    expect(readOnlyToggle).toHaveAttribute("aria-checked", "false");

    const hitlToggle = screen.getByRole("switch", {
      name: /Require HITL Review/i,
    });
    // Default is true in useSettings
    expect(hitlToggle).toHaveAttribute("aria-checked", "true");
    fireEvent.click(hitlToggle);
    expect(hitlToggle).toHaveAttribute("aria-checked", "false");

    const traceToggle = screen.getByRole("switch", {
      name: /Show Agent Execution Trace/i,
    });
    expect(traceToggle).toHaveAttribute("aria-checked", "true");
    fireEvent.click(traceToggle);
    expect(traceToggle).toHaveAttribute("aria-checked", "false");
  });

  it("should allow changing default row limit via dropdown", () => {
    render(
      <AuthProvider>
        <SettingsPage />
      </AuthProvider>
    );

    const rowLimitSelect = screen.getByLabelText(/Default Row Limit/i);
    expect(rowLimitSelect).toHaveValue("100");

    fireEvent.change(rowLimitSelect, { target: { value: "250" } });
    expect(rowLimitSelect).toHaveValue("250");
  });

  it("should clear cache and reset demo data when reset button is clicked", () => {
    // Populate some data first
    localStorage.setItem("querypilot_custom_key", "custom_val");

    render(
      <AuthProvider>
        <SettingsPage />
      </AuthProvider>
    );

    const resetBtn = screen.getByRole("button", {
      name: /Reset Demo Data|Clear Cache/i,
    });
    fireEvent.click(resetBtn);

    expect(
      screen.getByText(/Data & Cache Reset Successfully|Demo data reset/i)
    ).toBeInTheDocument();
  });
});
