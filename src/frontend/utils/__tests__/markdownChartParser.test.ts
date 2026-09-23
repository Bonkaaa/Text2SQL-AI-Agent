import { describe, it, expect } from "vitest";
import {
  parseMarkdownTable,
  extractRechartsConfig,
  alignDataWithConfig,
  extractChartAndDataFromMarkdown,
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

  it("2. extractRechartsConfig bóc tách đúng cấu hình lồng và phẳng", () => {
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

  it("3. alignDataWithConfig tự động map x_key và y_keys thiếu vào dữ liệu", () => {
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

  it("4. extractChartAndDataFromMarkdown bóc tách toàn diện từ cả văn bản Markdown", () => {
    const result = extractChartAndDataFromMarkdown(sampleMarkdown);

    expect(result.config).not.toBeNull();
    expect(result.config?.chart_type).toBe("bar");
    expect(result.config?.x_key).toBe("c_name");
    expect(result.data.length).toBe(3);
    expect(result.data[0].c_name).toBe("Customer#000000349");
    expect(result.data[0].total_spent).toBeCloseTo(14383665.02);
  });
});
