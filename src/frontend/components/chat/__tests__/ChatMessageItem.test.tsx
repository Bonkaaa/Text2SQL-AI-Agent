import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { ChatMessageItem, MessageItem } from "../ChatMessageItem";
import { ChatMessage, QueryResponse } from "@/types/api";

// Mock AppContext
vi.mock("@/context/AppContext", () => ({
  useAppContext: () => ({
    showToast: vi.fn(),
    currentRole: "Admin",
  }),
  useOptionalAppContext: () => ({
    showToast: vi.fn(),
    currentRole: "Admin",
  }),
}));

describe("Component 5.3: ChatMessageItem (Message Item Composer)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render tin nhắn của người dùng (User Message) căn phải kèm nội dung và thời gian", () => {
    const userMessage: ChatMessage = {
      id: "msg-user-1",
      role: "user",
      content: "Doanh thu năm 1995 theo từng khu vực địa lý?",
      timestamp: new Date(2026, 8, 22, 10, 30),
    };

    render(<ChatMessageItem message={userMessage} />);

    expect(
      screen.getByText("Doanh thu năm 1995 theo từng khu vực địa lý?")
    ).toBeInTheDocument();
    // Kiểm tra timestamp có hiển thị (theo định dạng giờ phút vi-VN)
    expect(screen.getByText(/10:30/)).toBeInTheDocument();
  });

  it("2. Render trạng thái đang xử lý (Loading State) với ReasoningTimeline", () => {
    const loadingMessage: ChatMessage = {
      id: "msg-asst-loading",
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isLoading: true,
    };

    render(<ChatMessageItem message={loadingMessage} />);

    // Kiểm tra ReasoningTimeline được hiển thị ở trạng thái loading
    expect(screen.getByText(/Quy trình suy luận/i)).toBeInTheDocument();
    expect(screen.getByText(/Schema & Categorical Retriever/i)).toBeInTheDocument();
  });

  it("3. Khi trạng thái là CLARIFICATION_REQUIRED, chỉ render ClarificationCard và gọi callback onSelectOption", () => {
    const mockOnSelectOption = vi.fn();
    const clarificationResponse: QueryResponse = {
      session_id: "sess-clarify",
      status: "CLARIFICATION_REQUIRED",
      question: "Doanh thu",
      is_ambiguous: true,
      clarification_question: "Bạn muốn xem doanh thu theo chỉ số nào?",
      suggested_options: ["Doanh thu thuần", "Tổng doanh số", "Doanh thu theo vùng"],
      requires_hitl: false,
      execution_time_ms: 120,
    };

    const message: ChatMessage = {
      id: "msg-clarify",
      role: "assistant",
      content: "Cần làm rõ ý định",
      timestamp: new Date(),
      status: "CLARIFICATION_REQUIRED",
      queryResponse: clarificationResponse,
    };

    render(
      <ChatMessageItem
        message={message}
        onSelectOption={mockOnSelectOption}
      />
    );

    // Kiểm tra render ClarificationCard
    expect(screen.getByText(/Cần làm rõ ý định câu hỏi/i)).toBeInTheDocument();
    expect(
      screen.getByText("Bạn muốn xem doanh thu theo chỉ số nào?")
    ).toBeInTheDocument();
    expect(screen.getByText(/Doanh thu thuần/i)).toBeInTheDocument();

    // Không render InsightCard khi đang chờ làm rõ
    expect(screen.queryByText(/Nhận định kinh doanh/i)).not.toBeInTheDocument();

    // Click vào chip tùy chọn
    const chip = screen.getByText(/Doanh thu thuần/i);
    fireEvent.click(chip);
    expect(mockOnSelectOption).toHaveBeenCalledWith("Doanh thu thuần");
  });

  it("4. Khi trạng thái là PENDING_APPROVAL, render HITLApprovalCard và không hiển thị bảng kết quả", () => {
    const mockOnApproveHitl = vi.fn();
    const hitlResponse: QueryResponse = {
      session_id: "sess-hitl",
      status: "PENDING_APPROVAL",
      question: "Quét toàn bộ bảng lineitem",
      is_ambiguous: false,
      suggested_options: [],
      sql: "SELECT * FROM lineitem;",
      estimated_cost_bytes: 157286400, // 150 MB
      requires_hitl: true,
      execution_time_ms: 85,
    };

    const message: ChatMessage = {
      id: "msg-hitl",
      role: "assistant",
      content: "Chờ phê duyệt",
      timestamp: new Date(),
      status: "PENDING_APPROVAL",
      queryResponse: hitlResponse,
    };

    render(
      <ChatMessageItem
        message={message}
        onApproveHitl={mockOnApproveHitl}
      />
    );

    // Kiểm tra render HITLApprovalCard
    expect(screen.getByText(/Cảnh báo chi phí truy vấn/i)).toBeInTheDocument();
    expect(screen.getByText(/150.0 MB/i)).toBeInTheDocument();
    expect(screen.getByText(/SELECT \* FROM lineitem;/i)).toBeInTheDocument();

    // Kiểm tra có nút Phê duyệt
    const approveBtn = screen.getByRole("button", { name: /Phê duyệt & Thực thi/i });
    expect(approveBtn).toBeInTheDocument();
    fireEvent.click(approveBtn);
    expect(mockOnApproveHitl).toHaveBeenCalledWith(true);

    // Không hiển thị bảng kết quả dữ liệu
    expect(screen.queryByText(/Bảng kết quả/i)).not.toBeInTheDocument();
  });

  it("5. Khi trạng thái là ERROR, render ErrorFeedbackCard kèm thông báo lỗi và gọi onRetry", () => {
    const mockOnRetry = vi.fn();
    const errorResponse: QueryResponse = {
      session_id: "sess-err",
      status: "ERROR",
      question: "Truy vấn lỗi cú pháp",
      is_ambiguous: false,
      suggested_options: [],
      error: "Không thể thực thi truy vấn do lỗi cú pháp SQL",
      error_type: "RBAC_VIOLATION",
      retry_count: 3,
      requires_hitl: false,
      execution_time_ms: 250,
    };

    const message: ChatMessage = {
      id: "msg-err",
      role: "assistant",
      content: "Lỗi thực thi",
      timestamp: new Date(),
      status: "ERROR",
      queryResponse: errorResponse,
    };

    render(<ChatMessageItem message={message} onRetry={mockOnRetry} />);

    // Kiểm tra render ErrorFeedbackCard
    expect(screen.getByText(/Không thể thực thi truy vấn/i)).toBeInTheDocument();
    expect(screen.getByText(/Chính sách bảo mật \(RBAC\)/i)).toBeInTheDocument();

    // Click nút Thử lại
    const retryBtn = screen.getByRole("button", { name: /Thử lại/i });
    fireEvent.click(retryBtn);
    expect(mockOnRetry).toHaveBeenCalledTimes(1);
  });

  it("6. Khi trạng thái là COMPLETED, render InsightCard và các tab Biểu đồ, Bảng dữ liệu, Truy vấn SQL", () => {
    const completedResponse: QueryResponse = {
      session_id: "sess-completed",
      status: "COMPLETED",
      question: "Doanh thu 5 khu vực",
      is_ambiguous: false,
      suggested_options: [],
      final_answer: "Khu vực **ASIA** dẫn đầu với doanh thu vượt trội.",
      sql: "SELECT r_name, SUM(o_totalprice) AS total FROM orders JOIN customer ON c_custkey = o_custkey GROUP BY r_name;",
      columns: ["r_name", "total"],
      data: [
        { r_name: "ASIA", total: 50000000 },
        { r_name: "EUROPE", total: 42000000 },
      ],
      recharts_config: {
        chart_type: "bar",
        title: "Doanh thu theo khu vực",
        x_key: "r_name",
        y_keys: ["total"],
      },
      requires_hitl: false,
      execution_time_ms: 180,
    };

    const message: ChatMessage = {
      id: "msg-completed",
      role: "assistant",
      content: completedResponse.final_answer!,
      timestamp: new Date(),
      status: "COMPLETED",
      queryResponse: completedResponse,
    };

    // Kiểm tra cả alias MessageItem
    render(<MessageItem message={message} />);

    // 1. Kiểm tra InsightCard
    expect(screen.getByText(/Nhận định kinh doanh/i)).toBeInTheDocument();
    expect(screen.getByText(/ASIA/i)).toBeInTheDocument();

    // 2. Kiểm tra các Tab chuyển đổi
    expect(screen.getByRole("button", { name: /^Biểu đồ$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Bảng kết quả$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Truy vấn SQL$/i })).toBeInTheDocument();

    // Mặc định tab Biểu đồ hiển thị khi có recharts_config
    expect(screen.getByText(/Doanh thu theo khu vực/i)).toBeInTheDocument();

    // Bấm chuyển sang tab Bảng kết quả
    const tableTab = screen.getByRole("button", { name: /^Bảng kết quả$/i });
    fireEvent.click(tableTab);
    expect(screen.getByText("EUROPE")).toBeInTheDocument();

    // Bấm chuyển sang tab Truy vấn SQL
    const sqlTab = screen.getByRole("button", { name: /^Truy vấn SQL$/i });
    fireEvent.click(sqlTab);
    expect(screen.getByText(/Truy vấn SQL đã thực thi/i)).toBeInTheDocument();
  });
});
