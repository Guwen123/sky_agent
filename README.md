# Agent - 智能生活服务助手
演示Bilibili：BV1oA93BtEzt

## 项目简介

本项目是一个面向餐饮与本地生活场景的智能体系统，采用 `Spring Boot + Vue + FastAPI + LangGraph` 的前后端分层架构，将点评数据、外卖数据、知识库检索与对话式 Agent 能力整合到同一个系统中。

用户登录后，可以在统一对话界面中完成以下操作：

- 查看 hmdp 热门博客、个人历史博客
- 查询 sky_take_out 历史订单
- 绑定 hmdp / sky_take_out 外部账号
- 结合知识库、GraphRAG、Text2SQL 获取餐饮推荐与问答结果
- 先预览再确认外卖订单，降低误下单风险

## 技术栈

- 后端：Spring Boot 2.3、MyBatis-Plus、MySQL、Redis、JWT
- Agent：FastAPI、LangGraph、LangChain、Neo4j、Chroma、GraphRAG、Text2SQL
- 前端：Vue 3、Vite、Axios、Vue Router
- 外部服务：hmdp、sky_take_out

## 核心亮点

### Model / Agent 侧亮点

- 基于 LangGraph 构建工作流，串联消息压缩、LLM 决策、工具调用、偏好更新，支持多轮会话记忆与流式输出。
- 构建 `GraphRAG + 向量检索 + BM25 + Rerank` 的混合检索链路，提升餐饮推荐、评价总结与知识问答的命中率。
- 当图谱未命中时，支持从 MySQL 回源补图，再回写 Neo4j 与向量索引，减少冷启动阶段的知识缺口。
- 封装 `service_tools`，将 hmdp / sky_take_out 的博客、订单、绑定、点单能力统一为 Agent 工具调用。
- 引入 Text2SQL 作为服务数据增强层，把博客结果中的 `shopId` 转成真实店铺名、地址、评分等信息，也为后续自然语言查询数据库预留扩展能力。
- 外卖下单采用“预览确认 -> 用户确认 -> 正式提交”的双阶段机制，避免模型直接下单带来的误操作。

### 工程侧亮点

- Java 后端负责登录鉴权、用户体系、外部账号绑定、对 Python Agent 服务的统一转发。
- Vue 前端支持聊天流式渲染、快捷提问、绑定状态展示、已绑定输入框隐藏、下单确认卡片等交互。
- Agent 与业务系统通过 HTTP 解耦，便于后续替换模型、扩展服务工具或接入更多本地生活平台。

## 项目结构

```text
Agent
├─ src/                         # Spring Boot 后端
│  ├─ main/java/com/agent
│  └─ main/resources
│     ├─ application.yaml
│     └─ db/                    # 初始化 SQL
├─ model/                       # Python Agent
│  ├─ service/run.py            # FastAPI 入口
│  ├─ workflow/
│  │  ├─ runner.py
│  │  ├─ graph_builder.py
│  │  ├─ rag/                   # GraphRAG / 向量检索
│  │  └─ mcp/tools/             # 知识工具、服务工具、Text2SQL
│  └─ contants/contant.py       # 模型/数据库/Neo4j 配置
├─ ui/                          # Vue 3 前端
├─ data/                        # 运行期生成目录
├─ rag_db/                      # Chroma 持久化目录
├─ api.md                       # 接口请求说明
├─ requirements.txt             # Python 依赖
└─ pom.xml                      # Java 依赖
```

## 功能清单

- 用户注册、登录、验证码校验
- Agent 对话与流式对话
- hmdp 账号绑定、验证码发送、历史博客读取、热门博客读取
- sky_take_out 账号绑定、历史订单读取、预览确认式点单
- 结合 GraphRAG 和知识库的餐饮问答与推荐
- 用户偏好注入与对话上下文压缩

## 环境依赖

推荐本地环境：

- JDK 8
- Maven 3.8+
- Python 3.10+
- Node.js 18+
- MySQL 5.7 / 8.0
- Redis 6+
- Neo4j 5.x

## 端口说明

| 服务 | 默认端口 | 说明 |
| --- | --- | --- |
| Vue 前端 | `5173` | Vite 默认开发端口 |
| Spring Boot 后端 | `8072` | 本项目主服务 |
| Python Agent | `8000` | FastAPI + LangGraph |
| hmdp | `8081` | 外部点评服务 |
| sky_take_out | `8086` | 外部外卖服务 |
| MySQL | `3306` | 数据库 |
| Redis | `6379` | 缓存 |
| Neo4j | `7687` | 图数据库 |

## 启动前需要准备

### 1. 数据库

本项目至少会用到以下数据库：

- `sky_agent`：本项目主库
- `hmdp`：点评业务库
- `sky_take_out`：外卖业务库

本仓库内可直接使用的 SQL：

- `src/main/resources/db/init.sql`
  - 初始化 `sky_agent`
  - 创建 `user` 和 `user_account_binding` 表
- `src/main/resources/db/user_account_binding.sql`
  - 单独创建绑定表
- `src/main/resources/db/hmdp.sql`
  - hmdp 基础数据
- `src/main/resources/db/hmdp_final_data.sql`
  - hmdp 补充或整理后的数据脚本，可按你的实际数据选择

说明：

- `sky_take_out` 库请使用你自己的外卖项目 SQL 初始化，并保证其后端接口能正常运行在 `8086`。
- GraphRAG 会读取 `hmdp` 数据，并将部分结构化知识写入 Neo4j 与本地向量库。

### 2. 中间件

确保以下服务已启动：

- MySQL
- Redis
- Neo4j
- hmdp 后端
- sky_take_out 后端

## 需要修改的配置

在推送到 GitHub 之前，请先把以下文件中的本地敏感信息、密钥、密码替换成你自己的配置，不要直接提交真实密钥。

### Java 后端配置

文件：`src/main/resources/application.yaml`

重点字段：

- `spring.datasource.url`
- `spring.datasource.username`
- `spring.datasource.password`
- `spring.redis.host`
- `spring.redis.port`
- `RequestApi.url`
- `external.hmdp.base-url`
- `external.sky-take-out.base-url`

### Python Agent 配置

文件：`model/contants/contant.py`

重点字段：

- `MODEL_API`
- `MODEL_NAME`
- `BASE_API`
- `MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD`
- `REDIS_HOST / REDIS_PORT`
- `HMDP_BASE_URL / SKY_TAKE_OUT_BASE_URL`
- `NEO4J_URL / NEO4J_USERNAME / NEO4J_PASSWORD / NEO4J_DATABASE`

## 启动步骤

建议按下面顺序启动。

### 1. 启动 Python Agent

在项目根目录执行：

```bash
pip install -r requirements.txt
uvicorn model.service.run:app --reload --host 0.0.0.0 --port 8000
```

启动后默认地址：

- `http://localhost:8000`

### 2. 启动 Spring Boot 后端

在项目根目录执行：

```bash
mvn spring-boot:run
```

启动后默认地址：

- `http://localhost:8072`

### 3. 启动前端

在 `ui` 目录执行：

```bash
npm install
npm run dev
```

前端默认访问地址：

- `http://localhost:5173`

## 使用流程

### 1. 登录系统

- 打开前端登录页
- 先获取验证码
- 完成注册或登录

### 2. 绑定外部账号

在设置页中可以绑定：

- `hmdp`
- `sky_take_out`

当前前端已支持：

- 已绑定时显示用户名或手机号
- 若无用户名和手机号则显示“已绑定”
- 已绑定时隐藏验证码、密码、微信 code 等输入框
- 支持重新绑定

### 3. 对话示例

你可以直接输入：

- `请帮我查看最热门的博客`
- `请帮我查看我的历史博客`
- `请帮我查看我的历史订单`
- `推荐一家适合聚餐的火锅店`
- `我要点一份鱼香肉丝和米饭`

### 4. 外卖下单确认

当用户提出点单请求时，系统不会立刻提交订单，而是先返回：

- 店铺名称
- 菜品列表
- 收货地址
- 收货人和手机号

用户确认后，再由 Agent 调用真正的下单接口提交订单。

## 项目当前实现的业务联动

- Java 后端通过 `ApiCilent` 调用 Python Agent 服务
- Python Agent 通过 `service_tools` 调用 hmdp / sky_take_out 业务接口
- Python Agent 通过 `Text2SQL` 直连 MySQL 做店铺信息补全
- GraphRAG 结合 Neo4j 与 Chroma 提供推荐和问答能力

## 后续可继续优化的方向

- 为 Python Agent 增加自动化测试与依赖锁定文件
- 为前端补充接口异常提示、加载态与会话管理
- 增加更多服务工具，例如收藏店铺、地址管理、订单详情查询等
