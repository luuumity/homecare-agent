# 安卓语音链路：桥接契约、识别开关与 AGC 配置

面向 `shell/android` 的语音实现说明。目标是：**没有 AGC 配置也能构建、也能用语音**；有 AGC 配置时再切到 HMS ML Kit，且切换只改构建参数，不改代码。

## 1. 分层与文件

| 层 | 文件 | 职责 |
| --- | --- | --- |
| 网页桥 | `frontend/src/shell.ts` | 检测 `window.Shell`，封装 `speak` / `listen` / `callNumber`，无壳时安全降级 |
| 对话页 | `frontend/src/views/ChatView.vue` | 话筒按钮、正在听/正在说状态、结果自动上屏并发送、回复自动播报、可打断 |
| 原生桥 | `shell/android/app/src/main/java/.../ShellBridge.kt` | JS 接口、TTS、识别调度、结果回传网页 |
| 识别抽象 | `.../SpeechInput.kt` | `SpeechInput` 接口 + `SpeechInputFactory`（按开关选择实现） |
| 系统识别 | `.../SystemSpeechInput.kt` | `ACTION_RECOGNIZE_SPEECH`，默认路径 |
| HMS 识别 | `app/src/hms/java/.../asr/HmsSpeechInput.kt` | HMS ML Kit 插件式识别，**只在开关打开时参与编译** |
| 构建开关 | `app/build.gradle.kts` | `hmsAsr` 属性 → `BuildConfig.HMS_ASR_ENABLED` + 可选源集/依赖 |

## 2. JS 契约（Android 与将来的鸿蒙保持一致）

原生注入对象名固定为 `window.Shell`：

| 方法 | 说明 |
| --- | --- |
| `shellVersion(): string` | 壳版本 |
| `serverUrl(): string` | 服务端地址 |
| `speak(text): void` | 播报，先停掉上一次 |
| `stopSpeaking(): void` | 立即停止播报 |
| `startListening(): boolean` | 开始识别；`false` 表示本机不可用 |
| `stopListening(): void` | 取消识别 |
| `callNumber(phone): void` | 打开拨号盘（只带号码） |
| `openUpdate(url): void` | 下载并安装 APK |

原生 → 网页的回调：

| 回调 | 说明 |
| --- | --- |
| `window.onShellAsrResult(text)` | 识别成功 |
| `window.onShellAsrError(message)` | 失败/取消/超时 |
| `window.onShellSpeakState('start' \| 'done')` | 播报开始/结束（驱动「正在说」状态） |

网页侧 `listen()` 是 Promise，默认 60 秒超时；超时或取消会 reject，`ChatView` 负责提示。

## 3. 默认路径：系统识别（无需任何配置）

- 实现：`SystemSpeechInput`，`RecognizerIntent.ACTION_RECOGNIZE_SPEECH`，`zh-CN`。
- 华为平板自带识别面板，**不需要 AGC、不需要华为账号、不引入任何依赖**。
- 局限：识别界面是系统提供的，字号不可控；部分机型首次使用要求下载离线语音包；离线时可能不可用。

真机验证时看日志（Tag `HomecareShell`）：

```
语音识别已启动：system-recognizer
```

## 4. 切换到 HMS ML Kit

### 4.1 构建开关

命令行：

```bash
cd shell/android
./gradlew assembleDebug -PhmsAsr=true
```

或写进 `~/.gradle/gradle.properties`（不要提交到仓库）：

```properties
hmsAsr=true
```

开启后：`BuildConfig.HMS_ASR_ENABLED=true`，`app/src/hms/java` 加入源集，并引入 `com.huawei.hms:ml-computer-voice-asr-plugin:3.11.0.301`。不传该参数时，这些全部不参与构建。

### 4.2 AGC（AppGallery Connect）操作步骤

1. 用华为开发者账号登录 [AppGallery Connect](https://developer.huawei.com/consumer/cn/service/josp/agc/index.html)，创建**项目**，在项目下添加**应用**：
   - 平台：Android
   - 包名：`com.family.eldercare.screen`（必须与 `applicationId` 完全一致）
2. 填签名证书指纹：在「项目设置 → 常规 → SHA-256 证书指纹」中填入实际签名证书的 SHA-256。
   - debug 包可用 `keytool` 读取本机 debug keystore：
     ```bash
     keytool -list -v -keystore ~/.android/debug.keystore \
       -alias androiddebugkey -storepass android -keypass android
     ```
   - 正式包用你自己的 release keystore，命令同上，换路径与别名。
3. 在 AGC 左侧「构建 → ML Kit」中开通/启用 **语音识别（ASR）**（若界面要求先开通 ML Kit 总开关，一并开启）。
4. 在「项目设置 → 常规 → 应用信息」下载 **`agconnect-services.json`**，放到：

   ```
   shell/android/app/agconnect-services.json
   ```

   该文件含应用密钥，**不要提交仓库**（见 `.gitignore`）；换机器/换签名指纹后需要重新下载。
5. 重新构建（带 `-PhmsAsr=true`）并安装。

### 4.3 关于 AGCP 插件

当前工程**刻意没有引入** `com.huawei.agconnect` 插件，原因是你要求「缺 AGC 配置时构建必须成立」。

后果：`agconnect-services.json` 不会被 AGCP 自动注入。如果 HMS 插件在运行时提示初始化失败（日志 Tag `HomecareShell` 会有记录），再按官方文档给 `app/build.gradle.kts` 加 AGCP 插件与对应 classpath，并**只在 `hmsAsr` 打开时启用**。这一步属于 HMS 路径的收尾，不影响默认构建与系统识别。

### 4.4 运行时回退

- `SpeechInputFactory`：开关打开但类不存在/依赖缺失 → 记日志，回退系统识别。
- `ShellBridge.startListening()`：HMS 启动抛异常或返回 false → 记日志，立即改用系统识别。
- 两条都失败才向网页返回「这台平板暂时用不了语音识别」。

日志示例：

```
HMS 语音识别不可用（缺少依赖或 AGC 配置），回退系统识别
语音识别已启动：hms-mlkit
```

## 5. 真机验收清单

1. **网页版**（浏览器直接打开）：话筒显示「待壳」且不可点；对话、播报都不触发原生。
2. **平板壳内**：话筒可点 → 弹出识别面板 → 说「我的老花镜放在哪里」→ 文本自动填入输入框并自动发送 → 回复自动朗读。
3. **播报态**：朗读时按钮显示「正在说」，按一下立即停止。
4. **取消**：识别中再按一下话筒，应取消且不报错。
5. **拒绝麦克风权限**：应给出提示，不崩溃。
6. **断网**：识别可能不可用，应有提示；不建议在断网时做验收。
7. **日志**：确认实际生效的实现（`system-recognizer` / `hms-mlkit`）。

## 6. 已知限制与未验证项

- **未编译验证**：当前开发机缺 JDK 17 与 Android SDK，改动只做了代码级检查；首次构建请以 Gradle 输出为准。
- HMS 插件 intent 的 extra 常量（`MLAsrConstants.LANGUAGE` / `FEATURE_WORDFLUX` / `RESULTS_RECOGNIZED` 等）随 SDK 版本可能变化，升级依赖时需对照官方文档核对。
- 识别 UI 由系统/HMS 提供，字号不可控，老人是否看得清需要真机判断。
- 唤醒词未实现；当前是「按一下话筒」触发。
- 识别结果只取第一条，不做多候选。
