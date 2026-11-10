# 更新日志

按时间倒序记录。应用版本号以 `backend/app/config.py` 的 `APP_VERSION` 为准，前端 `frontend/package.json` 与 `frontend/public/version.json` 跟随同步。

## 0.5.0-stage5 — 2026-11-10

- 统一登录 PIN 默认值为 `123321`：`backend/app/config.py`、`backend/.env.example`、`docs/stage4-handoff.md` 一致（以提交 `9d8ad38` 为准）。
- 应用版本号由 `0.4.0-stage3` 统一为 `0.5.0-stage5`（后端配置与 `.env.example`、前端 `package.json`、`public/version.json`），`min_shell_version` 保持 `0.1.0` 不变。
- 新增本文件；README / HANDOFF 的版本、PIN 与阶段状态表述与现状对齐。

## 0.4.0-stage3 — 2026-11-01

- 阶段 3：大屏 Web UI 完成，路由 `/`、`/chat`、`/items`、`/reminders`、`/contacts`、`/confirmations`、`/diagnose`。
- 阶段 5 初版部署：`https://homecare.cinnamon.xin`（HTTPS、页面内 PIN 登录、每日备份、systemd + nginx）。
- 2026-11-06：阶段 4 Android 壳工程骨架（`shell/android/`）与 GitHub Actions 出包，待真机验收。

## 阶段 0–2 — 2026-10-31 及以前

- 阶段 0：前后端骨架、SQLite/FTS5 探针、`/api/health`、`/api/version`、`/api/diagnose`。
- 阶段 1：schema v1 全部业务表、`/api/v1` 接口、审计与软删除、医疗/身份记忆双确认。
- 阶段 2：Agent 对话编排（工具循环、隐私脱敏、记忆检索、上下文压缩），`POST /api/v1/chat`。
