# 交接说明（HANDOFF）

给本地 Trae（有 Android SDK / adb / 真机）以及未来的自己。云端环境已完成阶段 0–3，但无法构建或安装 Android 壳。

## 1. 背景

- 使用场景：养老院房间里的 10 寸平板，常驻大屏，给卧床（半身不遂）的爷爷和行动方便但健忘的奶奶使用。
- 设备：华为 MatePad Air **DBY2-W00**，HarmonyOS 4.0。
- 家属不常在家：Web 部分必须能远程更新；壳（APK）偶尔更新，由家人点一下安装。
- 当前仓库：`frontend/` + `backend/` 已完成阶段 0–3；Android 壳未开始。

## 2. 已锁定决策（不要再改）

- 前端 Vue 3 + TypeScript + Vite + TailwindCSS；后端 FastAPI + sqlite3 标准库；不用 Pinia、不用 ORM、不用 Docker、不做复杂账号体系。
- 单个主对话，不做会话隔离；长期记忆 + 上下文压缩；Agent 只能通过受校验的工具写数据；软删除 + 审计。
- SQLite 单库分层表：messages、summaries、conversation_state、memories、memory_versions、memories_fts（FTS5 trigram）、items、reminders、call_logs、contacts、documents、pending_confirmations、audit_log、sync_outbox/sync_state。
- 隐私：发给 DeepSeek 前脱敏；手机号/身份证/详细住址用占位符，模型上下文里永不出现手机号；本地解析占位符。
- 医疗/身份类记忆：老人当面确认 + 家属推送二次确认（家属确认暂缓，先留适配接口，后续短信签名链接）。
- 电话：只外呼、固定白名单、不接听、不允许语音改联系人。护士站无 API：只记录 + 本地报警，**绝不伪造「已通知护士站」**。
- 部署：云 VPS + 同域 HTTPS（nginx 静态 `dist` + `/api` 反代）。Web 更新自动刷新；壳更新家属点安装。
- 语音最终架构：Android 薄壳 + WebView + HMS ASR/TTS；唤醒词自有方案（优先级：物理/BLE 按钮 > sherpa-onnx 离线 > Porcupine）；Web Speech 仅兜底。

### 华为语音限制（已调研，勿踩坑）

- HMS ML Kit 短语音识别单次约 60 秒；长语音转写约 5 小时；离线 TTS Full SDK 仅手机，平板不可用。
- Core Speech Kit 端侧唤醒/识别需 HarmonyOS 6+，**4.0 用不了**。
- TTS 说话前先停掉上一次播放（XiaoBan 的经验），避免叠音。

## 3. 云端已完成（阶段 0–3）

- 阶段 0：`backend/` 探针接口 `/api/health`、`/api/version`、`/api/diagnose`；离线探针；`frontend/` 大字首页与 `/diagnose`；`shell/version.json`。
- 阶段 1：迁移到 schema v1（`app/migrations.py`），建齐业务表（messages/summaries/conversation_state/memories/memory_versions/memories_fts/items/reminders/call_logs/contacts/documents/pending_confirmations/audit_log/sync_outbox/sync_state）。
- `/api/v1` 已提供物品、提醒、联系人、通话记录、记忆、待确认、审计接口；所有写操作写 `audit_log` 与 `sync_outbox`，删除均软删除；医疗/身份记忆走「老人确认 → 家属确认」两步，未老人确认时家属确认返回 409。
- 冒烟测试 `scripts/smoke_v1.py` 全部通过；旧库与全新库均能迁移到 v1。
- 验证：SQLite 3.45.1，FTS5 trigram 中文检索通过；前端 `vue-tsc` + `vite build` 通过。
- 阶段 2：`app/agent/` 实现 LLM 客户端（标准库 urllib）、脱敏、记忆检索、工具层、主对话编排与上下文压缩；接口 `POST /api/v1/chat`、`GET /api/v1/chat/history`、`GET /api/v1/chat/status`。
- 隐私：手机号、身份证、座机、银行卡发送前替换为占位符，回复本地还原；未确认的医疗/身份记忆不进入上下文；工具结果同样脱敏。
- 上下文：系统提示词 + 已确认记忆 + 最近 12 条消息 + 摘要；超过 30 条自动压缩较早对话。工具循环最多 4 轮。
- 冒烟测试 `scripts/smoke_agent.py`：离线 6 组 + 真实 DeepSeek 3 轮全部通过；端到端接口联调用临时库，开发库未污染。
- 阶段 2 收尾时曾清空 `LLM_API_KEY`；用户确认该测试密钥可继续用几周（额度较低）后已恢复，阶段 4/5 联调注意配额。
- 阶段 3：`frontend/` 完成大屏业务 UI，路由 `/`、`/chat`、`/items`、`/reminders`、`/contacts`、`/confirmations`、`/diagnose`；共享组件 `PageHeader`、`BaseModal`、`EmptyState`；接口统一走 `src/api.ts`（超时、错误、`X-Actor`、`URLSearchParams` 编码）。
- 阶段 3 验收：`npm run build` 通过；浏览器端到端走通首页、对话（`find_items`）、物品增删与过滤、提醒暂停、打电话记录、待确认两步流程。
- 沙箱限制：内置浏览器预览层会改写 URL 查询串，中文 `?q=` 在沙箱里会 400（curl 直连与经 Vite 均 200），中文搜索需在真实浏览器/平板复验。
- 云端**没有** Android SDK / adb / 真机；阶段 4 壳必须在本地 Trae（有 SDK + 真机）完成。
- 仓库已托管在 GitHub：`https://github.com/luuumity/homecare-agent`（`main` 分支，已推送阶段 0–3 全部代码）。后续每完成一个阶段都需 commit + push。
- 阶段 1–3 暂未加应用层鉴权（无账号体系），部署前在阶段 5 决定：优先 nginx Basic Auth / 平板端固定凭据，或后端 PIN 登录。上线前不要暴露到公网。

## 4. 本地 Trae 要做的 Android 壳（阶段 4）

产出目录 `shell/android/`，Kotlin，单个 Activity + WebView。

1. **工程**：`compileSdk 34`、`minSdk 26`、`targetSdk 33`（以真机实测为准）；包名建议 `com.family.eldercare.screen`；自签名 keystore 不提交仓库。
2. **WebView**：加载 `https://<域名>/`；开启 JS、DOM storage；同域 `/api` 走同一域名；`onPermissionRequest` 自动授予麦克风给本站；禁止外部链接跳出（拦截非本站 URL）。
3. **Kiosk**：全屏沉浸、隐藏导航栏、屏幕常亮（`FLAG_KEEP_SCREEN_ON`）、固定方向（按实际摆放）、拦截返回键（首页时回到首页而非退出）、崩溃自动重启 Activity。
4. **开机自启**：监听 `BOOT_COMPLETED`；Android 10+ 后台启动 Activity 受限，需在华为「应用启动管理」里允许自启动，首次由家人手动打开并授权（写入设置引导）。
5. **语音桥**：`addJavascriptInterface` 或 WebMessage 暴露：
   - `speech.asrStart()` / `asrStop()`：HMS ML Kit 短语音识别（≤60s），返回文本给 Web；无 HMS 时回退系统 `SpeechRecognizer`。
   - `speech.ttsSpeak(text)` / `ttsStop()`：HMS TTS；说话前先 `stop`。
   - 唤醒：先做「常驻大按钮 / BLE 按钮」触发；再评估 sherpa-onnx 离线唤醒词（4.0 上比 HMS 端侧方案可行）。
6. **版本与更新**：启动读取 `/api/version`，与 `BuildConfig.SHELL_VERSION` 比对 `min_shell_version`；低于则显示家属可见提示，下载同域 `/download/app.apk`，调起系统安装（`REQUEST_INSTALL_PACKAGES`，需家人点确认）。同步更新 `shell/version.json`。
7. **可维护性**：崩溃与关键日志本地落盘；预留上报接口（阶段 5 定）；WebView 远程调试仅在 debug 包开启。
8. **交付**：APK、签名/安装说明、真机验收记录，回填本文件。

设备侧必须验证：麦克风授权链路、TTS 平板是否可用（离线 TTS 平板不可用，需在线方案）、息屏/唤醒、断网重连、WebView 长时间驻留内存。

## 5. 壳与云端的接口约定

- `GET /api/version` → `{ "app_version", "api_version", "min_shell_version" }`
- `GET /api/health` → 服务状态
- `GET /api/v1/contacts` → 外呼白名单；`POST /api/v1/calls` → 记录外呼结果（服务端存脱敏号码）
- 页面：`https://<域名>/`；诊断页：`https://<域名>/diagnose`
- 阶段 3 起前端为单页应用，路由 `/`、`/chat`、`/items`、`/reminders`、`/contacts`、`/confirmations`、`/diagnose`，nginx 需 `try_files $uri /index.html`；壳只加载 `/` 即可，站内跳转由前端路由处理
- 业务接口阶段 1 起统一 `/api/v1/...`
- 阶段 2 起对话走 `POST /api/v1/chat`（JSON `{ "text": "..." }`）；壳后续接 HMS ASR 时，把识别文本 POST 过去，把 `reply` 交给 TTS 即可，无需另开会话接口

## 6. 云端部署备忘（阶段 5）

- VPS：2C2G、Ubuntu 22.04/24.04 起步；域名 + HTTPS（Let's Encrypt）。中国大陆服务器需备案，境外可免。
- nginx：`/` → `frontend/dist` 静态（`try_files ... /index.html`）；`/api` → `127.0.0.1:8000`。
- 后端 systemd 运行 uvicorn；`.env` 权限 600，密钥只存在服务器。
- 备份：每日 `sqlite3 .backup` + 异地副本，保留 7/30 天；保留上一版本代码与前端产物以便回滚。
- 更新：前端 `rsync dist` 原子切换；后端 `git pull` + `pip install -r` + 重启；失败回滚上一版本。

## 7. 未决事项

- 家属二次确认（短信签名链接）暂缓，只留接口。
- 唤醒方案最终选型需真机对比（按钮 / sherpa-onnx / Porcupine）。
- 云厂商、域名、备案方式待定。
- 护士站是否可能开放 API，暂无结论。

## 8. 现阶段约束

- 按阶段推进，每阶段结束等用户确认，**不要一次生成全部业务代码**。
- 不伪造护士站通知、不伪造天气或任何真实数据。
- 不把手机号、身份证、详细住址等敏感信息发送给模型。
