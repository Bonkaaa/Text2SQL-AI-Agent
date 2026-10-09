import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryComposer } from "../QueryComposer";
import { ClarificationChips } from "../ClarificationChips";
import { HITLApprovalBanner } from "../HITLApprovalBanner";
import { MessageItem } from "../MessageItem";
import { WorkspaceMessage } from "@/hooks/useWorkspace";

describe("Conversation Panel Components (TDD Suite 3)", () => {
  describe("QueryComposer", () => {
    it("should call onSubmit on Enter without Shift", () => {
      const handleSubmit = vi.fn();
      render(<QueryComposer onSubmit={handleSubmit} isLoading={false} />);

      const textarea = screen.getByPlaceholderText(/Ask a question about your data/i);
      fireEvent.change(textarea, { target: { value: "Show store sales 2003" } });
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      expect(handleSubmit).toHaveBeenCalledWith("Show store sales 2003");
    });

    it("should not call onSubmit on Shift+Enter", () => {
      const handleSubmit = vi.fn();
      render(<QueryComposer onSubmit={handleSubmit} isLoading={false} />);

      const textarea = screen.getByPlaceholderText(/Ask a question about your data/i);
      fireEvent.change(textarea, { target: { value: "Line 1" } });
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

      expect(handleSubmit).not.toHaveBeenCalled();
    });

    it("should disable button when loading", () => {
      render(<QueryComposer onSubmit={vi.fn()} isLoading={true} />);
      const button = screen.getByRole("button", { name: /send query/i });
      expect(button).toBeDisabled();
    });
  });

  describe("ClarificationChips", () => {
    it("should render question and clickable options", () => {
      const handleSelect = vi.fn();
      render(
        <ClarificationChips
          question="Bạn muốn lọc theo năm nào?"
          options={["Năm 2002", "Năm 2003"]}
          onSelectOption={handleSelect}
        />
      );

      expect(screen.getByText("Bạn muốn lọc theo năm nào?")).toBeInTheDocument();
      const optionBtn = screen.getByText("Năm 2003");
      fireEvent.click(optionBtn);

      expect(handleSelect).toHaveBeenCalledWith("Năm 2003");
    });
  });

  describe("HITLApprovalBanner", () => {
    it("should display estimated cost and trigger onApprove", () => {
      const handleApprove = vi.fn();
      render(
        <HITLApprovalBanner
          estimatedCostBytes={52428800}
          sql="SELECT * FROM store_sales;"
          onApprove={handleApprove}
          isApproving={false}
        />
      );

      expect(screen.getByText(/50.0 MB/i)).toBeInTheDocument();
      const approveBtn = screen.getByRole("button", { name: /Phê duyệt/i });
      fireEvent.click(approveBtn);

      expect(handleApprove).toHaveBeenCalledWith(true);
    });
  });

  describe("MessageItem", () => {
    it("should render user message", () => {
      const msg: WorkspaceMessage = {
        id: "1",
        role: "user",
        content: "Top 10 products",
        timestamp: "10:00 AM",
      };
      render(<MessageItem message={msg} />);
      expect(screen.getByText("Top 10 products")).toBeInTheDocument();
    });

    it("should render assistant message with execution time badge", () => {
      const msg: WorkspaceMessage = {
        id: "2",
        role: "assistant",
        content: "Result summarized.",
        timestamp: "10:01 AM",
        queryResponse: {
          session_id: "sess_1",
          status: "COMPLETED",
          question: "Top 10 products",
          execution_time_ms: 1250,
        },
      };
      render(<MessageItem message={msg} />);
      expect(screen.getByText("Result summarized.")).toBeInTheDocument();
      expect(screen.getByText("1.25s total")).toBeInTheDocument();
    });
  });
});
