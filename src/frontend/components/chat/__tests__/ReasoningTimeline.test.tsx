import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ReasoningTimeline,
  DEFAULT_REASONING_STEPS,
} from "../ReasoningTimeline";

describe("Component 2.4: ReasoningTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render tiêu đề và nút Accordion mở/thu gọn quy trình suy luận", () => {
    render(<ReasoningTimeline />);

    expect(
      screen.getByText(/Quy trình suy luận \(DeepAgents CoT\)/i)
    ).toBeInTheDocument();
    const toggleBtn = screen.getByRole("button", {
      name: /Quy trình suy luận \(DeepAgents CoT\)/i,
    });
    expect(toggleBtn).toBeInTheDocument();
  });

  it("2. Xuất khẩu danh sách 4 bước chuẩn DEFAULT_REASONING_STEPS của DeepAgents", () => {
    expect(DEFAULT_REASONING_STEPS).toBeDefined();
    expect(DEFAULT_REASONING_STEPS.length).toBe(4);

    expect(DEFAULT_REASONING_STEPS[0].title).toMatch(/Làm rõ ý định/i);
    expect(DEFAULT_REASONING_STEPS[1].title).toMatch(/Schema/i);
    expect(DEFAULT_REASONING_STEPS[2].title).toMatch(/SQL Generator/i);
    expect(DEFAULT_REASONING_STEPS[3].title).toMatch(/Control Guard|Synthesizer/i);
  });

  it("3. Mặc định thu gọn và click toggle để mở rộng hiển thị đầy đủ 4 bước", () => {
    render(<ReasoningTimeline defaultExpanded={false} />);

    // Ban đầu thu gọn, không thấy chi tiết các bước
    expect(screen.queryByText(/1\. Làm rõ ý định:/i)).not.toBeInTheDocument();

    const toggleBtn = screen.getByRole("button", {
      name: /Quy trình suy luận \(DeepAgents CoT\)/i,
    });
    fireEvent.click(toggleBtn);

    // Mở rộng ra thấy đầy đủ 4 bước
    expect(screen.getByText(/1\. Làm rõ ý định:/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Schema & Categorical Retriever:/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. SQL Generator:/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. LangGraph Control Guard & Synthesizer:/i)).toBeInTheDocument();
  });

  it("4. Hiển thị badge thời gian thực thi định dạng giây (s) khi được cung cấp", () => {
    render(<ReasoningTimeline executionTimeMs={345} />);

    expect(screen.getByText(/0\.35s/i)).toBeInTheDocument();
  });

  it("5. Khi isLoading = true, tự động mở rộng và hiển thị trạng thái đang xử lý", () => {
    render(<ReasoningTimeline isLoading={true} currentStep={2} />);

    // Khi loading thì timeline tự mở để người dùng theo dõi tiến trình
    expect(screen.getByText(/2\. Schema & Categorical Retriever:/i)).toBeInTheDocument();
    expect(screen.getByTestId("step-active-2")).toBeInTheDocument();
    expect(screen.getByTestId("step-done-1")).toBeInTheDocument();
  });

  it("6. Hỗ trợ prop defaultExpanded = true", () => {
    render(<ReasoningTimeline defaultExpanded={true} />);

    expect(screen.getByText(/1\. Làm rõ ý định:/i)).toBeInTheDocument();
  });
});
