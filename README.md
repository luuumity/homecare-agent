# 陪伴大屏

面向养老房间平板的大屏陪伴应用：卧床的爷爷 + 行动方便但易忘事的奶奶。核心是「大字体、少层级、能听会说、东西放哪了、提醒、一键打电话」。

## 当前进度

**阶段 5 初版已上线：https://homecare.cinnamon.xin**（页面内 PIN 登录，见「线上部署」）。平板浏览器打开即可完整使用首页、对话、物品、提醒、打电话、待确认与自检。

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 前后端骨架、SQLite/FTS5 探针、版本约定、交接文档 | 已完成 |
| 1 | 存储层 + 原始 REST API + 审计 | 已完成 |
| 2 | Agent 编排（纯文本联调） | 已完成 |
| 3 | 大屏 Web UI 业务页面 | 已完成 |
| 4 | Android 壳（WebView、kiosk、版本检查；HMS 语音待第二步） | 骨架已就绪（`shell/android/`），待本地构建与真机验收 |
| 5 | 云端 VPS 部署、备份、回滚 | 初版已完成（域名 + HTTPS + 备份） |

## 技术栈

- 前端：Vue 3 + TypeScript + Vite + TailwindCSS（`frontend/`）
- 后端：Python FastAPI + sqlite3 标准库（`backend/`），无 ORM、无 Docker
- 数据库：单文件 SQLite，中文检索用 FTS5 `trigram` 分词
- 模型：DeepSeek（OpenAI 兼容），密钥只放后端
- 壳：HarmonyOS 4.0 平板上的 Android 薄壳 + WebView + HMS 语音（阶段 4）

## Agent 能力

核心对话引擎在 `backend/app/agent/`，让老人/家属可以**用自然语言**操作所有功能，而不是点菜单。入口：`POST /api/v1/chat`。

### 能做什么

- **问事**：「我的老花镜放哪了？」→ 查物品库并回答位置
- **记事**：「遥控器在电视柜左边抽屉」→ 调用工具写入物品库
- **设提醒**：「每天早上 8 点提醒我吃降压药」→ 创建每日重复提醒
- **打电话**：「给我儿子打电话」→ 记录通话请求（网页版只记录，壳阶段 4 接拨号）
- **记忆问答**：「我对什么药过敏？」→ 从已确认的长期记忆中回答
- **记新事**：「我每天早饭后吃降压药」→ 保存为长期记忆（医疗/身份类需双确认）

### 工作原理

- **上下文**：系统提示词 + 已确认长期记忆（FTS5 中文片段召回）+ 最近 12 条消息 + 更早对话摘要
- **工具调用**：模型只能通过 12 个受校验的工具读写数据（物品/提醒/联系人/通话/记忆的增删改查），工具层复用阶段 1 的校验、审计和软删除
- **工具循环**：最多 4 轮，模型决定何时调用工具、何时直接回复
- **隐私脱敏**：发给模型前把手机号、身份证、座机、银行卡替换为 `[PHONE_1]` 等占位符，回复在本地还原；模型上下文永不出现原始号码
- **医疗/身份双确认**：这类记忆保存后为 `pending`，必须老人当面确认 → 家属确认才生效；未确认记忆不进入上下文
- **上下文压缩**：消息超过 30 条时，自动把较早对话压缩为摘要，保留最近 12 条
- **未配置密钥时**：接口返回 503，不会伪造回复

## 目录

```
backend/
  app/config.py       配置与 .env 读取
  app/db.py           SQLite 连接、初始化、FTS5 探针
  app/migrations.py   建表 SQL 与版本迁移
  app/repository.py   数据访问（审计 / 软删除 / 同步队列）
  app/schemas.py      探针接口模型
  app/schemas_v1.py   业务接口模型
  app/schemas_agent.py 对话接口模型
  app/routers/        /api/v1 接口（物品/提醒/联系人/通话/记忆/待确认/审计/对话）
  app/agent/          对话编排：LLM、脱敏、记忆检索、工具、压缩
  app/adapters/       家属通知通道占位
  scripts/probe.py    离线探针（不启动服务）
  scripts/smoke_v1.py 阶段 1 冒烟测试
  scripts/smoke_agent.py 阶段 2 冒烟测试（--live 走真实模型）
frontend/
  src/api.ts                  带类型的接口封装（统一超时、错误、X-Actor）
  src/router.ts               路由：/ /chat /items /reminders /contacts /confirmations /diagnose
  src/views/HomeView.vue      大字首页（时钟、四个磁贴、下一件事、待确认徽标）
  src/views/ChatView.vue      对话页（历史、发送、工具标签、待确认跳转）
  src/views/ItemsView.vue     东西放哪了（搜索、新增/改位置/删除）
  src/views/RemindersView.vue 提醒（列表、暂停/启用、增改删）
  src/views/ContactsView.vue  打电话（脱敏号码、确认弹窗、通话记录）
  src/views/ConfirmationsView.vue 待确认（老人确认 → 家属确认）
  src/views/DiagnoseView.vue  设备自检页
  src/components/             PageHeader / BaseModal / EmptyState
  public/version.json         前端版本约定
shell/version.json            壳版本约定
shell/android/                Android 壳工程（阶段 4 骨架，本地构建）
docs/stage4-handoff.md        阶段 4 构建、安装与真机验收步骤
```

## 本地启动

### 后端

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # 按需填写，至少保持默认即可
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

接口：

- `GET /api/health` 健康检查
- `GET /api/version` 版本（含 `min_shell_version`）
- `GET /api/diagnose` 数据库、FTS5、LLM 配置诊断（不返回密钥）

阶段 1 业务接口（写操作可带 `X-Actor: family|elder|agent|system`，默认 `family`）：

| 资源 | 接口 |
| --- | --- |
| 物品 | `GET/POST /api/v1/items`、`GET/PATCH/DELETE /api/v1/items/{id}`，支持 `?q=` 搜索 |
| 提醒 | `GET/POST /api/v1/reminders`、`GET/PATCH/DELETE /api/v1/reminders/{id}` |
| 联系人 | `GET/POST /api/v1/contacts`、`GET/PATCH/DELETE /api/v1/contacts/{id}` |
| 通话记录 | `GET/POST /api/v1/calls`（记录中只存脱敏号码） |
| 记忆 | `GET/POST /api/v1/memories`、`GET/PATCH/DELETE /api/v1/memories/{id}`、`GET .../versions` |
| 待确认 | `GET/POST /api/v1/confirmations`、`GET .../{id}`、`POST .../{id}/elder-confirm`、`.../family-confirm`、`.../reject` |
| 审计 | `GET /api/v1/audit?entity_type=&entity_id=` |
| 对话 | `POST /api/v1/chat`、`GET /api/v1/chat/history`、`GET /api/v1/chat/status` |

医疗/身份类记忆创建后为 `pending`，必须老人确认后再由家属确认才生效；低风险记忆直接 `active`。所有写操作写审计与 `sync_outbox`，删除均为软删除。

### 阶段 2 对话

`POST /api/v1/chat` 接收 `{ "text": "..." }`，返回 `reply`、本次调用的工具、待确认 ID、是否触发压缩。单个主对话，不做会话隔离。

- 上下文：系统提示词 + 已确认长期记忆（FTS5 中文片段召回）+ 最近 12 条消息 + 更早对话摘要。
- 工具：物品增删改查、提醒增删改查、联系人列表、通话请求、记忆检索、记忆保存；全部复用阶段 1 校验、审计与软删除。
- 医疗/身份记忆经工具保存后为 `pending`，回复会提示「需老人和家属确认」；未确认记忆不进入上下文。
- 发送模型前脱敏：手机号、身份证、座机、银行卡替换为 `[PHONE_1]` 等占位符，回复在本地还原；模型上下文不出现原始号码。
- 工具循环最多 4 轮；未配置密钥时接口返回 503。消息超过 30 条时自动把较早对话压缩为摘要（保留最近 12 条）。

离线探针（不启动服务，退出码非 0 表示异常）：

```bash
cd backend
.venv/bin/python scripts/probe.py
```

阶段 1 冒烟测试（需服务已启动）：

```bash
cd backend
.venv/bin/python scripts/smoke_v1.py
```

阶段 2 冒烟测试（离线默认；`--live` 会真实调用 3 轮 DeepSeek，使用临时库）：

```bash
cd backend
.venv/bin/python scripts/smoke_agent.py
.venv/bin/python scripts/smoke_agent.py --live
```

### 前端

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 ，/api 已代理到 127.0.0.1:8000
npm run build      # 产物在 frontend/dist/
```

### 阶段 3 页面

| 页面 | 路由 | 说明 |
| --- | --- | --- |
| 首页 | `/` | 大时钟、问候、四个入口磁贴、下一件事提醒、待确认数量、服务状态 |
| 说说话 | `/chat` | 文本对话、历史记录、工具动作标签、有待确认时可直接跳转 |
| 东西放哪了 | `/items` | 关键词搜索（300ms 防抖）、新增、改位置、删除 |
| 提醒 | `/reminders` | 今天与往后的提醒、暂停/启用、增改删、重复规则 |
| 打电话 | `/contacts` | 只读白名单、脱敏号码、确认后只记录请求（网页版不拨号） |
| 需要确认的事 | `/confirmations` | 老人已确认 → 家属确认两步，可拒绝并填原因 |
| 设备自检 | `/diagnose` | 版本、数据库、FTS5、模型配置、服务器时间 |

大屏约束：根字号 20px、主要按钮高度 ≥ 3.25rem、两级以内层级、全部中文、不使用 Emoji；语音按钮在阶段 4 壳完成前禁用并标注原因。

## 验证结果

阶段 0：

- SQLite 3.45.1，`fts5_available=true`，`fts5_trigram_available=true`，中文子串「提醒爷爷」命中 1 条
- `/api/health`、`/api/version`、`/api/diagnose` 均返回 200
- `npm run build`（含 `vue-tsc --noEmit`）通过
- `https://api.deepseek.com` 可达（未配置密钥时返回 401，属预期）；LLM 实际调用留到阶段 2

阶段 1：

- 旧库从 schema v0 迁移到 v1，全新库初始化同样到达 v1；20 张表（含 `memories_fts` 及触发器）就绪
- 冒烟测试 5 组全部通过：物品增删改查与软删除、联系人/通话记录脱敏、提醒停用、记忆检索与版本、医疗记忆双确认与拒绝
- 未老人确认时家属直接确认返回 409；审计与 `sync_outbox` 均有记录；FTS 中文子串检索可用

阶段 2（2026-11-01）：

- 离线 6 组通过：脱敏与还原、只召回已确认记忆、工具层读写与确认、模拟模型工具循环、医疗记忆双确认提示、上下文压缩
- 真实 DeepSeek 3 轮通过：查物品调用 `find_items`、记忆问答直接使用已确认记忆、记物品调用 `save_item` 并落库
- `POST /api/v1/chat` 端到端返回 200，`/chat/history`、`/chat/status` 正常；全部测试使用临时库，开发库未被污染
- 联调用的 DeepSeek 密钥按需写入 `backend/.env`（已被 `.gitignore` 忽略，不会提交）

阶段 3（2026-11-01）：

- `npm run build`（含 `vue-tsc --noEmit`）通过；浏览器端到端验收使用临时库，覆盖首页、对话、物品、提醒、联系人、待确认六类页面
- 首页：时钟、四个磁贴、下一件事、待确认徽标、服务状态正常；提醒时间以服务端 `Asia/Shanghai` 写入，浏览器时区不同时显示会换算
- 对话页：发送「我的老花镜放在哪里？」→ 调用 `find_items`，回复「老花镜在床头柜第二层，黑色镜框的那副。」并显示「查了物品记录」
- 物品页：新增「水杯 / 茶几上」、删除、搜索过滤均正常；提醒页暂停/启用正常
- 联系人页：号码显示为 `138****8000`、`139****9000`；确认弹窗明确「网页版不会真的拨号」，确认后写入通话记录
- 待确认页：老人已确认 → 家属确认两步走通，状态变为「已生效」，待确认区清空
- 已知环境限制：本沙箱的浏览器预览层会改写 URL 查询串（中文查询会被解成原始字节，后端返回 400）。同一请求用 curl 直连后端与经 Vite（`?q=%E8%80%81...`）均返回 200 且只命中「老花镜」，前端也已改用 `URLSearchParams` 编码，因此属沙箱问题；中文搜索需在真实浏览器/平板上复验
- 阶段 3 验收结束后已停止本地服务并删除临时库，开发库未被写入

阶段 5（2026-11-01）：

- 阿里云香港轻量（Ubuntu 22.04.5，2C1G，30G 盘）+ 2G swap；nginx 1.18 静态托管 `dist`，`/api` 反代 `127.0.0.1:8000`
- 后端 systemd（`homecare-api.service`，用户 `homecare`，仅监听 127.0.0.1，开机自启）
- `https://homecare.cinnamon.xin` Let's Encrypt 证书生效（到期 2027-01-30，`certbot.timer` 自动续期），HTTP 301 跳 HTTPS
- 页面内 PIN 登录（`POST /api/v1/auth/login`，HMAC 签名 Cookie，30 天有效；失败 5 次按 IP 锁定 5 分钟）；静态页面公开、业务接口全部要求会话；ufw 仅放行 22/80/443
- 每日 03:30 用 `sqlite3 .backup` 做在线备份，保留 14 天；journald 上限 200M
- 线上真实模型联调 3 轮通过（查物品 / 记忆问答 / 记物品，使用临时库，未污染生产库）
- 浏览器实测：首页四磁贴与时钟、进入 `/chat` 并收到模型回复，控制台无报错

## 线上部署（阶段 5）

线上地址 `https://homecare.cinnamon.xin`，使用页面内 6 位 PIN 登录（PIN 在服务器 `/opt/homecare/backend/.env` 的 `AUTH_PIN`，改后执行 `systemctl restart homecare-api`）。会话 Cookie 有效期 30 天，首页右上角可「退出」。连续输错 5 次按来源 IP 锁定 5 分钟。

常用运维命令（在服务器上以 root 执行）：

```bash
systemctl status homecare-api        # 后端状态
systemctl restart homecare-api       # 改代码/改 .env 后重启
journalctl -u homecare-api -n 50     # 后端日志
/opt/homecare/backups/backup.sh      # 手动备份（产物在 /opt/homecare/backups）
nginx -t && systemctl reload nginx   # 改 nginx 配置后校验并重载
```

更新流程：本地 `npm run build` → 上传 `dist` 到 `/opt/homecare/web` → 后端代码解包到 `/opt/homecare/backend` 并 `.venv/bin/pip install -r requirements.txt` → `systemctl restart homecare-api`。

## 版本约定

- 业务接口统一挂在 `/api/v1/` 下（阶段 1 起）；阶段 0 探针接口保留在 `/api/`。
- 后端版本：`backend/.env` 的 `APP_VERSION`（默认值在 `backend/app/config.py`），当前 `0.4.0-stage3`。
- 前端版本：`frontend/public/version.json`（`web_version`、`min_shell_version`、`built_at`）。
- 壳版本：`shell/version.json`（当前 `0.1.0`，需与 `shell/android/app/build.gradle.kts` 的 `SHELL_VERSION`、`versionName` 一致）。
- 壳启动时对比 `/api/version` 的 `min_shell_version`，低于则提示家属安装新 APK；Web 更新走同域静态文件，刷新即生效。

## 注意

- `.env` 已被忽略，切勿提交密钥；模型上下文禁止出现手机号、身份证、详细住址（阶段 2 已落实号码类脱敏，详细住址仍靠不采集）。
- 护士站没有可用 API：相关操作只记录 + 本地提醒，不伪造「已通知」。
- Android 壳无法在当前云端完成（无 SDK/adb/设备），见 [HANDOFF.md](./HANDOFF.md)。
