import { describe, it, expect } from "vitest";
import {
  parseMarkdownTable,
  extractRechartsConfig,
  alignDataWithConfig,
  extractChartAndDataFromMarkdown,
  inferRechartsConfig,
  cleanInsightMarkdown,
  parseNumericValue,
} from "../markdownChartParser";

describe("Utility: markdownChartParser", () => {
  const sampleMarkdown = `
Dưới đây là kết quả phân tích Top 5 khách hàng:

### 📊 Bảng dữ liệu chi tiết
| Mã KH (\`c_custkey\`) | Tên khách hàng (\`c_name\`) | Tổng chi tiêu (Net Revenue) |
|:--- | :--- | :--- |
| 349 | Customer#000000349 | 14,383,665.02 |
| 814 | Customer#00000814 | 10,875,191.51 |
| 1120 | Customer#000001120 | 10,640,403.94 |

---
### 📈 Cấu hình biểu đồ đề xuất (Recharts JSON)
\`\`\`json
{
  "chart_type": "bar",
  "recharts_config": {
    "title": "Top 5 khách hàng có tổng chi tiêu lớn nhất năm 1995",
    "x_key": "c_name",
    "y_keys": ["total_spent"],
    "series_labels": {
      "total_spent": "Tổng chi tiêu"
    }
  }
}
\`\`\`
`;

  it("1. parseMarkdownTable bóc tách chính xác các dòng và chuyển đổi số", () => {
    const { data, columns } = parseMarkdownTable(sampleMarkdown);

    expect(data.length).toBe(3);
    expect(columns).toContain("c_custkey");
    expect(columns).toContain("c_name");

    expect(data[0].c_name).toBe("Customer#000000349");
    expect(data[0].c_custkey).toBe(349);
    // Số tiền phân tách dấu phẩy được chuyển thành number
    const numericVal = Object.values(data[0]).find(
      (v) => typeof v === "number" && v > 10_000_000
    );
    expect(numericVal).toBeCloseTo(14383665.02);
  });

  it("2. parseNumericValue xử lý chính xác tiền tệ $, VND và chú thích phụ", () => {
    expect(parseNumericValue("$7,820,490.52")).toBeCloseTo(7820490.52);
    expect(parseNumericValue("$ 14,383,665.02")).toBeCloseTo(14383665.02);
    expect(parseNumericValue("89,806.08 (Lưu ý: năm 2003)")).toBeCloseTo(89806.08);
    expect(parseNumericValue("123,456.78 VND")).toBeCloseTo(123456.78);
    expect(parseNumericValue("0")).toBe(0);
    expect(parseNumericValue("0.55")).toBe(0.55);
    expect(parseNumericValue("Customer#123")).toBeNull();
  });

  it("3. extractRechartsConfig bóc tách đúng cấu hình lồng và phẳng", () => {
    const jsonNested = JSON.stringify({
      chart_type: "bar",
      recharts_config: {
        title: "Test Nested",
        x_key: "name",
        y_keys: ["value"],
      },
    });

    const cfg = extractRechartsConfig(jsonNested);
    expect(cfg).not.toBeNull();
    expect(cfg?.chart_type).toBe("bar");
    expect(cfg?.title).toBe("Test Nested");
    expect(cfg?.x_key).toBe("name");
    expect(cfg?.y_keys).toEqual(["value"]);
  });

  it("4. alignDataWithConfig tự động map x_key và y_keys thiếu vào dữ liệu", () => {
    const data = [
      { c_name: "Customer A", revenue: 100 },
      { c_name: "Customer B", revenue: 200 },
    ];
    const config = {
      chart_type: "bar" as const,
      x_key: "c_name",
      y_keys: ["total_spent"],
    };

    const aligned = alignDataWithConfig(data, config);
    expect(aligned[0].total_spent).toBe(100);
    expect(aligned[1].total_spent).toBe(200);
  });

  it("5. inferRechartsConfig tự động suy luận bar chart khi có bảng số liệu", () => {
    const data = [
      { d_year: 2001, total_revenue: 7820490.52 },
      { d_year: 2002, total_revenue: 8120300.12 },
    ];
    const columns = ["d_year", "total_revenue"];

    const inferred = inferRechartsConfig(data, columns);
    expect(inferred).not.toBeNull();
    expect(inferred?.chart_type).toBe("bar");
    expect(inferred?.x_key).toBe("d_year");
    expect(inferred?.y_keys).toContain("total_revenue");
  });

  it("6. cleanInsightMarkdown loại bỏ sạch sẽ các khối ASCII Text Chart", () => {
    const rawWithAscii = `
Dưới đây là doanh thu các năm:

### 📊 Biểu đồ dạng cột (Text Chart)
Năm | Doanh thu ($)
----+----------------------
2001 | [████████████] $7.8M
2002 | [█████████████] $8.1M

### 💡 Nhận định kinh doanh
Doanh thu năm 2002 tăng trưởng 3.8% so với năm 2001.
`;

    const cleaned = cleanInsightMarkdown(rawWithAscii);
    expect(cleaned).not.toContain("Text Chart");
    expect(cleaned).not.toContain("[████████████]");
    expect(cleaned).toContain("Dưới đây là doanh thu các năm:");
    expect(cleaned).toContain("Doanh thu năm 2002 tăng trưởng 3.8%");
  });

  it("7. extractChartAndDataFromMarkdown bóc tách toàn diện và fallback inferRechartsConfig", () => {
    // Trường hợp 1: Có JSON code block
    const result1 = extractChartAndDataFromMarkdown(sampleMarkdown);
    expect(result1.config).not.toBeNull();
    expect(result1.config?.chart_type).toBe("bar");
    expect(result1.config?.x_key).toBe("c_name");
    expect(result1.data.length).toBe(3);
    expect(result1.data[0].c_name).toBe("Customer#000000349");
    expect(result1.data[0].total_spent).toBeCloseTo(14383665.02);

    // Trường hợp 2: Không có JSON code block nhưng có bảng markdown tiền tệ
    const markdownNoJson = `
Bảng so sánh doanh thu các năm:
| Năm (\`d_year\`) | Tổng doanh thu ($) |
|:---|:---|
| 2001 | $7,820,490.52 |
| 2002 | $8,120,300.12 |
`;
    const result2 = extractChartAndDataFromMarkdown(markdownNoJson);
    expect(result2.config).not.toBeNull();
    expect(result2.config?.chart_type).toBe("bar");
    expect(result2.config?.x_key).toBe("d_year");
    expect(result2.data.length).toBe(2);
    expect(result2.data[0].d_year).toBe(2001);
  });
});
