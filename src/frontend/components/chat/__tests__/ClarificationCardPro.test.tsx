import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { ClarificationCard } from "../ClarificationCard";

describe("ClarificationCard Pro (Interactive Decision Cards & Keyboard Shortcuts)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockOptions = [
    "Doanh thu thuần: Đã trừ khuyến mãi và giảm giá",
    "Tổng giá niêm yết: Chưa trừ chiết khấu",
    "Doanh số theo khu vực địa lý",
  ];

  it("1. should render decision cards with shortcut badges (A, B, C)", () => {
    const onSelect = vi.fn();
    render(
      <ClarificationCard
        question="Bạn muốn tính doanh thu theo thước đo nào?"
        options={mockOptions}
        onSelectOption={onSelect}
      />
    );

    expect(screen.getByText("Bạn muốn tính doanh thu theo thước đo nào?")).toBeInTheDocument();
    expect(screen.getAllByText("A")[0]).toBeInTheDocument();
    expect(screen.getAllByText("B")[0]).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
    expect(screen.getByText(/Doanh thu thuần/)).toBeInTheDocument();
  });

  it("2. should trigger onSelectOption when clicking a decision card", () => {
    const onSelect = vi.fn();
    render(
      <ClarificationCard
        question="Chọn thước đo"
        options={mockOptions}
        onSelectOption={onSelect}
      />
    );

    const cardA = screen.getByRole("button", { name: /Doanh thu thuần/i });
    fireEvent.click(cardA);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(mockOptions[0]);
  });

  it("3. should trigger onSelectOption when pressing keyboard shortcut A or 1", () => {
    const onSelect = vi.fn();
    render(
      <ClarificationCard
        question="Chọn thước đo"
        options={mockOptions}
        onSelectOption={onSelect}
      />
    );

    const region = screen.getByRole("region");
    // Bấm phím 'a' hoặc 'A'
    fireEvent.keyDown(region, { key: "a" });
    expect(onSelect).toHaveBeenCalledWith(mockOptions[0]);

    // Bấm phím '2' -> phương án B
    fireEvent.keyDown(region, { key: "2" });
    expect(onSelect).toHaveBeenCalledWith(mockOptions[1]);
  });

  it("4. should not trigger selection when disabled is true", () => {
    const onSelect = vi.fn();
    render(
      <ClarificationCard
        question="Chọn thước đo"
        options={mockOptions}
        onSelectOption={onSelect}
        disabled={true}
      />
    );

    const cardA = screen.getByRole("button", { name: /Doanh thu thuần/i });
    fireEvent.click(cardA);
    expect(onSelect).not.toHaveBeenCalled();

    const region = screen.getByRole("region");
    fireEvent.keyDown(region, { key: "a" });
    expect(onSelect).not.toHaveBeenCalled();
  });
});
