import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageList } from "../MessageList";
import { ChatMessage } from "@/types/api";

// Mock AppContext
vi.mock("@/context/AppContext", () => ({
  useAppContext: () => ({
    showToast: vi.fn(),
  }),
}));

describe("Component 2.3: MessageList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it("1. Render rỗng khi messages là mảng rỗng", () => {
    const { container } = render(<MessageList messages={[]} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("2. Render danh sách tin nhắn của người dùng và trợ lý", () => {
    const mockMessages: ChatMessage[] = [
      {
        id: "msg-1",
        role: "user",
        content: "Phân tích doanh thu năm 1995",
        timestamp: new Date(),
      },
      {
        id: "msg-2",
        role: "assistant",
        content: "Tổng doanh thu năm 1995 là 15 tỷ VND.",
        timestamp: new Date(),
        queryResponse: {
          session_id: "s-1",
          status: "COMPLETED",
          question: "Phân tích doanh thu năm 1995",
          is_ambiguous: false,
          suggested_options: [],
          final_answer: "Tổng doanh thu năm 1995 là 15 tỷ VND.",
          execution_time_ms: 120,
          requires_hitl: false,
        },
      },
    ];

    render(<MessageList messages={mockMessages} />);

    expect(screen.getByText("Phân tích doanh thu năm 1995")).toBeInTheDocument();
    expect(
      screen.getByText("Tổng doanh thu năm 1995 là 15 tỷ VND.")
    ).toBeInTheDocument();
  });

  it("3. Tự động gọi scrollIntoView khi danh sách tin nhắn xuất hiện", () => {
    const scrollIntoViewMock = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

    const mockMessages: ChatMessage[] = [
      {
        id: "msg-1",
        role: "user",
        content: "Tin nhắn kiểm tra auto scroll",
        timestamp: new Date(),
      },
    ];

    render(<MessageList messages={mockMessages} />);

    expect(scrollIntoViewMock).toHaveBeenCalled();
  });

  it("4. Render thẻ HITL Approval Card khi requires_hitl = true", () => {
    const onApproveHitl = vi.fn();
    const mockMessages: ChatMessage[] = [
      {
        id: "msg-hitl",
        role: "assistant",
        content: "Cần phê duyệt",
        timestamp: new Date(),
        queryResponse: {
          session_id: "s-hitl",
          status: "PENDING_APPROVAL",
          question: "Quét toàn bộ lineitem",
          is_ambiguous: false,
          suggested_options: [],
          sql: "SELECT * FROM lineitem",
          estimated_cost_bytes: 1572864,
          execution_time_ms: 50,
          requires_hitl: true,
        },
      },
    ];

    render(
      <MessageList
        messages={mockMessages}
        isApprovingHitl={true}
        onApproveHitl={onApproveHitl}
      />
    );

    expect(
      screen.getByText("Cảnh báo chi phí truy vấn (HITL Required)")
    ).toBeInTheDocument();
    expect(screen.getAllByText("SELECT * FROM lineitem").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Phê duyệt & Thực thi")).toBeInTheDocument();
  });
});
