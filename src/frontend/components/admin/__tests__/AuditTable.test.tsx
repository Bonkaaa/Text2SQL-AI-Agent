import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { AuditTable } from "../AuditTable";
import { AuditLogItem } from "@/types/api";
import * as exportCsvModule from "@/services/exportCsv";

// Mock exportToCsv
vi.mock("@/services/exportCsv", () => ({
  exportToCsv: vi.fn(),
}));

const mockAuditLogs: AuditLogItem[] = [
  {
    query_id: "q-1",
    session_id: "sess-101",
    user_id: "user_admin",
    role: "Admin",
    question: "Doanh thu tổng hợp theo từng khu vực năm 1995",
    sql: "SELECT r_name, SUM(o_totalprice) FROM orders JOIN customer ON c_custkey = o_custkey GROUP BY r_name;",
    status: "SUCCESS",
    execution_time_ms: 145.2,
    bytes_scanned: 15728640, // ~15 MB
    created_at: "2026-09-21T10:15:30Z",
  },
  {
    query_id: "q-2",
    session_id: "sess-102",
    user_id: "user_analyst",
    role: "Analyst",
    question: "Xem số điện thoại và số dư tài khoản của khách hàng",
    sql: "SELECT c_phone, c_acctbal FROM customer LIMIT 10;",
    status: "BLOCKED_RBAC",
    execution_time_ms: 12.0,
    bytes_scanned: 0,
    error_message: "Truy cập bị chặn: Cột 'c_phone' và 'c_acctbal' bị hạn chế theo chính sách RBAC.",
    created_at: "2026-09-21T10:18:00Z",
  },
  {
    query_id: "q-3",
    session_id: "sess-103",
    user_id: "user_unknown",
    role: "Analyst",
    question: "Xóa toàn bộ dữ liệu trong bảng orders",
    sql: "DROP TABLE orders;",
    status: "BLOCKED_AST",
    execution_time_ms: 8.5,
    bytes_scanned: 0,
    error_message: "AST Sanitizer chặn câu lệnh DDL/DML: Chỉ cho phép câu lệnh SELECT đọc dữ liệu.",
    created_at: "2026-09-21T10:20:15Z",
  },
  {
    query_id: "q-4",
    session_id: "sess-104",
    user_id: "user_analyst",
    role: "Analyst",
    question: "Quét toàn bộ bảng lineitem không có mệnh đề WHERE",
    sql: "SELECT * FROM lineitem;",
    status: "BLOCKED_COST",
    execution_time_ms: 45.0,
    bytes_scanned: 104857600, // 100 MB
    error_message: "Cost Guard chặn: Dung lượng quét vượt ngưỡng giới hạn phân tích.",
    created_at: "2026-09-21T10:22:00Z",
  },
  {
    query_id: "q-5",
    session_id: "sess-105",
    user_id: "user_admin",
    role: "Admin",
    question: "Top 5 sản phẩm bán chạy nhất quý 1",
    sql: "SELECT p_name, SUM(l_quantity) FROM lineitem JOIN part ON p_partkey = l_partkey GROUP BY p_name LIMIT 5;",
    status: "SUCCESS",
    execution_time_ms: 210.0,
    bytes_scanned: 8388608, // 8 MB
    created_at: "2026-09-21T10:25:00Z",
  },
];

describe("Component 5.1: AuditTable (Admin Audit Table)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. Render danh sách bản ghi kiểm toán với đầy đủ các cột và badge trạng thái", () => {
    render(<AuditTable logs={mockAuditLogs} />);

    // Kiểm tra tiêu đề mặc định
    expect(screen.getByText(/Nhật ký kiểm toán an ninh/i)).toBeInTheDocument();

    // Kiểm tra các cột hiển thị thông tin
    expect(screen.getByText(/Doanh thu tổng hợp theo từng khu vực/i)).toBeInTheDocument();
    expect(screen.getAllByText(/user_admin/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/user_analyst/i).length).toBeGreaterThanOrEqual(1);

    // Kiểm tra các badge trạng thái an ninh (xuất hiện ở cả tab và dòng bảng)
    expect(screen.getAllByText(/Thành công/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Vi phạm RBAC/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Chặn AST/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Chặn chi phí/i).length).toBeGreaterThanOrEqual(1);

    // Kiểm tra thời gian thực thi hiển thị
    expect(screen.getByText(/145.2ms/i)).toBeInTheDocument();
  });

  it("2. Lọc danh sách bản ghi theo các tab bộ lọc trạng thái (Status Filter Tabs)", () => {
    render(<AuditTable logs={mockAuditLogs} />);

    // Ban đầu hiển thị tất cả 5 bản ghi
    expect(screen.getByText(/Hiển thị 1 - 5 của 5 bản ghi/i)).toBeInTheDocument();

    // Bấm vào tab 'Vi phạm RBAC'
    const rbacTab = screen.getByRole("button", { name: /Vi phạm RBAC/i });
    fireEvent.click(rbacTab);

    // Chỉ còn 1 bản ghi RBAC hiển thị
    expect(screen.getByText(/Hiển thị 1 - 1 của 1 bản ghi/i)).toBeInTheDocument();
    expect(screen.getByText(/Xem số điện thoại và số dư tài khoản/i)).toBeInTheDocument();
    expect(screen.queryByText(/Doanh thu tổng hợp theo từng khu vực/i)).not.toBeInTheDocument();

    // Bấm lại vào tab 'Tất cả'
    const allTab = screen.getByRole("button", { name: /Tất cả/i });
    fireEvent.click(allTab);
    expect(screen.getByText(/Hiển thị 1 - 5 của 5 bản ghi/i)).toBeInTheDocument();
  });

  it("3. Thanh tìm kiếm nhanh (Instant Search) lọc bản ghi theo từ khóa câu hỏi hoặc SQL", () => {
    render(<AuditTable logs={mockAuditLogs} />);

    const searchInput = screen.getByPlaceholderText(/Tìm kiếm theo câu hỏi, SQL, người dùng/i);
    fireEvent.change(searchInput, { target: { value: "DROP TABLE" } });

    // Chỉ còn 1 bản ghi AST vi phạm chứa DROP TABLE
    expect(screen.getByText(/Xóa toàn bộ dữ liệu trong bảng orders/i)).toBeInTheDocument();
    expect(screen.queryByText(/Doanh thu tổng hợp theo từng khu vực/i)).not.toBeInTheDocument();

    // Bấm nút xóa tìm kiếm
    const clearButton = screen.getByRole("button", { name: /Xóa tìm kiếm/i });
    fireEvent.click(clearButton);

    // Trở về 5 bản ghi
    expect(screen.getByText(/Doanh thu tổng hợp theo từng khu vực/i)).toBeInTheDocument();
  });

  it("4. Mở Modal Chi Tiết Kiểm Toán khi click nút xem chi tiết và hiển thị toàn văn câu lệnh SQL", () => {
    render(<AuditTable logs={mockAuditLogs} />);

    // Tìm tất cả các nút xem chi tiết (hoặc nút Chi tiết)
    const detailButtons = screen.getAllByRole("button", { name: /Chi tiết/i });
    fireEvent.click(detailButtons[0]);

    // Modal xuất hiện
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/Chi tiết truy vấn kiểm toán/i)).toBeInTheDocument();

    // Kiểm tra thông tin trong modal
    expect(screen.getByText(/sess-101/i)).toBeInTheDocument();
    expect(screen.getByText(/q-1/i)).toBeInTheDocument();
    expect(screen.getByText(/SELECT r_name, SUM\(o_totalprice\)/i)).toBeInTheDocument();

    // Đóng modal
    const closeBtn = screen.getByRole("button", { name: /Đóng modal/i });
    fireEvent.click(closeBtn);

    // Modal biến mất
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("5. Phân trang (Pagination) hoạt động chính xác khi có nhiều bản ghi", () => {
    // Tạo 12 bản ghi để kiểm tra phân trang 5 bản ghi/trang
    const manyLogs: AuditLogItem[] = Array.from({ length: 12 }, (_, i) => ({
      query_id: `q-${i + 1}`,
      session_id: `sess-${i + 1}`,
      user_id: `user_${i + 1}`,
      role: i % 2 === 0 ? "Admin" : "Analyst",
      question: `Câu hỏi kiểm toán số ${i + 1}`,
      sql: `SELECT * FROM table_${i + 1};`,
      status: "SUCCESS",
      execution_time_ms: 100 + i,
      bytes_scanned: 1024 * (i + 1),
      created_at: new Date(2026, 8, 21, 10, i).toISOString(),
    }));

    render(<AuditTable logs={manyLogs} initialPageSize={5} />);

    // Trang 1: Hiển thị 1 - 5 của 12 bản ghi
    expect(screen.getByText(/Hiển thị 1 - 5 của 12 bản ghi/i)).toBeInTheDocument();
    expect(screen.getByText(/Câu hỏi kiểm toán số 1\b/i)).toBeInTheDocument();
    expect(screen.queryByText(/Câu hỏi kiểm toán số 6\b/i)).not.toBeInTheDocument();

    // Bấm nút Trang sau
    const nextBtn = screen.getByRole("button", { name: /Trang sau/i });
    fireEvent.click(nextBtn);

    // Trang 2: Hiển thị 6 - 10 của 12 bản ghi
    expect(screen.getByText(/Hiển thị 6 - 10 của 12 bản ghi/i)).toBeInTheDocument();
    expect(screen.getByText(/Câu hỏi kiểm toán số 6\b/i)).toBeInTheDocument();
    expect(screen.queryByText(/Câu hỏi kiểm toán số 1\b/i)).not.toBeInTheDocument();
  });

  it("6. Bấm nút [Xuất CSV] gọi hàm xuất dữ liệu tiện ích exportToCsv", () => {
    render(<AuditTable logs={mockAuditLogs} />);

    const exportBtn = screen.getByRole("button", { name: /Xuất CSV/i });
    fireEvent.click(exportBtn);

    expect(exportCsvModule.exportToCsv).toHaveBeenCalledTimes(1);
    expect(exportCsvModule.exportToCsv).toHaveBeenCalledWith(
      expect.stringContaining("nhat_ky_kiem_toan"),
      expect.any(Array),
      expect.any(Array)
    );
  });
});
