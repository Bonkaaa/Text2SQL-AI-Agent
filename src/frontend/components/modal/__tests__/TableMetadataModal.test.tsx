import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { TableMetadataModal } from "../TableMetadataModal";

describe("TableMetadataModal component (TPC-DS 24 Tables Inspector)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. should render table metadata when isOpen is true and tableName is provided", () => {
    render(
      <TableMetadataModal
        isOpen={true}
        tableName="store_sales"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "store_sales" })).toBeInTheDocument();
    expect(screen.getByText(/Giao dịch bán lẻ trực tiếp/i)).toBeInTheDocument();
    expect(screen.getAllByText("ss_sold_date_sk").length).toBeGreaterThanOrEqual(1);
  });

  it("2. should display PII indicators for sensitive customer columns", () => {
    render(
      <TableMetadataModal
        isOpen={true}
        tableName="customer"
        onClose={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: "customer" })).toBeInTheDocument();
    expect(screen.getAllByText(/PII/i).length).toBeGreaterThanOrEqual(1);
  });

  it("3. should call onSelectForPrompt when clicking 'Use table in prompt' button", () => {
    const onSelect = vi.fn();
    render(
      <TableMetadataModal
        isOpen={true}
        tableName="web_sales"
        onClose={vi.fn()}
        onSelectForPrompt={onSelect}
      />
    );

    const useBtn = screen.getByRole("button", { name: /Sử dụng bảng này/i });
    expect(useBtn).toBeInTheDocument();

    fireEvent.click(useBtn);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("web_sales");
  });

  it("4. should call onClose when clicking close button or pressing Escape", () => {
    const onClose = vi.fn();
    render(
      <TableMetadataModal
        isOpen={true}
        tableName="store_sales"
        onClose={onClose}
      />
    );

    const closeBtn = screen.getByLabelText(/Đóng modal/i);
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);

    // Bấm Escape
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("5. should return null when isOpen is false", () => {
    const { container } = render(
      <TableMetadataModal
        isOpen={false}
        tableName="store_sales"
        onClose={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
