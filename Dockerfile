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
    uv pip install --no-cache-dir . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装项目源码
COPY . .

# 阶段2: 生产镜像
FROM python:3.12-slim-bookworm

# 配置生产环境镜像源，并移除默认源
RUN rm -rf /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    dbus \
    dbus-x11 \
    libdbus-1-3 \
    libnotify-bin \
    libglib2.0-bin \
    # 包含 gdbus
    # 声音依赖
    pulseaudio-utils \
    alsa-utils \
    # 初始化 D-Bus
    && dbus-uuidgen > /var/lib/dbus/machine-id \
    && mkdir -p /run/dbus \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制源代码
COPY --from=builder /app/src /app/src

# 配置环境变量
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# 由 pyproject.toml 中的 project.scripts 定义的入口点
ENTRYPOINT ["mcp-server-notify"]