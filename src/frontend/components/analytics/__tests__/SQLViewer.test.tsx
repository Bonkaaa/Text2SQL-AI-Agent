import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { SQLViewer } from "../SQLViewer";

describe("Component 4.4: SQLViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const sampleSql = `SELECT 
  r.r_name, 
  SUM(l.l_extendedprice * (1 - l.l_discount)) AS revenue 
FROM region r 
JOIN nation n ON r.r_regionkey = n.n_regionkey 
GROUP BY r.r_name 
ORDER BY revenue DESC;`;

  it("1. Render câu lệnh SQL và tiêu đề hiển thị chuẩn xác", () => {
    render(<SQLViewer sql={sampleSql} />);

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText("Truy vấn SQL đã thực thi")).toBeInTheDocument();
    expect(screen.getByText(/SELECT/)).toBeInTheDocument();
    expect(screen.getByText(/ORDER BY revenue DESC;/)).toBeInTheDocument();
  });

  it("2. Hiển thị cột số dòng (Line Numbers gutter: 1, 2, 3...)", () => {
    render(<SQLViewer sql={sampleSql} showLineNumbers={true} />);

    // sampleSql có 7 dòng
    const lineNumbers = screen.getByTestId("sql-line-numbers");
    expect(lineNumbers).toBeInTheDocument();
    expect(lineNumbers).toHaveTextContent("1");
    expect(lineNumbers).toHaveTextContent("7");
  });

  it("3. Hiển thị badge thống kê số dòng code và badge an toàn AST Verified", () => {
    render(<SQLViewer sql={sampleSql} />);

    expect(screen.getByText("7 dòng")).toBeInTheDocument();
    expect(screen.getByText("AST Verified")).toBeInTheDocument();
  });

  it("4. Sao chép câu lệnh SQL vào clipboard khi bấm nút [Sao chép] và hiển thị 'Đã chép'", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    const onCopyMock = vi.fn();

    render(<SQLViewer sql={sampleSql} onCopy={onCopyMock} />);

    const copyBtn = screen.getByRole("button", { name: /Sao chép SQL/i });
    expect(copyBtn).toBeInTheDocument();

    fireEvent.click(copyBtn);

    expect(await screen.findByText(/Đã chép/i)).toBeInTheDocument();
    expect(writeTextMock).toHaveBeenCalledWith(sampleSql);
    expect(onCopyMock).toHaveBeenCalledTimes(1);
  });

  it("5. Bấm nút toggle bọc dòng chuyển đổi thuộc tính bọc dòng", () => {
    render(<SQLViewer sql={sampleSql} allowWrapToggle={true} />);

    const wrapBtn = screen.getByRole("button", { name: /Bọc dòng/i });
    expect(wrapBtn).toBeInTheDocument();
    expect(wrapBtn).toHaveAttribute("aria-pressed", "false");

    // Click bật wrap
    fireEvent.click(wrapBtn);
    expect(wrapBtn).toHaveAttribute("aria-pressed", "true");

    // Click tắt wrap
    fireEvent.click(wrapBtn);
    expect(wrapBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("6. Xử lý an toàn khi SQL rỗng không làm vỡ giao diện", () => {
    render(<SQLViewer sql="" />);

    expect(screen.getByText("Không có câu lệnh SQL")).toBeInTheDocument();
  });
});
