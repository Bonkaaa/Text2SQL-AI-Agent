import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatMessageItem } from "../components/chat/ChatMessageItem";
import { ChatMessage } from "../types/api";

describe("Anti-AI-Cliche & TPC-DS Compliance (Task 1.2)", () => {
  it("should NOT render hardcoded 'AST Verified' badge when telemetry does not confirm it", () => {
    const mockMessage: ChatMessage = {
      id: "msg-1",
      role: "assistant",
      content: "Doanh thu năm 2003 đạt 12.5 triệu USD.",
      timestamp: new Date(),
      queryResponse: {
        session_id: "test-session",
        status: "COMPLETED",
        question: "Doanh thu năm 2003?",
        final_answer: "Doanh thu năm 2003 đạt 12.5 triệu USD.",
        is_ambiguous: false,
        suggested_options: [],
        execution_time_ms: 120,
        requires_hitl: false,
        // No explicit ast_verified flag
      },
    };

    render(<ChatMessageItem message={mockMessage} />);

    // Should NOT have hardcoded 'AST Verified' badge without proof
    expect(screen.queryByText("AST Verified")).toBeNull();
  });

  it("should reference TPC-DS instead of legacy TPC-H in assistant header", () => {
    const mockMessage: ChatMessage = {
      id: "msg-2",
      role: "assistant",
      content: "Kết quả truy vấn.",
      timestamp: new Date(),
      queryResponse: {
        session_id: "test-session",
        status: "COMPLETED",
        question: "Test question",
        is_ambiguous: false,
        suggested_options: [],
        execution_time_ms: 50,
        requires_hitl: false,
      },
    };

    render(<ChatMessageItem message={mockMessage} />);

    // Must NOT contain 'TPC-H'
    expect(screen.queryByText(/TPC-H/i)).toBeNull();
    // Must reference TPC-DS
    expect(screen.getByText(/TPC-DS/i)).toBeInTheDocument();
  });
});
