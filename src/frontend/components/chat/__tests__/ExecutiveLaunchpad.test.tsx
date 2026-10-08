import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ExecutiveLaunchpad } from "../ExecutiveLaunchpad";

describe("ExecutiveLaunchpad Component (Task 1.4)", () => {
  it("should render role-aware greeting and 4 curated TPC-DS business question starters", () => {
    const handleSelectPrompt = vi.fn();

    render(
      <ExecutiveLaunchpad
        currentRole="Analyst"
        onSelectPrompt={handleSelectPrompt}
      />
    );

    // Should render headline
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /Khám phá số liệu kho dữ liệu/i
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /TPC-DS Enterprise/i
    );

    // Check for 4 business domains/questions via headings
    expect(
      screen.getByRole("heading", { name: /Doanh thu thuần Đa kênh/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Tỷ lệ Hoàn hàng/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Tồn kho & Kho hàng/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Hiệu quả Khuyến mãi/i })
    ).toBeInTheDocument();
  });

  it("should trigger onSelectPrompt when clicking on a starter card", () => {
    const handleSelectPrompt = vi.fn();

    render(
      <ExecutiveLaunchpad
        currentRole="Analyst"
        onSelectPrompt={handleSelectPrompt}
      />
    );

    // Click on the first card (Doanh thu thuần Đa kênh)
    const cardTitle = screen.getByRole("heading", {
      name: /Doanh thu thuần Đa kênh/i,
    });
    const card = cardTitle.closest("button");
    expect(card).not.toBeNull();
    if (card) {
      fireEvent.click(card);
      expect(handleSelectPrompt).toHaveBeenCalledTimes(1);
      expect(handleSelectPrompt).toHaveBeenCalledWith(
        expect.stringContaining("store_sales")
      );
    }
  });
});
