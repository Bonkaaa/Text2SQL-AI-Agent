/**
 * Tiện ích xuất dữ liệu bảng thành Markdown table và hỗ trợ sao chép vào Clipboard.
 * Tuân thủ triệt để nguyên tắc Ponytail: Sử dụng native API, zero dependencies.
 */

/**
 * Sinh chuỗi Markdown định dạng bảng chuẩn từ danh sách cột và các dòng dữ liệu.
 */
export function generateMarkdownTable(
  columns: string[],
  rows: Record<string, any>[]
): string {
  if (!columns || columns.length === 0) {
    return "";
  }

  // Header row
  const header = `| ${columns.join(" | ")} |`;
  // Separator row
  const separator = `| ${columns.map(() => "---").join(" | ")} |`;
  // Data rows
  const body = (rows || [])
    .map(
      (row) =>
        `| ${columns
          .map((col) => {
            const val = row[col];
            if (val === null || val === undefined) return "-";
            return String(val);
          })
          .join(" | ")} |`
    )
    .join("\n");

  return `${header}\n${separator}\n${body}`;
}

/**
 * Sao chép chuỗi bảng Markdown vào Clipboard hệ thống.
 */
export async function copyMarkdownToClipboard(
  columns: string[],
  rows: Record<string, any>[]
): Promise<boolean> {
  const md = generateMarkdownTable(columns, rows);
  if (!md) return false;

  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(md);
      return true;
    } catch (err) {
      console.error("Lỗi khi sao chép vào clipboard:", err);
      return false;
    }
  }
  return false;
}
