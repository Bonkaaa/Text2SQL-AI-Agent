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
 * Phân tích và chuyển đổi chuỗi số học thông minh,
 * hỗ trợ các ký hiệu tiền tệ ($ € £ ₫ USD VND), số phân cách dấu phẩy,
 * và loại bỏ các chú thích phụ trong ngoặc đơn (vd: 89,806.08 (Lưu ý...)).
 */
export function parseNumericValue(valStr: string): number | null {
  if (!valStr || typeof valStr !== "string") return null;
  const trimmed = valStr.trim();
  if (!trimmed) return null;

  // Khớp số có dấu phẩy phân cách hàng nghìn và phần thập phân, có thể có ký hiệu tiền tệ phía trước
  // Ví dụ: "$7,820,490.52", "89,806.08 (Lưu ý:...)", "14,383,665.02 VND", "123.45"
  const match = trimmed.match(
    /^[\$€£₫\s]*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)/i
  );
  if (match) {
    const rawNum = match[1].replace(/,/g, "");
    const parsed = Number(rawNum);
    // Tránh nhận nhầm các mã định danh có số 0 ở đầu (vd: "000123") ngoại trừ số 0 đơn thuần hoặc số thập phân "0.xx"
    if (!isNaN(parsed) && (!/^0\d+/.test(rawNum) || rawNum === "0")) {
      return parsed;
    }
  }
  return null;
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

      // Thử parse thành số thực thông minh
      const parsedNum = parseNumericValue(cleanCell);
      const isNum = parsedNum !== null;

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
 * Tự động suy luận cấu hình Recharts (RechartsConfig) từ dữ liệu bảng
 * khi LLM không sinh ra khối JSON nhưng có dữ liệu bảng số liệu phân tích.
 */
export function inferRechartsConfig(
  data: Record<string, any>[],
  columns: string[],
  title?: string
): RechartsConfig | null {
  if (!data || data.length === 0 || !columns || columns.length < 2) {
    return null;
  }

  const sample = data[0];
  const keys = Object.keys(sample);

  // 1. Xác định cột phân loại / trục hoành (X-Axis)
  // Ưu tiên cột thời gian, danh mục, tên: year, date, month, channel, category, name, brand...
  const categoryKeywords = [
    "year",
    "d_year",
    "năm",
    "month",
    "d_moy",
    "tháng",
    "channel",
    "kênh",
    "category",
    "danh mục",
    "item",
    "mặt hàng",
    "name",
    "tên",
    "c_name",
    "brand",
    "thương hiệu",
    "state",
    "bang",
    "tỉnh",
  ];

  let xKey = keys.find((k) =>
    categoryKeywords.some((kw) => k.toLowerCase().includes(kw))
  );

  // Nếu không thấy, lấy cột đầu tiên có kiểu string
  if (!xKey) {
    xKey = keys.find((k) => typeof sample[k] === "string");
  }

  // Nếu tất cả đều là số, lấy cột đầu tiên
  if (!xKey) {
    xKey = keys[0];
  }

  // 2. Xác định các cột số liệu đo lường / trục tung (Y-Axis)
  // Loại bỏ các cột id, sk, mã
  const isIdCol = (k: string) =>
    /(_sk|_id|_key|stt|mã|^id$|^key$)/i.test(k);

  const numericKeys = keys.filter(
    (k) => k !== xKey && typeof sample[k] === "number" && !isIdCol(k)
  );

  // Nếu không có cột số phi-id nào, lấy các cột số bất kỳ khác xKey
  const finalYKeys =
    numericKeys.length > 0
      ? numericKeys
      : keys.filter((k) => k !== xKey && typeof sample[k] === "number");

  if (finalYKeys.length === 0) {
    return null;
  }

  // Giới hạn tối đa 3 chuỗi số liệu để biểu đồ không bị rối
  const selectedYKeys = finalYKeys.slice(0, 3);

  // Tạo series_labels thân thiện
  const seriesLabels: Record<string, string> = {};
  selectedYKeys.forEach((k) => {
    // Viết hoa chữ cái đầu hoặc giữ nguyên
    seriesLabels[k] = k
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  });

  return {
    chart_type: "bar",
    title: title || "Biểu đồ trực quan hóa số liệu",
    x_key: xKey,
    x_axis: xKey,
    y_keys: selectedYKeys,
    y_axis: selectedYKeys,
    series_labels: seriesLabels,
    legend: selectedYKeys.length > 1,
  };
}

/**
 * Làm sạch văn bản Markdown, loại bỏ các khối Text Chart ASCII thô sơ
 * (biểu đồ text thô vẽ bằng dấu gạch ngang, ký tự [████], ASCII pipes...)
 * để giao diện chỉ giữ lại nhận định kinh doanh và nhường việc vẽ đồ thị cho Recharts.
 */
export function cleanInsightMarkdown(text: string): string {
  if (!text || typeof text !== "string") return "";

  let cleaned = text;

  // 1. Loại bỏ các heading kèm khối text chart
  // Ví dụ:
  // ### 📊 Biểu đồ dạng cột (Text Chart)
  // Năm | Doanh thu ($)
  // ----+----------------------
  // 2001 | [████████████] $7.8M
  const headingWithAsciiPattern =
    /(?:#{1,4}\s*(?:[^\n]*(?:Text Chart|Biểu đồ dạng cột|Biểu đồ cột|ASCII Chart|Biểu đồ minh họa)[^\n]*)\n+)(?:[^\n]*\n*)*?(?=(?:\n#{1,4}\s|\n---|\n\*\*|\Z))/gi;
  cleaned = cleaned.replace(headingWithAsciiPattern, "");

  // 2. Loại bỏ khối codeblock chứa text chart
  const codeBlockAsciiPattern =
    /```(?:text|ascii)?\s*\n[\s\S]*?(?:\[[█■#=*]+\]|----+[\-+]+)[\s\S]*?```/gi;
  cleaned = cleaned.replace(codeBlockAsciiPattern, "");

  // 3. Loại bỏ các đoạn text chart trần không có heading
  const rawAsciiTablePattern =
    /(?:\n|^)[^\n]+(?:\||\+)[^\n]+\n(?:[-+:| ]{4,}\n)(?:[^\n]*(?:\[[█■#=*]+\]|[█■]{2,})[^\n]*\n*)+/gi;
  cleaned = cleaned.replace(rawAsciiTablePattern, "\n");

  // Thu gọn các dòng trống liên tiếp
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n").trim();

  return cleaned;
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

  // 3. Nếu chưa có config từ JSON block nhưng có bảng số liệu, tự động suy luận RechartsConfig
  if (!extractedConfig && data.length > 0) {
    extractedConfig = inferRechartsConfig(data, columns);
  }

  // 4. Nếu có cả config và data, căn chỉnh cho khớp
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

