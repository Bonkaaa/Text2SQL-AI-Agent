/**
 * Tiện ích định dạng thời gian và dữ liệu hiển thị trên giao diện người dùng.
 */

/**
 * Định dạng mili-giây (ms) sang dạng giây (s) với 2 chữ số thập phân.
 * Ví dụ:
 *  - 30246.05 -> "30.25s"
 *  - 185 -> "0.19s"
 *  - 0 -> "0.00s"
 */
export function formatDurationSeconds(ms?: number | null): string {
  if (ms === undefined || ms === null || isNaN(ms)) {
    return "";
  }
  const seconds = Math.round(ms / 10) / 100;
  return `${seconds.toFixed(2)}s`;
}

/**
 * Định dạng số với phân tách hàng nghìn chuẩn tiếng Việt.
 */
export function formatNumberVi(value: number | string): string {
  if (typeof value === "number") {
    return value.toLocaleString("vi-VN");
  }
  const num = Number(value);
  if (!isNaN(num)) {
    return num.toLocaleString("vi-VN");
  }
  return String(value);
}
