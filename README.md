# Weather Chat Agent

一个基于 LangChain、LangGraph 和 DeepSeek 的命令行天气查询 Agent。用户可以通过自然语言查询北京、上海和广州的当前天气；Agent 会按需调用 Open-Meteo API，并在同一会话中保留对话状态。

本项目用于学习模型配置、工具调用、会话记忆、错误处理和基础测试。天气数据是实时数据，示例输出会随时间变化。

## 功能

- 使用 DeepSeek `deepseek-flash` 模型进行中文对话。
- 使用 LangChain `create_agent` 创建 Agent，并通过工具调用查询天气。
- 使用 Open-Meteo 免费天气 API 获取当前天气，不需要天气 API Key。
- 当前仅支持北京、上海、广州；坐标定义在 `CITY_COORDS` 中。
- 将 WMO 天气代码转换为中文描述，未收录的代码使用兜底文案。
- 使用 `InMemorySaver` 保存当前进程内的会话状态。
- 通过 Trace Handler 在终端显示模型和工具的开始、完成、失败状态及耗时；不输出提示词、用户输入、工具参数或回复正文。
- 捕获模型 API 错误并提示用户；天气工具会将请求或响应处理错误作为文本返回给 Agent。

## 技术栈

- Python 3.10+
- LangChain (`create_agent`)
- LangGraph (`InMemorySaver`)
- `langchain-deepseek` (`ChatDeepSeek`)
- DeepSeek API
- Open-Meteo API
- `requests`
- `pytest`（测试）

项目当前在 Windows、Python 3.14.9 环境中验证。其他 Python 版本或操作系统尚未在本项目中验证。

## 快速开始

### 1. 创建虚拟环境并安装依赖

在项目根目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install langchain langchain-deepseek langgraph requests pytest
```

如果 PowerShell 阻止激活脚本，可以直接使用虚拟环境中的 Python 执行命令：

```powershell
& .\.venv\Scripts\python.exe -m pip install langchain langchain-deepseek langgraph requests pytest
```

### 2. 设置 DeepSeek API Key

程序通过 `os.environ["DEEPSEEK_API_KEY"]` 读取密钥。代码**不会自动加载 `.env` 文件**，因此只创建 `.env` 文件并不会让程序读取密钥。

在当前 PowerShell 窗口临时设置：

```powershell
$env:DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
```

该设置仅对当前终端会话及其启动的程序有效。也可以在 Windows 用户环境变量中设置 `DEEPSEEK_API_KEY`；设置后重新打开 VS Code 和终端。

不要把真实密钥提交到 Git、粘贴到日志或分享给他人。如果密钥曾经公开，应先在 DeepSeek 控制台撤销并重新生成。

### 3. 启动程序

实际主程序文件名是 `Weather_Chat_Agent.py`：

```powershell
python .\Weather_Chat_Agent.py
```

如果没有激活虚拟环境：

```powershell
& .\.venv\Scripts\python.exe .\Weather_Chat_Agent.py
```

输入天气问题开始对话，输入 `quit` 退出。运行需要有效的 DeepSeek API Key 和网络连接；查询天气还需要能够访问 Open-Meteo。

## 示例

```text
用户: 北京天气怎么样？
[追踪] 模型开始：聊天模型
[追踪] 模型完成（耗时 1.04 秒）
[追踪] 工具开始：天气查询工具
[追踪] 工具完成（耗时 1.10 秒）
[追踪] 模型开始：聊天模型
[追踪] 模型完成（耗时 0.77 秒）
助手: 北京当前天气为多云，气温 13.5°C，风速 5.2 km/h。
```

实际天气、耗时和模型回复会变化。Agent 当前查询的是实时天气，不提供未来天气预报、历史天气或官方预警信息。

## 测试

### 自动化模拟测试

测试使用 Mock 替代天气 HTTP 请求和模型请求，不访问真实天气 API，也不会消耗 DeepSeek API 调用：

```powershell
python -m pytest -v test_weather.py
```

最近一次记录为 13 项测试通过。测试覆盖支持城市天气结果和坐标、不支持城市、未知天气代码、HTTP 错误、请求超时、响应字段缺失、模型连接错误处理及 Trace Handler 输出。以本机实际 pytest 输出为准。

### 真实天气 API 测试

这条命令直接调用天气工具，不经过 DeepSeek Agent，但会实际请求 Open-Meteo：

```powershell
python -c "from Weather_Chat_Agent import get_weather; print(get_weather.invoke({'city': '北京'}))"
```

将 `北京` 替换为 `上海` 或 `广州` 可测试其他支持城市。返回的天气内容随实时数据变化。

### Agent 端到端测试

运行 `Weather_Chat_Agent.py` 后，在交互中提问。这会实际调用 DeepSeek；模型判断需要查询天气时，也会调用 Open-Meteo。真实测试受网络、服务状态和 API Key 有效性影响。

手动测试记录（包括断网、工具耗时、畸形数据和安全诱导场景）见 `测试FAIL.txt`。其中部分失败是测试时故意注入错误后的观察结果，不代表当前正常配置下必然失败。

## 设计说明与已知限制

### Agent 和工具

`create_agent` 负责协调模型和工具：模型根据对话判断是否调用 `get_weather`，工具函数发起天气请求并返回结果，Agent 再生成面向用户的回复。模型可能会根据工具错误信息重试；Trace 可帮助观察调用步骤和耗时。

天气工具使用同步 HTTP 请求。`timeout=5` 限制天气 HTTP 请求的等待时间；如果工具中执行其他同步的慢操作（例如 `time.sleep(10)`），当前这轮 Agent 调用仍会等待其完成。`try/except` 可以处理异常，但不会让慢操作提前结束。

### 会话记忆

程序固定使用 `thread_id="user-chat-1"`，所以同一进程里的连续输入属于同一个会话。`InMemorySaver` 只在进程运行期间保留状态；程序退出后记忆丢失。它不是每轮输入一个独立会话，也不是磁盘持久化存储。

### 天气范围和错误处理

- 城市坐标手动维护在 `CITY_COORDS` 中，新增城市需要添加坐标。
- 当前工具只查询当前天气，不支持预报、历史天气或天气预警。
- 天气请求和响应解析异常会作为文本返回给 Agent；模型 API 错误会由交互循环捕获并提示。
- 真实 API 和网络可能失败，Agent 回复不应被当作官方预警或气象服务承诺。

### Trace 和隐私

Trace Handler 记录模型/工具事件的状态和耗时，不记录输入、输出或工具参数。它是用于本地观察调用流程的轻量回调，不是 LangSmith 追踪服务或持久化审计日志。

## 项目结构

```text
weather_chat_agent/
├── Weather_Chat_Agent.py  # 模型、天气工具、Trace Handler、Agent 和命令行循环
├── test_weather.py        # 自动化模拟测试
├── README.md              # 项目说明
├── 测试FAIL.txt            # 自动化及手动测试记录
└── .gitignore             # 忽略虚拟环境和本地密钥文件
```

这是一个用于学习 Agent 开发的练习项目，优先展示清晰的调用链路和可重复的工具测试，而不是完整的生产级天气服务。
