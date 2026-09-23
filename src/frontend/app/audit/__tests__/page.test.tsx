import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AuditPage from "../page";
import * as apiModule from "@/services/api";
import { AuditLogsResponse } from "@/types/api";

// Mock services/api
vi.mock("@/services/api", () => ({
  getAuditLogs: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    detail: string;
    constructor(message: string, status = 500, detail = "") {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  },
}));

// Mock next/link to render simple <a> tag
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mutable AppContext mock
let mockCurrentRole = "Admin";
const mockSetCurrentRole = vi.fn();
const mockShowToast = vi.fn();

vi.mock("@/context/AppContext", () => ({
  useAppContext: () => ({
    currentRole: mockCurrentRole,
    setCurrentRole: mockSetCurrentRole,
    showToast: mockShowToast,
  }),
  useOptionalAppContext: () => ({
    currentRole: mockCurrentRole,
    setCurrentRole: mockSetCurrentRole,
    showToast: mockShowToast,
  }),
}));

const mockAuditLogsResponse: AuditLogsResponse = {
  total: 5,
  limit: 100,
  offset: 0,
  logs: [
    {
      query_id: "q-1",
      session_id: "sess-101",
      user_id: "user_admin",
      role: "Admin",
      question: "Doanh thu tổng hợp theo từng khu vực năm 1995",
      sql: "SELECT r_name, SUM(o_totalprice) FROM orders JOIN customer ON c_custkey = o_custkey GROUP BY r_name;",
      status: "SUCCESS",
      execution_time_ms: 145.2,
      bytes_scanned: 15728640,
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
      user_id: "user_analyst",
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
      bytes_scanned: 104857600,
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
      bytes_scanned: 8388608,
      created_at: "2026-09-21T10:25:00Z",
    },
  ],
};

describe("Component 5.2: Admin Audit Page (app/audit/page.tsx)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCurrentRole = "Admin";
  });

  it("1. Khi vai trò là Analyst, hiển thị màn hình cảnh báo 403 Forbidden và không gọi API getAuditLogs", () => {
    mockCurrentRole = "Analyst";

    render(<AuditPage />);

    // Kiểm tra màn hình từ chối quyền truy cập
    expect(screen.getByText(/Truy cập bị hạn chế/i)).toBeInTheDocument();
    expect(screen.getAllByText(/403 Forbidden/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Trần Thị Bình/i)).toBeInTheDocument();
    expect(screen.getByText(/Nguyễn Văn An/i)).toBeInTheDocument();

    // Không được gọi API lấy dữ liệu audit
    expect(apiModule.getAuditLogs).not.toHaveBeenCalled();

    // Có nút quay về trang phân tích
    expect(screen.getByRole("link", { name: /Quay về trang phân tích/i })).toBeInTheDocument();
  });

  it("2. Bấm nút 'Chuyển sang vai trò Admin' trên màn hình 403 sẽ gọi setCurrentRole('Admin')", () => {
    mockCurrentRole = "Analyst";

    render(<AuditPage />);

    const switchBtn = screen.getByRole("button", { name: /Chuyển sang vai trò Admin/i });
    fireEvent.click(switchBtn);

    expect(mockSetCurrentRole).toHaveBeenCalledWith("Admin");
  });

  it("3. Khi vai trò là Admin, gọi API getAuditLogs và hiển thị đủ 4 thẻ thống kê KPI kiểm toán", async () => {
    mockCurrentRole = "Admin";
    vi.mocked(apiModule.getAuditLogs).mockResolvedValueOnce(mockAuditLogsResponse);

    render(<AuditPage />);

    // Kiểm tra đã gọi API với vai trò Admin
    expect(apiModule.getAuditLogs).toHaveBeenCalledWith(100, 0, "Admin");

    // Chờ dữ liệu nạp và kiểm tra 4 thẻ KPI
    await waitFor(() => {
      expect(screen.getByText(/Tổng số truy vấn/i)).toBeInTheDocument();
      expect(screen.getByText(/Tỷ lệ thành công/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Vi phạm RBAC/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Chặn AST & Chi phí/i)).toBeInTheDocument();
    });

    // Kiểm tra số liệu tính toán:
    // Tổng số: 5
    expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(1);
    // Vi phạm RBAC: 1
    expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
    // Chặn AST & Chi phí: 1 (AST) + 1 (COST) = 2
    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
  });

  it("4. Render bảng kiểm toán AuditTable với dữ liệu nhận được từ API", async () => {
    mockCurrentRole = "Admin";
    vi.mocked(apiModule.getAuditLogs).mockResolvedValueOnce(mockAuditLogsResponse);

    render(<AuditPage />);

    await waitFor(() => {
      // Kiểm tra câu hỏi của bản ghi hiển thị trong bảng
      expect(screen.getByText(/Doanh thu tổng hợp theo từng khu vực/i)).toBeInTheDocument();
      expect(screen.getByText(/Xem số điện thoại và số dư tài khoản/i)).toBeInTheDocument();
    });
  });

  it("5. Bấm nút Làm mới trên TopBar kích hoạt gọi lại API getAuditLogs", async () => {
    mockCurrentRole = "Admin";
    vi.mocked(apiModule.getAuditLogs).mockResolvedValue(mockAuditLogsResponse);

    render(<AuditPage />);

    await waitFor(() => {
      expect(apiModule.getAuditLogs).toHaveBeenCalledTimes(1);
    });

    const refreshBtn = screen.getByRole("button", { name: /Làm mới dữ liệu/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(apiModule.getAuditLogs).toHaveBeenCalledTimes(2);
      expect(mockShowToast).toHaveBeenCalledWith(
        expect.stringContaining("Đã làm mới dữ liệu kiểm toán"),
        "info"
      );
    });
  });

  it("6. Hiển thị thông báo lỗi khi API ném ngoại lệ và hỗ trợ nút Thử lại", async () => {
    mockCurrentRole = "Admin";
    vi.mocked(apiModule.getAuditLogs).mockRejectedValueOnce(
      new Error("Không thể kết nối đến máy chủ backend")
    );

    render(<AuditPage />);

    await waitFor(() => {
      expect(screen.getByText(/Không thể tải nhật ký kiểm toán/i)).toBeInTheDocument();
    });

    // Mock cho lần gọi kế tiếp thành công
    vi.mocked(apiModule.getAuditLogs).mockResolvedValueOnce(mockAuditLogsResponse);

    const retryBtn = screen.getByRole("button", { name: /Thử lại/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(apiModule.getAuditLogs).toHaveBeenCalledTimes(2);
      expect(screen.getByText(/Doanh thu tổng hợp theo từng khu vực/i)).toBeInTheDocument();
    });
  });
});
