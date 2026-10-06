# OPLang Compiler Lite

Trình biên dịch OPLang với giao diện web, được duy trì bởi [nguyendnam](https://github.com/nguyendnam).

Dự án phục vụ học tập và thử nghiệm các giai đoạn của một compiler:

```text
OPLang source → Lexer → Parser → AST → Semantic analysis → Jasmin
```

Giao diện hiển thị lỗi biên dịch, AST dạng JSON và mã Jasmin cho JVM. API chỉ biên dịch, không thực thi chương trình người dùng. Mỗi lần biên dịch ghi kết quả vào thư mục tạm riêng và tự dọn sau khi hoàn tất.

## Công nghệ và tính năng

- Compiler: Python, ANTLR 4.13.2, kiểm tra ngữ nghĩa và sinh mã Jasmin.
- Backend: FastAPI, kiểm tra kích thước source tối đa 100 KiB, cấu hình CORS.
- Frontend: React 19, TypeScript, Vite, Monaco Editor.
- Có chương trình mẫu, phím tắt Ctrl/Cmd+Enter, lưu source trong trình duyệt và hủy yêu cầu cũ khi đổi source.
- Docker Compose chạy toàn bộ ứng dụng; GitHub Actions kiểm tra compiler, API, frontend và Docker.

## Chạy bằng Docker

Cần Docker và Docker Compose. Từ thư mục repository:

```sh
docker compose up --build
```

- Giao diện: <http://localhost:5173>
- API và Swagger: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/v1/health>

Lần build đầu cần kết nối mạng để tải dependency và ANTLR. Dừng ứng dụng bằng `docker compose down`.

## Chạy trực tiếp

Cần Python 3.12+, Java 17+ (để sinh lexer/parser), Node.js 22.12+ và npm. Các lệnh chạy từ thư mục repository, trừ bước frontend.

### Backend

```sh
python -m venv .venv
```

Kích hoạt môi trường:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# Linux / macOS
source .venv/bin/activate
```

Cài dependency, sinh parser và chạy API:

```sh
python -m pip install -r requirements.txt
python scripts/build_antlr.py
python -m uvicorn backend.app.main:app --reload --port 8000
```

Script sinh ANTLR chạy trên Windows/Linux/macOS, tải JAR vào `.cache/` và sinh module Python vào `build/`. Chạy lại script sau khi sửa `src/grammar/OPLang.g4`. Hai thư mục này không được commit.

### Frontend

Mở terminal thứ hai:

```sh
cd frontend
npm ci
npm run dev
```

Mở <http://localhost:5173>. Mặc định frontend kết nối API tại `http://localhost:8000`. Để dùng API khác, sao chép `frontend/.env.example` thành `frontend/.env.local`, sửa `VITE_API_URL` rồi khởi động lại Vite.

### Cấu hình backend

Backend đọc biến môi trường của tiến trình; `.env.example` là mẫu tham khảo, không được tự động nạp. Ví dụ PowerShell trước khi chạy API:

```powershell
$env:OPLANG_ALLOWED_ORIGINS = "http://localhost:5173"
$env:OPLANG_MAX_SOURCE_BYTES = "102400"
```

`OPLANG_ALLOWED_ORIGINS` nhận danh sách origin cách nhau bằng dấu phẩy. Khi triển khai frontend ở domain khác, thêm origin đó vào cấu hình backend.

## API

- `GET /api/v1/health`: HTTP 200 khi compiler sẵn sàng, HTTP 503 nếu thiếu mã nguồn hoặc module ANTLR.
- `POST /api/v1/compile`: nhận JSON như ví dụ bên dưới.

```json
{
  "source": "class Main { static void main() { io.writeIntLn(10); } }",
  "options": { "includeAst": true, "includeJasmin": true }
}
```

Kết quả gồm `success`, `stage`, `ast`, `jasmin_files`, `errors` và `compilation_time_ms`. Lỗi lexer/parser/ngữ nghĩa/sinh mã trả HTTP 200 với `success: false`; source quá lớn trả HTTP 413. Xem schema đầy đủ tại `/docs`.

## Kiểm tra và build

Sau khi kích hoạt môi trường Python và sinh ANTLR:

```sh
python -m pip install -r requirements.txt
python -m pytest tests backend/tests -q
```

Build frontend:

```sh
cd frontend
npm ci
npm run build
```

Output nằm trong `frontend/dist/`. Bộ test kiểm tra lexer, parser, AST, ngữ nghĩa, mã Jasmin dạng text và API; không yêu cầu Jasmin assembler hay chạy bytecode JVM.

## Cấu trúc

```text
backend/              FastAPI, schema, route và test API
compiler_core/        Facade biên dịch và chuẩn hóa kết quả
frontend/             Giao diện React và ví dụ OPLang
src/                  Grammar, AST, semantic checker, code generator, runtime IO
tests/                Test hồi quy compiler
scripts/              Script sinh ANTLR
.github/              Workflow CI
Dockerfile            Image backend
compose.yaml          Chạy backend và frontend cùng nhau
render.yaml           Cấu hình triển khai backend trên Render
requirements.txt      Dependency chạy backend và kiểm thử
```

Đặc tả ngôn ngữ: [oplang_specification.md](oplang_specification.md).
Quy tắc ngữ nghĩa: [oplang-semantic_constraints_and_errors.md](oplang-semantic_constraints_and_errors.md).

## Triển khai

Backend dùng `Dockerfile`; `render.yaml` có cấu hình Render và yêu cầu đặt `OPLANG_ALLOWED_ORIGINS` theo domain frontend. Frontend triển khai thư mục `frontend/dist/` lên dịch vụ static hosting; đặt `VITE_API_URL` trước khi build. Backend đọc `PORT` từ môi trường, mặc định `10000` trong Docker.