import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { InsightCard } from "../InsightCard";

describe("Component 4.1: InsightCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render đúng tiêu đề mặc định, phụ đề và nội dung nhận định kinh doanh", () => {
    render(
      <InsightCard insightText="Doanh thu khu vực ASIA đạt mức tăng trưởng cao nhất với 250 tỷ VNĐ." />
    );

    expect(screen.getByRole("region")).toBeInTheDocument();
    expect(screen.getByText("Nhận định kinh doanh")).toBeInTheDocument();
    expect(
      screen.getByText("Tổng hợp từ dữ liệu TPC-H")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Doanh thu khu vực ASIA đạt mức tăng trưởng cao nhất/i)
    ).toBeInTheDocument();
  });

  it("2. Hỗ trợ tiêu đề và phụ đề tùy biến khi được cung cấp qua props", () => {
    render(
      <InsightCard
        insightText="Tỷ lệ đơn hàng giao trễ qua đường AIR chiếm 12%."
        title="Tóm tắt phân tích TPC-H"
        subtitle="Dữ liệu vận chuyển năm 1995"
      />
    );

    expect(screen.getByText("Tóm tắt phân tích TPC-H")).toBeInTheDocument();
    expect(screen.getByText("Dữ liệu vận chuyển năm 1995")).toBeInTheDocument();
  });

  it("3. Định dạng markdown in đậm **từ khóa** thành thẻ strong nổi bật", () => {
    render(
      <InsightCard
        insightText="Doanh thu tăng trưởng **15.4%** so với cùng kỳ năm trước."
      />
    );

    const boldElement = screen.getByText("15.4%");
    expect(boldElement.tagName.toLowerCase()).toBe("strong");
    expect(boldElement).toHaveClass("font-semibold");
  });

  it("4. Hỗ trợ hiển thị danh sách gạch đầu dòng (bullet points)", () => {
    const listText = `Tổng hợp các phát hiện chính:
- Top 1 khách hàng chi tiêu lớn nhất là Customer#000000001
- Phân khúc BUILDING chiếm 35% tổng doanh số
- Khu vực EUROPE có chiết khấu trung bình thấp nhất`;

    render(<InsightCard insightText={listText} />);

    expect(
      screen.getByText(/Customer#000000001/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Phân khúc BUILDING chiếm 35%/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Khu vực EUROPE có chiết khấu trung bình/i)
    ).toBeInTheDocument();
  });

  it("5. Hiển thị badge thời gian tổng hợp định dạng giây (s)", () => {
    render(
      <InsightCard
        insightText="Phân tích hoàn tất thành công."
        executionTimeMs={185}
      />
    );

    expect(screen.getByText("0.19s")).toBeInTheDocument();
  });

  it("6. Sao chép nội dung vào clipboard khi bấm nút [Sao chép] và hiển thị phản hồi 'Đã chép'", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    const onCopyMock = vi.fn();

    render(
      <InsightCard
        insightText="Doanh thu thuần quý 3 đạt 4.2 triệu USD."
        onCopy={onCopyMock}
      />
    );

    const copyBtn = screen.getByRole("button", { name: /Sao chép/i });
    expect(copyBtn).toBeInTheDocument();

    fireEvent.click(copyBtn);

    expect(await screen.findByText(/Đã chép/i)).toBeInTheDocument();
    expect(writeTextMock).toHaveBeenCalledWith(
      "Doanh thu thuần quý 3 đạt 4.2 triệu USD."
    );
    expect(onCopyMock).toHaveBeenCalledTimes(1);
  });

  it("7. Compile bảng Markdown thành table HTML với th, td đẹp mắt", () => {
    const tableMarkdown = `
### 📊 Bảng dữ liệu chi tiết
| Mã KH | Tên khách hàng | Doanh số |
|:--- | :--- | :--- |
| 101 | Khách hàng VIP A | 500,000 |
| 102 | Khách hàng VIP B | 300,000 |
`;

    render(<InsightCard insightText={tableMarkdown} />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Tên khách hàng")).toBeInTheDocument();
    expect(screen.getByText("Khách hàng VIP A")).toBeInTheDocument();
    expect(screen.getByText("500,000")).toBeInTheDocument();
  });

  it("8. Tự động phát hiện cấu hình Recharts JSON và chuyển đổi thành DynamicChart trực quan", () => {
    const markdownWithChart = `
| Tên KH (\`c_name\`) | Tổng chi tiêu (\`total_spent\`) |
|:--- | :--- |
| Customer A | 1000 |
| Customer B | 2000 |

\`\`\`json
{
  "chart_type": "bar",
  "recharts_config": {
    "title": "Top khách hàng chi tiêu",
    "x_key": "c_name",
    "y_keys": ["total_spent"]
  }
}
\`\`\`
`;

    render(<InsightCard insightText={markdownWithChart} />);

    // Kiểm tra render component biểu đồ
    expect(screen.getByText(/Biểu đồ trực quan \(BAR\)/i)).toBeInTheDocument();
    expect(screen.getByText("Top khách hàng chi tiêu")).toBeInTheDocument();
  });
});
