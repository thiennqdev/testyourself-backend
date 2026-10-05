FROM python:3.11-slim

WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn backend
COPY . .

# Tạo sẵn thư mục lưu trữ dữ liệu và ảnh tải lên
RUN mkdir -p instance uploads

# Thiết lập biến môi trường mặc định
ENV PYTHONUNBUFFERED=1 \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

# Mở cổng 5000
EXPOSE 5000

# Healthcheck kiểm tra backend đã sẵn sàng
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/courses/public || exit 1

# Tự động khởi tạo database (tạo bảng + tài khoản admin) và khởi chạy server
CMD ["sh", "-c", "python init_db.py && python run.py"]
