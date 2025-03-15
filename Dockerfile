# 阶段1: 使用预装 uv 的镜像
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# 配置国内镜像源（兼容 slim 镜像）
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

WORKDIR /app

# 分阶段安装依赖
COPY pyproject.toml uv.lock ./

# 创建虚拟环境并安装生产依赖
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache-dir -r uv.lock -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装项目源码
COPY . .
RUN . /app/.venv/bin/activate && \
    uv pip install --no-cache-dir -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阶段2: 生产镜像
FROM python:3.12-slim-bookworm

# 配置生产环境镜像源
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libsdl2-mixer-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 配置环境变量
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

ENTRYPOINT ["python", "-m", "mcp_server_notify"]