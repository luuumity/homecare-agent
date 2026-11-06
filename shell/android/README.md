# Android 壳（阶段 4）

薄壳：`Activity + WebView`，业务页面全部由服务端下发，壳只负责原生能力。

## 现状

- ✅ 工程骨架（Gradle 8.7 / AGP 8.5.2 / Kotlin 1.9.24 / compileSdk 34 / minSdk 26 / targetSdk 33）
- ✅ WebView 加载 `https://homecare.cinnamon.xin/`，站外链接拦截，断网显示重试页
- ✅ 全屏沉浸、屏幕常亮、返回键回首页、麦克风权限授予本站
- ✅ 开机自启（`BOOT_COMPLETED`）
- ✅ 版本检查（对比 `/api/version` 的 `min_shell_version`）
- ✅ JS 桥 `Shell`（版本、TTS 朗读、打开拨号盘、安装更新、语音识别占位）
- ⏳ 尚未接入 HMS ASR、未做通知、未做真机验收

**本地构建与真机安装步骤见 [docs/stage4-handoff.md](../../docs/stage4-handoff.md)。**

## 快速构建

```bash
cd shell/android
./gradlew assembleDebug
# 产物：app/build/outputs/apk/debug/app-debug.apk
```

## 修改服务端地址

`app/build.gradle.kts` 中的 `SERVER_URL`：

```kotlin
buildConfigField("String", "SERVER_URL", "\"https://homecare.cinnamon.xin/\"")
```

## 版本对齐

`SHELL_VERSION`（`app/build.gradle.kts`）、`versionName`、`versionCode` 与根目录 `shell/version.json`、后端 `MIN_SHELL_VERSION` 保持一致。
