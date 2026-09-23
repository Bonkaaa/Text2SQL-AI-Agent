import { ChartType, RechartsConfig } from "@/types/api";

/**
 * Kết quả bóc tách dữ liệu và cấu hình biểu đồ từ văn bản Markdown
 */
export interface ExtractedChartData {
  config: RechartsConfig | null;
  data: Record<string, any>[];
  columns: string[];
}

/**
 * Trích xuất bảng Markdown (Markdown Table) thành danh sách các objects và tên cột.
 */
export function parseMarkdownTable(text: string): {
  data: Record<string, any>[];
  columns: string[];
} {
  if (!text || typeof text !== "string") {
    return { data: [], columns: [] };
  }

  const lines = text.split("\n");
  const tableLines: string[] = [];
  let inTable = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      inTable = true;
      tableLines.push(trimmed);
    } else if (inTable) {
      if (tableLines.length >= 3) {
        // Đã thu thập đủ một bảng Markdown hoàn chỉnh
        break;
      }
      inTable = false;
      tableLines.length = 0;
    }
  }

  if (tableLines.length < 3) {
    return { data: [], columns: [] };
  }

  const parseCells = (row: string): string[] =>
    row
      .slice(1, -1)
      .split("|")
      .map((c) => c.trim());

  const rawHeaders = parseCells(tableLines[0]);
  if (rawHeaders.length === 0) {
    return { data: [], columns: [] };
  }

  // Chuẩn hóa tên cột: ưu tiên lấy từ trong backtick `column_name` hoặc (col)
  const headerKeys = rawHeaders.map((h, idx) => {
    const backtickMatch = h.match(/`([^`]+)`/);
    if (backtickMatch) return backtickMatch[1].trim();
    const parenMatch = h.match(/\(([^)]+)\)/);
    if (parenMatch) return parenMatch[1].trim();
    const cleaned = h
      .replace(/[^a-zA-Z0-9_\s]/g, "")
      .trim()
      .replace(/\s+/g, "_")
      .toLowerCase();
    return cleaned || `col_${idx}`;
  });

  const dataRows: Record<string, any>[] = [];

  // Bỏ qua dòng header (index 0) và dòng divider |:--- | :--- | (index 1)
  for (let i = 2; i < tableLines.length; i++) {
    const cells = parseCells(tableLines[i]);
    if (cells.length === 0) continue;

    const rowObj: Record<string, any> = {};

    cells.forEach((cell, idx) => {
      // Loại bỏ định dạng markdown trong ô dữ liệu như **in đậm** hoặc `code`
      const cleanCell = cell.replace(/[`*]/g, "").trim();

      // Thử parse thành số thực nếu hợp lệ (loại bỏ dấu phẩy phân cách hàng nghìn)
      const numericCandidate = cleanCell.replace(/,/g, "");
      const parsedNum = Number(numericCandidate);
      const isNum =
        !isNaN(parsedNum) &&
        numericCandidate !== "" &&
        !/^0\d+/.test(numericCandidate);

      const val = isNum ? parsedNum : cleanCell;
      const key = headerKeys[idx] || `col_${idx}`;
      rowObj[key] = val;

      // Lưu thêm alias theo header gốc sạch để khớp linh hoạt
      const rawKey = rawHeaders[idx]?.replace(/[`*]/g, "").trim();
      if (rawKey && rawKey !== key) {
        rowObj[rawKey] = val;
      }
    });

    dataRows.push(rowObj);
  }

  return {
    data: dataRows,
    columns: headerKeys,
  };
}

/**
 * Bóc tách và chuẩn hóa cấu hình Recharts từ JSON string (hoặc codeblock)
 */
export function extractRechartsConfig(rawJson: string): RechartsConfig | null {
  if (!rawJson || typeof rawJson !== "string") {
    return null;
  }

  try {
    const trimmed = rawJson.trim();
    const parsed = JSON.parse(trimmed);

    if (typeof parsed !== "object" || parsed === null) {
      return null;
    }

    // Trường hợp 1: Có nested object `recharts_config`
    if (parsed.recharts_config && typeof parsed.recharts_config === "object") {
      const inner = parsed.recharts_config;
      const chartType: ChartType =
        parsed.chart_type || inner.chart_type || "bar";
      return {
        chart_type: chartType,
        title: inner.title || parsed.title,
        x_key: inner.x_key || inner.x_axis,
        x_axis: inner.x_axis || inner.x_key,
        y_keys: Array.isArray(inner.y_keys)
          ? inner.y_keys
          : inner.y_keys
            ? [inner.y_keys]
            : Array.isArray(inner.y_axis)
              ? inner.y_axis
              : inner.y_axis
                ? [inner.y_axis]
                : [],
        y_axis: inner.y_axis || inner.y_keys,
        series_labels: inner.series_labels || {},
        description: inner.description,
        legend: inner.legend ?? true,
      };
    }

    // Trường hợp 2: Cấu trúc phẳng có `chart_type` hoặc `x_key`/`y_keys`
    if (parsed.chart_type || parsed.x_key || parsed.x_axis) {
      const chartType: ChartType = parsed.chart_type || "bar";
      return {
        chart_type: chartType,
        title: parsed.title,
        x_key: parsed.x_key || parsed.x_axis,
        x_axis: parsed.x_axis || parsed.x_key,
        y_keys: Array.isArray(parsed.y_keys)
          ? parsed.y_keys
          : parsed.y_keys
            ? [parsed.y_keys]
            : Array.isArray(parsed.y_axis)
              ? parsed.y_axis
              : parsed.y_axis
                ? [parsed.y_axis]
                : [],
        y_axis: parsed.y_axis || parsed.y_keys,
        series_labels: parsed.series_labels || {},
        description: parsed.description,
        legend: parsed.legend ?? true,
      };
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Đồng bộ các trường x_key và y_keys giữa config và dữ liệu bảng.
 * Đảm bảo Recharts luôn tìm thấy thuộc tính để vẽ cột/đường/mảng.
 */
export function alignDataWithConfig(
  data: Record<string, any>[],
  config: RechartsConfig
): Record<string, any>[] {
  if (!data || data.length === 0) return [];

  const sample = data[0];
  const keys = Object.keys(sample);

  // Tìm x_key phù hợp
  let targetXKey = config.x_key || config.x_axis || "";
  if (!targetXKey || sample[targetXKey] === undefined) {
    // Tìm key có chứa tên targetXKey hoặc key dạng chuỗi đầu tiên
    const matched = keys.find(
      (k) =>
        k.toLowerCase() === targetXKey.toLowerCase() ||
        k.toLowerCase().includes(targetXKey.toLowerCase())
    );
    if (matched) {
      targetXKey = matched;
    } else {
      // Lấy key dạng string đầu tiên
      const strKey = keys.find((k) => typeof sample[k] === "string");
      if (strKey) targetXKey = strKey;
    }
  }

  // Tìm y_keys phù hợp
  let targetYKeys = config.y_keys || [];
  if (targetYKeys.length === 0 && config.y_axis) {
    targetYKeys = Array.isArray(config.y_axis) ? config.y_axis : [config.y_axis];
  }

  // Tìm các cột kiểu số trong dữ liệu
  const numericKeys = keys.filter((k) => typeof sample[k] === "number");
  const isIdKey = (k: string) =>
    /(_id|_key|mã|stt|^id$|^key$)/i.test(k);
  const metricCandidates = numericKeys.filter((k) => !isIdKey(k));
  const fallbackNumericKeys =
    metricCandidates.length > 0 ? metricCandidates : numericKeys;

  // Bản đồ từ khóa ngữ nghĩa giữa key tiếng Anh và nhãn tiếng Việt/Anh
  const semanticKeywords: Record<string, string[]> = {
    spent: ["spent", "chi tiêu", "tiêu", "mua"],
    revenue: ["revenue", "doanh thu", "doanh số"],
    total: ["total", "tổng", "sum", "toàn bộ"],
    profit: ["profit", "lợi nhuận", "lãi"],
    cost: ["cost", "chi phí", "giá vốn"],
    price: ["price", "giá", "đơn giá"],
    quantity: ["quantity", "qty", "số lượng"],
    discount: ["discount", "chiết khấu", "giảm giá"],
  };

  return data.map((row) => {
    const updated = { ...row };

    // Đảm bảo x_key có dữ liệu
    if (config.x_key && updated[config.x_key] === undefined && updated[targetXKey] !== undefined) {
      updated[config.x_key] = updated[targetXKey];
    }

    // Đảm bảo từng y_key có dữ liệu số
    targetYKeys.forEach((yKey, idx) => {
      if (updated[yKey] === undefined) {
        // 1. Thử khớp trực tiếp theo tên
        let matchedNumKey = keys.find((k) =>
          k.toLowerCase().includes(yKey.toLowerCase())
        );

        // 2. Thử khớp theo từ khóa ngữ nghĩa tiếng Việt / Anh
        if (!matchedNumKey) {
          const lowerY = yKey.toLowerCase();
          for (const [concept, keywords] of Object.entries(semanticKeywords)) {
            if (lowerY.includes(concept)) {
              matchedNumKey = fallbackNumericKeys.find((k) =>
                keywords.some((kw) => k.toLowerCase().includes(kw))
              );
              if (matchedNumKey) break;
            }
          }
        }

        // 3. Fallback vào cột số phi-ID hoặc cột số theo index
        if (!matchedNumKey) {
          matchedNumKey =
            fallbackNumericKeys[idx] || fallbackNumericKeys[0] || numericKeys[0];
        }

        if (matchedNumKey && updated[matchedNumKey] !== undefined) {
          updated[yKey] = updated[matchedNumKey];
        }
      }
    });

    return updated;
  });
}

/**
 * Trích xuất toàn diện cả cấu hình biểu đồ và dữ liệu bảng từ Markdown Text.
 */
export function extractChartAndDataFromMarkdown(markdownText: string): ExtractedChartData {
  if (!markdownText || typeof markdownText !== "string") {
    return { config: null, data: [], columns: [] };
  }

  // 1. Tìm khối ```json ... ``` trong markdown
  const jsonBlockRegex = /```(?:json)?\s*([\s\S]*?)\s*```/g;
  let match: RegExpExecArray | null;
  let extractedConfig: RechartsConfig | null = null;

  while ((match = jsonBlockRegex.exec(markdownText)) !== null) {
    const candidateJson = match[1];
    if (
      candidateJson.includes("chart_type") ||
      candidateJson.includes("recharts_config")
    ) {
      const cfg = extractRechartsConfig(candidateJson);
      if (cfg) {
        extractedConfig = cfg;
        break;
      }
    }
  }

  // 2. Tìm bảng Markdown
  const { data, columns } = parseMarkdownTable(markdownText);

  // 3. Nếu có cả config và data, căn chỉnh cho khớp
  let alignedData = data;
  if (extractedConfig && data.length > 0) {
    alignedData = alignDataWithConfig(data, extractedConfig);
  }

  return {
    config: extractedConfig,
    data: alignedData,
    columns,
  };
}
