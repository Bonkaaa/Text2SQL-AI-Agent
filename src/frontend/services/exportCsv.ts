/**
 * Tiện ích xuất dữ liệu bảng kết quả truy vấn Text2SQL thành file CSV.
 * Hỗ trợ chuẩn mã hóa UTF-8 với Byte Order Mark (BOM) để Microsoft Excel hiển thị tiếng Việt chính xác.
 */

/**
 * Chuẩn hóa và escape các ký tự đặc biệt trong ô dữ liệu CSV (dấu phẩy, dấu nháy kép, ký tự xuống dòng).
 */
function formatCsvCell(value: any): string {
  if (value === null || value === undefined) {
    return "";
  }

  if (typeof value === "object") {
    value = JSON.stringify(value);
  } else {
    value = String(value);
  }

  // Nếu chứa dấu phẩy, dấu ngoặc kép hoặc ký tự ngắt dòng thì cần bọc trong dấu ngoặc kép và escape nháy đôi
  if (
    value.includes('"') ||
    value.includes(",") ||
    value.includes("\n") ||
    value.includes("\r")
  ) {
    return `"${value.replace(/"/g, '""')}"`;
  }

  return value;
}

/**
 * Xuất mảng dữ liệu JSON thành tệp tin CSV tải về trực tiếp trên trình duyệt.
 *
 * @param filename Tên file xuất ra (ví dụ: 'bao_cao_doanh_thu_1995')
 * @param columns Danh sách tên các cột dữ liệu
 * @param rows Danh sách các bản ghi kết quả truy vấn
 */
export function exportToCsv(
  filename: string,
  columns: string[],
  rows: Record<string, any>[]
): void {
  if (!columns || columns.length === 0) {
    console.warn("Không có cột dữ liệu nào để xuất CSV.");
    return;
  }

  // 1. Tạo dòng tiêu đề (Header Row)
  const headerLine = columns.map(formatCsvCell).join(",");

  // 2. Tạo các dòng dữ liệu (Data Rows)
  const dataLines = (rows || []).map((row) =>
    columns.map((col) => formatCsvCell(row[col])).join(",")
  );

  // 3. Nối các dòng lại kèm ký tự UTF-8 BOM (\uFEFF) cho Excel
  const csvContent = "\uFEFF" + [headerLine, ...dataLines].join("\r\n");

  // 4. Khởi tạo Blob và kích hoạt tải về phía Client
  const blob = new Blob([csvContent], {
    type: "text/csv;charset=utf-8;",
  });

  const url = URL.createObjectURL(blob);
  const cleanFilename = filename.endsWith(".csv") ? filename : `${filename}.csv`;

  const downloadLink = document.createElement("a");
  downloadLink.href = url;
  downloadLink.setAttribute("download", cleanFilename);
  document.body.appendChild(downloadLink);
  downloadLink.click();

  // Dọn dẹp DOM node và URL object
  document.body.removeChild(downloadLink);
  URL.revokeObjectURL(url);
}
