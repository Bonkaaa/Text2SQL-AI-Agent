import { describe, it, expect } from "vitest";
import { formatDurationSeconds, formatNumberVi } from "../formatters";

describe("Utility: formatters", () => {
  it("formatDurationSeconds đổi đúng mili-giây sang giây với 2 chữ số thập phân", () => {
    expect(formatDurationSeconds(30246.05)).toBe("30.25s");
    expect(formatDurationSeconds(185)).toBe("0.19s");
    expect(formatDurationSeconds(85)).toBe("0.09s");
    expect(formatDurationSeconds(1000)).toBe("1.00s");
    expect(formatDurationSeconds(0)).toBe("0.00s");
  });

  it("formatDurationSeconds xử lý an toàn khi đầu vào là undefined, null, NaN", () => {
    expect(formatDurationSeconds(undefined)).toBe("");
    expect(formatDurationSeconds(null)).toBe("");
    expect(formatDurationSeconds(NaN)).toBe("");
  });

  it("formatNumberVi định dạng phân tách hàng nghìn chuẩn", () => {
    expect(formatNumberVi(14383665.02)).toContain("14");
    expect(formatNumberVi("1000")).toContain("1");
  });
});
