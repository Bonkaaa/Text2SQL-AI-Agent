import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AppProvider } from "@/context/AppContext";
import { InspectorDrawer } from "../InspectorDrawer";
import { Sidebar } from "../Sidebar";

describe("3-Pane Adaptive Workspace Layout (Task 1.3)", () => {
  it("should render Sidebar with Session History and New Chat action", () => {
    const handleSelectPrompt = vi.fn();
    const handleReset = vi.fn();

    render(
      <AppProvider>
        <Sidebar
          onSelectPrompt={handleSelectPrompt}
          onResetToHome={handleReset}
        />
      </AppProvider>
    );

    // Sidebar should present Session History and actions
    expect(screen.getByText("Lịch sử phân tích")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Phân tích mới/i })).toBeInTheDocument();
    expect(screen.getByText("Trang làm việc")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Tìm kiếm session\/bảng\.\.\./i)
    ).toBeInTheDocument();
  });

  it("should render InspectorDrawer with Telemetry, SQL Viewer and Governance panels", () => {
    const handleClose = vi.fn();

    render(
      <InspectorDrawer
        isOpen={true}
        onClose={handleClose}
        executionTimeMs={154}
        scannedBytes={48200000}
        sql="SELECT s_store_name, SUM(ss_net_paid) FROM store_sales JOIN store ON ss_store_sk = s_store_sk GROUP BY 1;"
        astVerified={true}
        role="Analyst"
      />
    );

    // Must display Inspector title
    expect(screen.getByText(/Context & Governance Inspector/i)).toBeInTheDocument();

    // Telemetry
    expect(screen.getByText(/Thời gian phân tích/i)).toBeInTheDocument();
    expect(screen.getByText(/154ms/i)).toBeInTheDocument();

    // Security & AST clearance
    expect(screen.getByText(/AST Sanitizer/i)).toBeInTheDocument();
    expect(screen.getByText(/SELECT-ONLY \(Hợp lệ\)/i)).toBeInTheDocument();

    // SQL Code section (check multiple matches)
    expect(screen.getAllByText(/store_sales/i).length).toBeGreaterThanOrEqual(1);
  });

  it("should trigger onClose when clicking close button in InspectorDrawer", () => {
    const handleClose = vi.fn();

    render(
      <InspectorDrawer
        isOpen={true}
        onClose={handleClose}
      />
    );

    const closeButton = screen.getByRole("button", { name: /đóng inspector/i });
    fireEvent.click(closeButton);
    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
