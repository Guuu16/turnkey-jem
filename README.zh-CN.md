# 全栈编程面试评估

英文主版本：[README.md](README.md)

仓库地址：<https://github.com/Guuu16/turnkey-jem>

## 项目概览

本仓库包含 Task A 和 Task B 的实现、Task C 的书面回答，以及一个可运行的全栈应用（FastAPI + SQLite 后端，Next.js + TypeScript 前端）。主要文档和源代码注释使用英文；本文件是根目录 README 的中文版。

## 题目要求

以下内容根据原始评估题目整理，用中文说明交付范围和验收点。

### 提交要求

- 提交一个公开或可访问的 GitHub / GitLab 仓库。
- 仓库根目录必须包含 `A/`、`B/`、`C/`、`app/` 四个目录。
- 根目录包含 `README.md`，写明启动步骤、运行命令、假设、架构说明和已知限制。
- 包含自动化测试，并且所有测试都能使用 README 中记录的命令运行。
- 不要提交凭证、token、真实客户数据或个人数据。
- 披露在哪些地方使用了 AI，并能解释或现场修改每一个提交的决策。
- 优先保证正确性、可读性和可维护性，避免不必要的复杂度。
- 校验输入，并让失败行为显式化。
- 明确列出标准库和第三方依赖。

### Task A：库存预留账本（20 分）

为单一 SKU 实现一个确定性的命令处理器。账本需要维护 `on_hand`（在手数量）、`reserved`（已预留数量）和已处理的事件 ID。可用库存为 `on_hand - reserved`。

输入第一行是初始库存 `S` 和命令数量 `N`，随后是 `N` 条命令：

```text
RESERVE event_id order_id qty
RELEASE event_id order_id qty
SHIP event_id order_id qty
RESTOCK event_id qty
```

必须实现的行为：

- 所有数量必须是正整数。
- 格式错误的输入必须被拒绝，并且不能产生部分状态变化。
- `RESERVE` 只有在可用库存足够时才能成功。
- `RELEASE` 和 `SHIP` 不能超过该订单当前的预留数量。
- `SHIP` 同时减少 `on_hand` 和该订单的预留数量。
- 每个 `event_id` 都是幂等的；重放已处理事件返回 `DUPLICATE`，并且不能改变状态。
- 被业务规则拒绝的操作，仍算作已处理事件，以保证后续重放返回 `DUPLICATE`。

每条命令输出 `OK`、`REJECTED` 或 `DUPLICATE`，后跟当前的 `on_hand` 和总 `reserved`。全部命令处理完后，按 `order_id` 排序输出未结预留。

约束：

```text
0 <= S <= 10^12
1 <= N <= 200,000
1 <= qty <= 10^12
event_id 和 order_id 是非空 ASCII token
```

交付物：可执行的 Python 程序、边界和重放测试，以及简短的复杂度分析。

### Task B：履约拆分优化器（20 分）

选择一个仓库分配方案，使订单恰好履约 `Q` 件，并按以下优先级优化：

1. 使用最少的仓库数量。
2. 最小化总成本：每个使用的仓库贡献 `fixed_cost + allocated_qty * unit_cost`。
3. 在当前结果中选择按 `warehouse_id` 排序后字典序最小的分配列表。

输入格式：

```text
W Q
warehouse_id stock fixed_cost unit_cost
```

仓库记录重复 `W` 次。字段含义如下：

- `warehouse_id`：仓库唯一标识。
- `stock`：该仓库最多可分配的数量，分配量必须在 `0..stock`。
- `fixed_cost`：只要使用该仓库就支付一次；分配量为 0 时不支付。
- `unit_cost`：每分配一件商品支付一次。

约束：

```text
1 <= W <= 30
1 <= Q <= 2,000
0 <= stock <= 2,000
0 <= fixed_cost, unit_cost <= 10^6
sum(stock) 可能小于 Q
```

输出要求：

- 无法履约时打印 `1`。
- 否则第一行打印使用的仓库数量和总成本。
- 随后按 `warehouse_id` 排序，打印每个使用的仓库及分配数量。

解法必须超越枚举所有子集的暴力方法，只能使用 Python 标准库，并在文档中说明状态表示、决胜策略以及时间/空间复杂度。测试必须覆盖无法履约、零库存仓库、成本相同平局和超大数量。

### Task C：Xero 集成审查（20 分）

使用简洁的 Markdown 回答，覆盖可观察检查、故障处理和生产环境安全行为。需要时可使用代码片段或伪代码。场景是一个多租户服务在内部订单系统和 Xero 之间同步发票，同步运行在后台 worker 中；token、租户 ID 和同步游标按已连接组织分别存储。

- **C1 连接验证：** 在读取发票前，描述证明 OAuth 和租户选择正常工作的最少调用与检查，并解释每个结果证明了什么。
- **C2 故障诊断：** 当 `connections` 成功但 `invoices` 在不同环境返回 401、403、404 时，给出诊断决策树，覆盖 token 过期、scope、tenant header / ID、权限和环境配置。
- **C3 增量同步：** 为大型组织设计可恢复的发票同步，覆盖分页、变更窗口或 `modified-since`、游标持久化、重复数据、部分失败和安全重放。
- **C4 速率限制：** worker 收到 HTTP 429 时，说明响应头、退避与抖动、并发限制、重试预算、任务调度，以及哪些错误不应重试。
- **C5 数据完整性：** 防止创建发票超时后重试导致重复开票，并说明“Xero 已成功但响应丢失”时如何对账。
- **C6 可观测性与安全：** 列出日志、指标、告警和关联标识符；说明哪些内容绝不能记录，以及密钥和 token 如何存储与轮换。

使用当前官方 Xero 开发者文档，附上引用页面链接，并说明对 SDK 或 API 版本的假设。

### 全栈应用：变体商品详情页（40 分）

构建一个小而具有生产意识的商品详情页（PDP）和后端 API。本环节评估端到端行为，而不只是视觉效果。

技术栈：

- 后端：Python 3.11+ 和 FastAPI。
- 前端：React 和 TypeScript，可使用 Next.js 或 Vite。
- 存储：内存或 SQLite；种子数据必须让应用启动后立即可用。

领域模型要求：

- 一个商品，至少两个选项维度，例如颜色和尺寸。
- 至少 6 个 SKU。
- 包含一个不存在的组合和一个缺货 SKU。
- 每个 SKU 都有自己的 ID、价格、可用数量、图片和选项值。

API 要求：

| 方法 | 端点 | 行为 |
| --- | --- | --- |
| GET | `/api/products/{id}` | 返回商品、选项和 SKU 数据 |
| POST | `/api/cart/items` | 将 SKU 和数量加入购物车 |
| GET | `/api/cart` | 返回当前购物车和商品总数 |

后端要求：

- 在服务端校验 SKU 是否存在、数量以及当前库存。
- 绝不信任客户端传来的价格或库存。
- 加购请求必须接受 `Idempotency-Key`，相同 key 的重复请求不能重复加入商品。
- 对无效输入、库存不足和意外失败返回结构化错误。
- 两个并发请求争抢最后一件库存时不能超卖，并说明实现方式。
- 测试成功、校验、幂等和库存竞态。
- 记录请求/响应示例和状态码；OpenAPI 页面只能补充说明，不能替代 README 中的契约。

前端要求：

- 展示商品图片、名称、描述、所选价格、库存状态和购物车数量。
- 渲染两个选项维度，并明显禁用不存在或不可用的组合。
- 选项改变时解析选中 SKU，并实时更新价格、图片和库存，不能出现陈旧 UI。
- 数量范围限制在 `1` 到可用库存之间，切换 SKU 后仍然有效。
- 加购按钮显示加载状态，防止误触重复提交。
- 以无障碍方式展示成功和错误反馈。
- 覆盖初始加载、可重试的商品加载失败、选择不完整、无效组合、缺货、加购中、成功、校验失败、库存不足和服务端错误状态。
- 在约 `375px` 和 `1280px` 宽度下均可用。
- 支持键盘操作、可见焦点、语义化标签和辅助技术播报。
- 避免不必要的 TypeScript `any`，分离 API、领域和 UI 关注点。
- 至少包含 3 个有意义的前端测试，包括组合解析和防双击。
- 请求延迟、失败或返回比初始响应更新的库存时，UI 必须能在不整页刷新的情况下恢复。

认证、结算、支付和生产部署不在范围内。可选扩展包括带明确回滚策略的乐观更新、隐私安全的 `view_item` / `select_item` / `add_to_cart` 埋点，以及容器化或一条命令启动前后端。

### 评分与提交前检查

| 部分 | 评分重点 | 分值 |
| --- | --- | --- |
| Task A | 状态迁移、幂等、校验、O(N) 处理、高价值测试 | 20 |
| Task B | 优化顺序与决胜策略、可扩展 DP、复杂度分析 | 20 |
| Task C | 诊断准确、可恢复同步、克制重试、完整性、安全与可观测性 | 20 |
| 后端 | 契约清晰、服务端规则、并发安全、幂等、结构化错误与测试 | 20 |
| 前端 | SKU 状态、异步 UX 韧性、无障碍、TypeScript 设计、针对性测试 | 15 |
| 交付 | 易于启动、仓库整洁、明确记录取舍和限制 | 5 |

提交前必须验证仓库可访问、所有启动命令可用、自动化测试通过、假设已记录、AI 使用已披露，并确认没有提交任何密钥。

## 提交索引

- Task A 实现和文档：[A/README.md](A/README.md)
- Task B 实现和文档：[B/README.md](B/README.md)
- 全栈应用文档和 API 契约：[app/README.md](app/README.md)
- Task C 英文回答（包含 C1-C6 的 Python 风格伪代码）：[C/answers.md](C/answers.md)

## 仓库结构

```text
turnkey-jem/
├── .gitignore
├── A/
│   ├── README.md
│   ├── src/
│   └── tests/
├── B/
│   ├── README.md
│   ├── src/
│   └── tests/
├── app/
│   ├── README.md
│   ├── backend/
│   │   ├── app/
│   │   ├── tests/
│   │   └── requirements.txt
│   └── frontend/
│       ├── app/
│       ├── components/
│       ├── docs/
│       └── lib/
├── C/
│   ├── answers.md
│   ├── tests/
│   └── screenshots/
├── requirements.txt
├── README.md
└── README.zh-CN.md
```

## 架构

`A/` 是一个确定性的单进程库存状态机，核心状态为 `on_hand`、`reserved` 和已处理事件 ID。

`B/` 先使用一维 DP 最小化仓库数量和成本，再按仓库 ID 顺序重建字典序最小的分配方案。

`C/` 是 Xero 多租户同步的设计审查，覆盖连接验证、故障分类、增量游标、速率限制、幂等开票、可观测性和密钥轮换。

`app/` 通过 Next.js 服务端渲染初始商品数据，通过同源 `/api/*` 调用 FastAPI；价格、库存、购物车和幂等状态由 FastAPI 在 SQLite 事务中管理。

## 运行测试

在仓库根目录创建 Python 3.11+ 测试环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

在仓库根目录运行 Task A：

```powershell
Push-Location A
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

运行 Task B：

```powershell
Push-Location B
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

运行代码检查：

```powershell
Push-Location A
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m ruff format --check src tests
Pop-Location

Push-Location B
..\.venv\Scripts\python.exe -m ruff check src tests
..\.venv\Scripts\python.exe -m ruff format --check src tests
Pop-Location
```

运行 Task C 的伪代码契约测试：

```powershell
Push-Location C
..\.venv\Scripts\python.exe -m pytest -q
Pop-Location
```

### macOS Terminal

macOS 需要 Python 3.11+，以及带 npm 的 Node.js 20.9+。

在仓库根目录运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

cd A
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check src tests
../.venv/bin/python -m ruff format --check src tests
cd ..

cd B
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check src tests
../.venv/bin/python -m ruff format --check src tests
cd ..

cd C
../.venv/bin/python -m pytest -q
cd ..
```

## 运行全栈应用

先启动 API（首次运行会创建并灌入 SQLite 数据）：

```powershell
Push-Location app\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location
```

再启动前端并打开 <http://127.0.0.1:3000>：

```powershell
Push-Location app\frontend
npm install
npm run dev
Pop-Location
```

运行全栈应用测试和检查：

```powershell
Push-Location app\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m ruff format --check app tests
Pop-Location

Push-Location app\frontend
npm run typecheck
npm test
npm run build
Pop-Location
```

在 macOS 上打开两个 Terminal 窗口。第一个窗口启动 API：

```bash
cd app/backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

第二个窗口启动前端：

```bash
cd app/frontend
npm install
npm run dev
```

在 macOS 上运行全栈检查：

```bash
cd app/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app tests
.venv/bin/python -m ruff format --check app tests
cd ../frontend
npm test
npm run typecheck
npm run build
```

后端测试套件包含 `33` 个测试，前端测试套件包含 `15` 个测试。前端已在 `375×812` 和 `1280×800` 视口完成浏览器验收：移动端为清晰的单列布局，桌面端为双列布局，均无水平溢出。截图见 [375×812](app/frontend/docs/responsive-375x812.png) 和 [1280×800](app/frontend/docs/responsive-1280x800.png)。API 契约、错误码、幂等和防超卖设计见 [app/README.md](app/README.md)。

## AI 使用

- 使用 AI 翻译题目、澄清约束并拆分评分目标。
- 使用 AI 设计正常路径、边界、非法输入和随机差分测试。
- 使用 AI 比较算法方案、审查实现并简化代码结构。
- 使用 AI 解释代码逻辑并整理英文文档。
- 使用项目测试、Ruff、格式检查和手工示例验证最终结果。
- AI 只处理本评估中的合成数据，没有使用凭证、客户数据或个人信息。

## 依赖

- 题目可执行程序只使用 Python 标准库。
- `pytest` 和 `ruff` 只用于开发和验证。
- 根目录依赖见 [requirements.txt](requirements.txt)。
- 全栈应用依赖见 [app/backend/requirements.txt](app/backend/requirements.txt)、[app/backend/requirements-dev.txt](app/backend/requirements-dev.txt) 和 [app/frontend/package.json](app/frontend/package.json)。

## 假设和已知限制

- Task B 遵循题目字面要求：`Q >= 1`，无法履约时输出 `1`。
- Task C 提供可执行的 Python 风格伪代码和审查说明，不连接真实 Xero 租户，也不存储真实凭证。
- 全栈应用只有一个演示购物车，不包含认证、结算、支付或生产部署。
- 商品加入购物车时立即预留库存；没有预留过期和后台释放机制。
- SQLite 适合单主机评估；多节点生产环境应将相同的条件更新和幂等规则迁移到共享数据库。
- 幂等记录目前没有保留期限，商品目录是种子数据，没有管理 API。
