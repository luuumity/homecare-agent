package com.family.eldercare.screen

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.speech.tts.TextToSpeech
import android.webkit.JavascriptInterface
import android.widget.Toast
import java.util.Locale

/**
 * 暴露给网页的 JavaScript 接口，名字固定为 `Shell`：
 *
 *   Shell.shellVersion()       壳版本
 *   Shell.serverUrl()          当前服务端地址
 *   Shell.speak(text)          系统 TTS 朗读（先停上一次，避免叠音）
 *   Shell.stopSpeaking()       停止朗读
 *   Shell.startListening()     语音识别（占位，阶段 4 第二步接 HMS ML Kit）
 *   Shell.stopListening()      停止识别
 *   Shell.callNumber(phone)    打开系统拨号盘（不直接拨出，无需 CALL_PHONE）
 *   Shell.openUpdate(url)      下载 APK 并调起安装器
 */
class ShellBridge(private val activity: Activity) {

    private var tts: TextToSpeech? = null
    private var ttsReady = false

    init {
        tts = TextToSpeech(activity) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                tts?.language = Locale.SIMPLIFIED_CHINESE
            }
        }
    }

    @JavascriptInterface
    fun shellVersion(): String = BuildConfig.SHELL_VERSION

    @JavascriptInterface
    fun serverUrl(): String = BuildConfig.SERVER_URL

    @JavascriptInterface
    fun speak(text: String) {
        if (text.isBlank()) return
        activity.runOnUiThread {
            val engine = tts
            if (engine == null || !ttsReady) return@runOnUiThread
            engine.stop()
            engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, "homecare")
        }
    }

    @JavascriptInterface
    fun stopSpeaking() {
        activity.runOnUiThread { tts?.stop() }
    }

    @JavascriptInterface
    fun startListening(): Boolean {
        // TODO(阶段 4 第二步)：接入 HMS ML Kit 短语音识别，识别结果通过
        // webView.evaluateJavascript("window.onShellAsrResult && onShellAsrResult('...')", null) 回传。
        activity.runOnUiThread {
            Toast.makeText(activity, "语音识别尚未接入", Toast.LENGTH_SHORT).show()
        }
        return false
    }

    @JavascriptInterface
    fun stopListening() {
        // 与 startListening 一并实现
    }

    @JavascriptInterface
    fun callNumber(phone: String) {
        activity.runOnUiThread {
            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(phone)))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            activity.startActivity(intent)
        }
    }

    @JavascriptInterface
    fun openUpdate(url: String) {
        activity.runOnUiThread {
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(Uri.parse(url), "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            activity.startActivity(intent)
        }
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
    }
}
