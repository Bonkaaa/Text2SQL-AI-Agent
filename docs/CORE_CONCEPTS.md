# CORE_CONCEPTS.md — Giải thích Các Khái niệm Kỹ thuật Cốt lõi

> **Dự án**: AI Agent Text-to-SQL Self-Service Analytics (TPC-H Benchmark)  
> **Mục đích**: Tài liệu này phân tích chi tiết bản chất, cơ chế hoạt động và lý do lựa chọn các công nghệ nền tảng trong hệ thống: **sqlglot, BigQuery dryRun / DuckDB EXPLAIN, Vector DDL Indexing, Qdrant / pgvector**, và phân định vai trò giữa **DuckDB vs PostgreSQL**.

---

## 1. `sqlglot` — Trọng tài AST & Hàng rào An ninh Truy vấn

### 1.1. `sqlglot` là gì?
`sqlglot` là một thư viện Python mã nguồn mở thuần túy (no C-extensions) chuyên về **SQL Parser, Transpiler, Optimizer và AST Engine**. Nó hỗ trợ hơn 20 dialect SQL khác nhau (BigQuery, DuckDB, Postgres, Snowflake, Spark, SQLite...).

### 1.2. Tại sao KHÔNG ĐƯỢC dùng Regular Expression (Regex) để kiểm tra SQL?
Rất nhiều hệ sinh thái AI sơ khai mắc bẫy bảo mật khi dùng Regex để kiểm tra an toàn, ví dụ:
```python
# SAI LẦM NGUY HIỂM:
if re.search(r"\b(DELETE|DROP|ALTER|INSERT)\b", sql, re.IGNORECASE):
    raise SecurityError("Forbidden keyword detected")
```
Regex kiểm tra chuỗi (String Matching) hoàn toàn bất lực trước các kỹ thuật bypass cơ bản:
1. **Comment Injection**: `SEL/*comment*/ECT ...` hoặc dấu ngắt dòng.
2. **Ký tự ẩn / Encoding**: Chèn ký tự unicode tương đương.
3. **Từ khóa nằm trong Literal String**: Người dùng hỏi: *"Tìm sản phẩm có chữ 'DROP' trong tên"* $\rightarrow$ `WHERE p_name LIKE '%DROP%'` sẽ bị regex chặn nhầm (False Positive).
4. **Stacked Queries / CTE Injection**: `WITH malicious AS ( ... ) SELECT ...`

### 1.3. Cơ chế Abstract Syntax Tree (AST) của `sqlglot`
Thay vì đọc văn bản thô, `sqlglot` phân tích câu lệnh SQL thành một **Cây cú pháp trừu tượng (Abstract Syntax Tree - AST)**, trong đó mỗi thành phần của câu truy vấn trở thành một Node đối tượng rõ ràng (`Select`, `From`, `Join`, `Where`, `Column`, `Table`).

```
                    [exp.Select] (Root Node)
                   /     |      \
        [expressions]  [from]    [where]
             |           |          |
         [Column]     [Table]   [Predicate]
        (l_quantity) (lineitem)     |
                                  [EQ]
                                 /    \
                           [Column]  [Literal]
                         (l_shipmode) ('AIR')
```

### 1.4. Cách hệ thống ứng dụng `sqlglot` trong Control Pipeline
Trong node **AST Sanitizer** và **RBAC Policy**:

1. **Chặn 100% lệnh ghi / phá hoại cấu trúc (Zero-Trust Security)**:
   ```python
   import sqlglot
   from sqlglot import exp

   ast = sqlglot.parse_one(sql, read="duckdb")

   # Bắt buộc Root Node phải là đối tượng exp.Select
   if not isinstance(ast, exp.Select):
       raise SecurityException("Chỉ cho phép truy vấn đọc (SELECT ONLY)!")

   # Quét đệ quy toàn bộ cây để đảm bảo không có câu lệnh con mang tính biến đổi
   forbidden_nodes = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Command)
   if any(ast.find_all(forbidden_nodes)):
       raise SecurityException("Phát hiện câu lệnh can thiệp cấu trúc dữ liệu bị cấm!")
   ```

2. **Trích xuất chính xác danh sách bảng & cột phục vụ RBAC**:
   `sqlglot` duyệt cây AST để lấy chính xác các cột thực sự được `SELECT` hoặc `JOIN`, bỏ qua các chuỗi văn bản thuần:
   ```python
   # Lấy tất cả các bảng được tham chiếu
   tables = [table.name for table in ast.find_all(exp.Table)]

   # Lấy tất cả các cột được gọi
   columns = [col.name for col in ast.find_all(exp.Column)]

   # Đối chiếu RBAC: Nếu role == 'Analyst' mà có 'c_phone' hoặc 'c_acctbal' -> CHẶN
   ```

3. **Tự động gắn chốt an toàn `LIMIT 1000`**:
   Nếu câu truy vấn của LLM quên viết LIMIT, `sqlglot` có thể tự động biến đổi AST trước khi gửi đến warehouse:
   ```python
   if not ast.args.get("limit"):
       ast = ast.limit(1000)
   sanitized_sql = ast.sql("duckdb")
   ```

4. **Chuyển đổi cú pháp giữa các Dialects (Dialect Transpilation)**:
   Code viết cho DuckDB có thể transpile sang BigQuery Standard SQL chỉ bằng:
   ```python
   bigquery_sql = sqlglot.transpile(duckdb_sql, read="duckdb", write="bigquery")[0]
   ```

---

## 2. Cost Guard — BigQuery dryRun vs. DuckDB EXPLAIN

### 2.1. Tại sao phải ước tính chi phí trước khi thực thi?
- Trong môi trường Cloud Data Warehouse (Google BigQuery, Snowflake), chi phí được tính dựa trên **dung lượng dữ liệu được quét từ đĩa (Bytes Scanned)**, thông thường là **$6.25 / 1 TB**.
- Bảng `lineitem` trong thực tế doanh nghiệp có thể chứa hàng trăm triệu đến hàng tỷ dòng. Một câu query không có filter thời gian: `SELECT SUM(l_extendedprice) FROM lineitem` có thể quét hàng trăm Gigabyte dữ liệu trong vài giây, làm cạn kiệt ngân sách hoặc gây nghẽn tài nguyên.
- **Cost Guard** đóng vai trò chốt chặn kiểm soát ngân sách: Nếu câu query dự kiến quét quá hạn mức (ví dụ: > 1GB đối với vai trò `Analyst`), hệ thống sẽ từ chối hoặc bắt buộc phê duyệt đặc biệt.

### 2.2. BigQuery `dryRun=True`
- **Cơ chế**: BigQuery API cung cấp cờ `dry_run=True` khi tạo QueryJob:
  ```python
  from google.cloud import bigquery

  client = bigquery.Client()
  job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
  query_job = client.query(sql_text, job_config=job_config)

  bytes_scanned = query_job.total_bytes_processed
  print(f"Query này sẽ quét: {bytes_scanned / (1024**2):.2f} MB")
  ```
- **Ưu điểm vượt trội**:
  1. **Chi phí 0 USD**: Google hoàn toàn miễn phí các request dry-run.
  2. **Chính xác tuyệt đối**: Trả về chính xác số bytes BigQuery sẽ đọc từ hệ thống lưu trữ Colossus.
  3. **Validate cú pháp và quyền hạn**: Nếu sai tên bảng hoặc vi phạm cú pháp BigQuery, `dryRun` sẽ ném lỗi ngay mà không cần chạy thật.

### 2.3. DuckDB `EXPLAIN`
DuckDB là cơ sở dữ liệu in-process / local, do đó không có cơ chế tính phí theo bytes như dịch vụ cloud. Tuy nhiên, ta dùng câu lệnh `EXPLAIN` hoặc `EXPLAIN ANALYZE` để thu thập **Kế hoạch thực thi (Execution Plan)**:
```sql
EXPLAIN SELECT SUM(l_extendedprice) FROM lineitem WHERE l_shipdate >= '1995-01-01';
```
DuckDB trả về một cây toán tử (Physical Plan):
- `PROJECTION`
- `FILTER` (Pushdown predicate)
- `SEQ_SCAN` hoặc `PARQUET_SCAN` kèm ước tính số dòng `EC: 150000`.

**Chiến lược Cost Guard trên DuckDB của đồ án**:
1. Đọc số lượng dòng ước tính (`Estimated Cardinality`) từ output của `EXPLAIN`.
2. Đối với dữ liệu lưu dạng Parquet trong thư mục `data/`: Ta đọc metadata kích thước file `lineitem.parquet` (khoảng 19MB với scale factor 0.1) và nhân tỷ lệ filter để ước lượng dung lượng bytes scanned tương đương.

---

## 3. Vector DDL Indexing — Schema Linking trong Text-to-SQL

### 3.1. Thách thức lớn nhất của Text-to-SQL trong Doanh nghiệp
Trong cơ sở dữ liệu doanh nghiệp có hàng chục hoặc hàng trăm bảng:
- Không thể nhét toàn bộ câu lệnh `CREATE TABLE` của tất cả các bảng vào Context Window của LLM vì:
  1. **Tràn token & Chi phí cao**: Tiêu tốn hàng nghìn token vô ích cho mỗi câu hỏi đơn giản.
  2. **Hiện tượng Context Dilution (Loãng thông tin)**: Khi context quá dài, LLM bị phân tâm ("Lost in the Middle") và dễ hallucinate tên cột giữa các bảng khác nhau.
  3. **Độ trễ tăng cao (High Latency)**.

### 3.2. Cơ chế hoạt động của Vector DDL Indexing
**Vector DDL Indexing** là kỹ thuật áp dụng RAG (Retrieval-Augmented Generation) chuyên biệt cho Database Metadata:

```
[8 Bảng DDL + Business Metadata]
              ↓
  [Chunking & Enrichment] (Bảng + Cột + Kiểu dữ liệu + Ý nghĩa kinh doanh)
              ↓
  [Embedding Model] (text-embedding-3-small / BGE-M3)
              ↓
  [Vector Database] (Lưu vector đại diện ngữ nghĩa của từng bảng)
              ↓
[User hỏi: "Doanh thu năm 1995 theo từng nước"]
              ↓
  [Vector Similarity Search] (Top-k = 4 bảng: orders, lineitem, customer, nation)
              ↓
  [Chỉ nạp 4 bảng này vào prompt của SQL Generator]
```

### 3.3. Categorical Value Indexing (Cực kỳ quan trọng)
Nếu chỉ index DDL bảng (`c_mktsegment VARCHAR`), LLM sẽ không thể biết được trong database có các phân khúc nào:
- Người dùng hỏi: *"Lọc khách hàng ngành xe hơi"*.
- LLM có thể tự chế ra: `WHERE c_mktsegment = 'Xe hoi'` hoặc `'Cars'` (Sai hoàn toàn!).
- Nhờ có **Categorical Value Indexing**, hệ thống index sẵn danh sách các giá trị phân loại rời rạc:
  - `c_mktsegment`: `['AUTOMOBILE', 'BUILDING', 'FURNITURE', 'HOUSEHOLD', 'MACHINERY']`
  - `r_name`: `['AFRICA', 'AMERICA', 'ASIA', 'EUROPE', 'MIDDLE EAST']`
  - `l_shipmode`: `['AIR', 'FOB', 'MAIL', 'RAIL', 'REG AIR', 'SHIP', 'TRUCK']`
- Khi người dùng hỏi "ngành xe hơi", bộ tra cứu ngữ nghĩa sẽ tìm ra giá trị chuẩn là `'AUTOMOBILE'` và nạp vào file `schema_context.md`.

---

## 4. Qdrant vs. pgvector — So sánh & Đánh giá

Cả hai đều là công cụ lưu trữ vector embeddings phục vụ khâu Schema Search, nhưng có triết lý thiết kế khác nhau:

| Tiêu chí | **Qdrant** | **pgvector** |
|---|---|---|
| **Bản chất** | Vector Database chuyên dụng (Standalone Engine viết bằng Rust) | Extension mở rộng bổ sung kiểu dữ liệu Vector cho PostgreSQL |
| **Hiệu năng tìm kiếm** | Cực cao, tối ưu hóa thuật toán HNSW, hỗ trợ Vector Quantization | Tốt cho quy mô nhỏ/vừa, chậm hơn khi dữ liệu đạt hàng triệu vector |
| **Payload Filtering** | **Rất mạnh**: Lọc metadata kết hợp vector search trong cùng một chu trình index | Hỗ trợ qua câu lệnh SQL WHERE nhưng tốc độ phụ thuộc vào index Postgres |
| **Mức độ phức tạp vận hành**| Cần chạy service riêng (Docker container hoặc Qdrant Cloud) | Tiện lợi nếu đã có sẵn database PostgreSQL (dùng chung một DB) |
| **Mức độ tiêu thụ RAM** | Quản lý bộ nhớ hiệu quả qua Memory-mapped (mmap) files | Tốn nhiều RAM khi build HNSW index trên Postgres |

### Lựa chọn tối ưu cho đồ án:
- **Phương án gọn nhẹ nhất cho Dev**: Dùng **Qdrant Cloud (Free tier)** hoặc **ChromaDB / SQLite-vss** chạy local file để không cần cài đặt thêm server cồng kềnh.
- **Nếu hệ thống Backend đã dùng PostgreSQL**: Tận dụng luôn extension `pgvector` trên PostgreSQL của Supabase để lưu cả bảng `users`, `audit_logs` lẫn vector schema.

---

## 5. Chọn DuckDB hay PostgreSQL cho Project?

Đây là câu hỏi kiến trúc kinh điển nhất trong các đồ án Data & AI. Để trả lời chính xác, cần hiểu rõ sự khác biệt giữa hai kiến trúc lưu trữ:

### 5.1. Bản chất: OLTP (PostgreSQL) vs. OLAP (DuckDB)

```
[PostgreSQL: Row-Oriented (OLTP)]
Row 1: [order_id, cust_id, date, total]  → Dữ liệu từng dòng lưu liền nhau trên đĩa
Row 2: [order_id, cust_id, date, total]  → Tối ưu: INSERT, UPDATE, tìm 1 bản ghi theo ID
Row 3: [order_id, cust_id, date, total]  → Kém tối ưu: SUM(total) phải đọc cả bảng

[DuckDB: Column-Oriented (OLAP)]
Col 1 (order_id): [1, 2, 3, ...]         → Dữ liệu từng cột lưu liền nhau trên đĩa
Col 2 (total):    [100, 250, 50, ...]    → Tối ưu: SUM(total) chỉ đọc đúng cột total!
Col 3 (date):     ['1995', '1995', ...]  → Vectorized Execution: Quét hàng triệu số/giây
```

### 5.2. Bảng so sánh trực tiếp trong ngữ cảnh Đồ án Text-to-SQL

| Tiêu chí | **DuckDB** (Lựa chọn làm Analytical Warehouse) | **PostgreSQL** (Lựa chọn làm Application Database) |
|---|---|---|
| **Kiến trúc dữ liệu** | **Columnar Store (Định dạng cột)** | **Row Store (Định dạng dòng)** |
| **Use case tối ưu** | **OLAP**: Phân tích tổng hợp (`SUM`, `AVG`, `GROUP BY`, quét hàng triệu dòng bảng `lineitem`) | **OLTP**: Giao dịch, ghi đơn lẻ (`INSERT`, `UPDATE`, quản lý phiên người dùng) |
| **Đọc file Parquet** | **Bản địa (Native)**: Đọc trực tiếp các file `lineitem.parquet` không cần nạp vào DB | Phải tạo bảng và COPY dữ liệu vào đĩa trước |
| **Tích hợp TPC-H** | Có sẵn extension `INSTALL tpch; CALL dbgen(sf=0.1);` chỉ trong 1 dòng lệnh | Phải dùng công cụ dbgen bên ngoài biên dịch C rồi import thủ công |
| **Cài đặt & Vận hành** | **In-process**: Không cần server daemon, chạy trực tiếp trong Python process (`import duckdb`) | Cần cài đặt server PostgreSQL, cấu hình user/password/port/network |
| **Concurrency (Ghi đồng thời)**| Kém khi nhiều luồng cùng ghi vào 1 file `.duckdb` | Rất mạnh: Hỗ trợ hàng nghìn transaction đồng thời với ACID đầy đủ |

### 5.3. KẾT LUẬN KIẾN TRÚC: "ĐÚNG NGƯỜI ĐÚNG VIỆC" (HYBRID STORAGE)

Trong đồ án này, ta **không chọn 1 bỏ 1**, mà phân định nhiệm vụ rạch ròi theo đúng chuẩn kỹ thuật doanh nghiệp:

1. **DuckDB đóng vai trò ANALYTICS DATA WAREHOUSE (Kho dữ liệu phân tích)**:
   - Chứa 8 bảng TPC-H (`lineitem`, `orders`, `customer`...).
   - Toàn bộ câu lệnh SQL do AI Agent sinh ra sẽ được thực thi trên DuckDB.
   - Lý do: Tốc độ chạy các câu lệnh TPC-H (join 5 bảng, aggregate triệu dòng) của DuckDB nhanh gấp **10 đến 50 lần** so với PostgreSQL, hỗ trợ Parquet trực tiếp và không tốn chi phí hạ tầng.

2. **PostgreSQL / SQLite đóng vai trò APPLICATION DATABASE (Cơ sở dữ liệu vận hành)**:
   - Chứa các bảng nghiệp vụ hệ thống: `users`, `chat_sessions`, `chat_messages`, `audit_logs`.
   - Quản lý phiên đa người dùng, lưu vết an ninh và phân quyền người dùng.
   - Lý do: Cần tính năng ghi đồng thời an toàn (concurrency), không bị lock file khi nhiều user cùng chat một lúc.
