<a href="https://glama.ai/mcp/servers/@Cactusinhand/mcp_server_notify"> <img width="380" height="200" src="https://glama.ai/mcp/servers/@Cactusinhand/mcp_server_notify/badge" alt="Glama badge for Notify MCP server" /> </a> [![MseeP.ai Security Assessment Badge](https://mseep.net/pr/cactusinhand-mcp-server-notify-badge.png)](https://mseep.ai/app/cactusinhand-mcp-server-notify) 

[![PyPI version](https://badge.fury.io/py/mcp-server-notify.svg)](https://badge.fury.io/py/mcp-server-notify)

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/Cactusinhand/mcp_server_notify)](https://archestra.ai/mcp-catalog/Cactusinhand__mcp_server_notify)

# MCP Notify Server

[English](README.md) | [中文](README.zh.md)

一个为 LLM 提供系统通知功能的 Model Context Protocol (MCP) 服务。当完成 agent 任务时，可以通过这个服务发送系统桌面通知并且带有音效。

## 功能特点

- 在Agent任务完成后发送系统桌面通知
- 播放提示音以引起用户注意，内置简单的音效文件
- 跨平台支持（Windows, macOS, Linux）
- 基于标准 MCP 协议，可与多种 LLM 客户端集成

## 安装

### 使用 [uv](https://docs.astral.sh/uv/) 包管理器安装

```bash
git clone https://github.com/Cactusinhand/mcp_server_notify.git
cd mcp_server_notify

uv venv
source .venv/Scripts/activate

#
uv pip install mcp-server-notify
# or
pip install mcp-server-notify
```

安装完成后，直接调用模块，查看是否安装成功：
```bash
python -m mcp_server_notify
```
该模块接受 `--debug`, `--log--file` 选项，在调试时可以打开，如：
```shell
python -m mcp_server_notify --debug
python -m mcp_server_notify --debug --log-file=path/to/logfile.log
```

## 特别依赖
由于使用了 [Apprise](https://github.com/caronc/apprise) 接口用来实现不同桌面系统的通知发送，需要额外安装一些依赖。

**Windows**
```shell
# windows:// minimum requirements
pip install pywin32
```

**macOS**
```shell
# Make sure terminal-notifier is installed into your system
brew install terminal-notifier
```


## 使用方法

### 在 Claude Desktop 上使用：

找到配置文件 `claude_desktop_config.json`
```json
{
    "mcpServers": {
        "NotificationServer": {
            "command": "uv",
            "args": [
              "--directory",
              "path/to/your/mcp_server_notify project",
              "run",
              "mcp-server-notify",
            ]
        }
    }
}
```

如果是安装到了全局，还可以使用 python 命令调用：
```json
{
    "mcpServers": {
        "NotificationServer": {
            "command": "python",
            "args": [
              "-m",
              "mcp_server_notify",
            ]
        }
    }
}
```

### 在 Cursor 上使用：
找到配置文件 `~/.cursor/mcp.json` 或者： `your_project/.cursor/mcp.json`
```json
{
    "mcpServers": {
        "NotificationServer": {
            "command": "uv",
            "args": [
              "--directory",
              "path/to/your/mcp_server_notify project",
              "run",
              "mcp-server-notify",
            ]
        }
    }
}
```

配置完成后，只需要在给 AI 输入任务的最后，加上一句类似于这样的提示词：`finally, send me a notification when task finished.` 就可以触发了。

在 Cursor 中可以在 `Cursor Settings` -> `Rules` 里面添加这条提示词作为规则，则不用每次手动输入了。


### 通过Docker运行

由于环境兼容问题，暂时还不行。
如果 Docker 容器需要触发主机通知，无论主机操作系统是 Windows、macOS 还是 Linux，解决方案将变得复杂得多，直接使用原生通知通常不可行。

主要问题：
1. 操作系统特定通知系统
每个操作系统（Windows、macOS、Linux）都有其独特的通知机制。

2. Docker 隔离
Docker 容器的隔离性限制了其直接访问主机操作系统资源的能力。

3. 依赖管理
需要为每个操作系统处理不同的通知库和依赖项。


## 许可证

MIT

## 贡献

欢迎提交问题和拉取请求！ 
