import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TableMetadataModal } from "../../modal/TableMetadataModal";

describe("TPC-DS Metadata Inspection Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should open TableMetadataModal and render table details with prompt action", () => {
    const handleSelectPrompt = vi.fn();
    const handleClose = vi.fn();

    render(
      <TableMetadataModal
        isOpen={true}
        tableName="store_sales"
        onClose={handleClose}
        onSelectForPrompt={handleSelectPrompt}
      />
    );

    // Modal xuất hiện
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "store_sales" })).toBeInTheDocument();
    expect(screen.getByText(/Giao dịch bán lẻ trực tiếp/i)).toBeInTheDocument();

    // Bấm nút sử dụng bảng này trong prompt
    const useBtn = screen.getByRole("button", { name: /Sử dụng bảng này/i });
    fireEvent.click(useBtn);

    expect(handleSelectPrompt).toHaveBeenCalledWith("store_sales");
  });
});

