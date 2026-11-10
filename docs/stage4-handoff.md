# 阶段 4 交接文档：Android 壳

给在 MacBook 上使用本地 Trae / Android Studio 的人（家人或未来的自己）。

> 一句话：**工程骨架已经在云端写好并推到 GitHub，你只需要装 SDK、构建、装进平板、按清单验收。** HMS 语音是第二步，不在骨架里。

## 1. 边界：云端能做什么、不能做什么

| 能做 | 不能做 |
| --- | --- |
| 写 Kotlin / Gradle / Manifest / 文档 | 装 Android Studio（图形化、要管理员密码） |
| 推送到 GitHub 触发自动构建 | 连 USB、点平板上的"允许调试" |
| 提供 GitHub Actions 出 APK | 登录华为 AGC 拿 `agconnect-services.json` |
| 写验收清单与故障排查 | 真机上的全屏、语音、拨号、开机自启验收 |

## 2. 现状（2026-11-06）

已实现：

- `compileSdk 34` / `minSdk 26` / `targetSdk 33`，包名 `com.family.eldercare.screen`
- WebView 加载 `https://homecare.cinnamon.xin/`，开启 JS / DOM Storage / 数据库
- 站外链接拦截（不跳出大屏），站内跳转交给前端路由
- 断网或主页面加载失败 → 大号"网络连接不上 / 重试"页
- 全屏沉浸（隐藏状态栏导航栏）、屏幕常亮、返回键回首页而非退出
- 麦克风权限：仅授予本站来源（`onPermissionRequest` + 运行时权限）
- 开机自启（`BOOT_COMPLETED` + `MY_PACKAGE_REPLACED`）
- 版本检查：启动拉 `/api/version`，`SHELL_VERSION` 低于 `min_shell_version` 时顶部橙色横幅提示，点击走安装器
- JS 桥 `Shell`：`shellVersion()`、`serverUrl()`、`speak()`、`stopSpeaking()`、`startListening()`（占位）、`stopListening()`、`callNumber()`、`openUpdate()`
- 崩溃后尝试自动重启 Activity（尽力而为，不保证所有场景）

未实现（第二步）：

- HMS ML Kit / 系统 `SpeechRecognizer` 的 ASR
- 提醒弹窗与系统通知
- Kiosk 锁定任务模式（LockTask）与设备所有者（DPC）
- 崩溃日志落盘与上报
- 正式签名与 `versionCode` 递增流程固化

## 3. 环境准备（MacBook）

1. 磁盘预留 **20 GB**（不装模拟器；若装模拟器需 30 GB+）
2. 安装 **Android Studio**（自带 JDK 17、SDK Manager、adb）
3. SDK Manager 里勾选：
   - `Android 14.0 (API 34)` → SDK Platform
   - `Android SDK Build-Tools`（34.x）
   - `Android SDK Platform-Tools`
4. 不要装模拟器，直接用平板真机

## 4. 构建

```bash
git clone https://github.com/luuumity/homecare-agent.git
cd homecare-agent/shell/android
./gradlew assembleDebug
```

产物：`app/build/outputs/apk/debug/app-debug.apk`

首次构建会下载 Gradle 8.7 与 AGP 依赖，约几百 MB，之后走缓存。

也可以不装环境，用 GitHub Actions：

- 推送到 `main` 且改动位于 `shell/android/**` 时自动构建
- 或 Actions 页面手动 `workflow_dispatch`
- 下载产物 `homecare-shell-debug`

## 5. 安装到平板（华为 MatePad Air DBY2-W00，HarmonyOS 4.0）

### 平板设置

1. 设置 → 关于平板 → 连点"版本号"7 次，开启开发者模式
2. 设置 → 系统和更新 → 开发人员选项：
   - 打开 **USB 调试**
   - 打开 **"仅充电"模式下允许 ADB 调试**（部分机型）
3. 设置 → 系统和更新 → **纯净模式** → 关闭（否则会拦截侧载安装）
4. 用数据线连接 Mac，平板弹"允许 USB 调试吗？"→ 勾选"始终允许"→ 确定

### 安装

```bash
adb devices                 # 确认设备已授权
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

覆盖安装报 `INSTALL_FAILED_UPDATE_INCOMPATIBLE` 时：先 `adb uninstall com.family.eldercare.screen` 再装（**数据在服务端，卸载不丢**）。

### 首次打开后必须做的华为设置

- 设置 → 应用 → 应用启动管理 → 找到"陪伴大屏"→ 关闭"自动管理"，勾选**允许自启动 / 允许关联启动 / 允许后台活动**
- 设置 → 电池 → 关闭对本应用的智能省电限制
- 首次进网页会弹麦克风授权（给页面用），选"允许"

## 6. 版本与更新

| 位置 | 字段 | 当前值 |
| --- | --- | --- |
| `app/build.gradle.kts` | `versionCode` | 1 |
| 同上 | `versionName` / `SHELL_VERSION` | 0.1.0 |
| `shell/version.json` | `shell_version` | 0.1.0 |
| 服务器 `.env` | `MIN_SHELL_VERSION` | 0.1.0 |

发新壳时：`versionCode +1`、`versionName`/`SHELL_VERSION` 同步递增、`shell/version.json` 更新，需要强制升级才提高服务器 `MIN_SHELL_VERSION`。

更新通道（待补服务端）：

- APK 放在服务器 `/opt/homecare/web/download/app.apk`，nginx 增加 `location /download/`
- 壳检测到版本落后 → 顶栏提示 → 点击走 `Shell.openUpdate()` 调起安装器（需家人确认）

## 7. 签名

- **内测**：debug 签名即可，家人侧载
- **长期/上架**：生成 release keystore，**务必备份**，丢失后无法覆盖升级

```bash
keytool -genkeypair -v -keystore homecare-release.jks -alias homecare \
  -keyalg RSA -keysize 4096 -validity 10000
```

keystore 与密码**绝不提交仓库**（`.gitignore` 已排除 `*.jks` / `*.keystore`）。

## 8. 第二步：HMS 语音（可选，需要华为账号）

> 现状：语音链路已实现。默认用系统 `RecognizerIntent`，**不做任何 AGC 配置也能用**；HMS 只是可替换实现，开启方式与完整步骤见 [hms-asr-setup.md](./hms-asr-setup.md)。

1. 打开 AppGallery Connect，创建应用，包名填 `com.family.eldercare.screen`
2. 开通 ML Kit 语音识别
3. 下载 `agconnect-services.json`，放到 `app/` 目录（`.gitignore` 已排除，**不要提交**）
4. 构建时加 `-PhmsAsr=true`（依赖与源集由 `app/build.gradle.kts` 的条件开关控制，默认构建不受影响）
5. 识别结果由 `ShellBridge` 通过 `window.onShellAsrResult` 回传，HMS 启动失败会自动回退系统识别
6. TTS 注意：**平板不支持离线 TTS Full SDK**，只能用在线方案；每次朗读前先 `stop()` 防叠音

## 9. 网页侧配合（已完成）

- `frontend/src/shell.ts`：检测 `window.Shell`，封装 `speak` / `listen` / `callNumber`，无壳时安全降级
- 对话页：有壳时启用话筒按钮，识别结果填入输入框并自动发送；回复自动播报，可按下打断
- 打电话：壳内可用 `Shell.callNumber(phone)` 直接调起拨号盘；网页版仍只记录

## 10. 验收清单（真机）

- [ ] 安装后打开即全屏，无地址栏、无状态栏
- [ ] 输入 PIN `123321` 能进入首页，登录状态保留
- [ ] 断网 → 出现"网络连接不上"，恢复网络点重试能回到页面
- [ ] 返回键：有历史时后退，首页时停在首页，不退出应用
- [ ] 锁屏/亮屏后仍全屏，屏幕不会自动熄灭
- [ ] 重启平板后自动打开（华为启动管理设置正确时）
- [ ] 页面内的"打电话"能调起系统拨号盘（壳内），不直接拨出
- [ ] `SHELL_VERSION` 低于 `min_shell_version` 时顶栏出现橙色提示
- [ ] 连续停留 2 小时不崩、不白屏（观察 WebView 内存）
- [ ] 长按/误触不会跳出浏览器或应用市场

## 11. 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| `SDK location not found` | 用 Android Studio 打开工程同步一次，或建 `local.properties` 写 `sdk.dir=/Users/<你>/Library/Android/sdk` |
| `Unsupported class file major version` | Gradle 用了错误 JDK；Android Studio → Settings → Build Tools → Gradle → JDK 选 17 |
| 构建卡在下载 Gradle | 网络问题；重试或用 GitHub Actions 产物 |
| 白屏 | 先看平板系统时间是否正确（证书校验依赖时间）；再看 WebView 版本是否过旧（华为应用市场更新"Android System WebView"） |
| 无法开机自启 | 华为"应用启动管理"未允许；Android 10+ 后台启动 Activity 本身受限，属已知限制 |
| 纯净模式拦截安装 | 关闭纯净模式，或走 AppGallery Connect 内部测试通道 |
| 页面提示登录过期 | 30 天 Cookie 到期，重新输 PIN |

## 12. 与云端的接口约定

- 页面入口：`https://homecare.cinnamon.xin/`（壳只加载 `/`）
- 版本：`GET /api/version` → `{ app_version, api_version, min_shell_version }`
- 健康：`GET /api/health`
- 对话：`POST /api/v1/chat`，JSON `{ "text": "..." }`（ASR 识别文本直接 POST，`reply` 交 TTS）
- 通话记录：`POST /api/v1/calls`（服务端只存脱敏号码）
- 更新包：`https://homecare.cinnamon.xin/download/app.apk`（**服务端尚未配置，需补 nginx location 与文件**）
