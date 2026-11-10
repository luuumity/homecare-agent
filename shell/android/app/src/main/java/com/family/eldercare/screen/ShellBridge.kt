package com.family.eldercare.screen

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject
import java.util.Locale

/**
 * 暴露给网页的 JavaScript 接口，名字固定为 `Shell`：
 *
 *   Shell.shellVersion()       壳版本
 *   Shell.serverUrl()          当前服务端地址
 *   Shell.speak(text)          系统 TTS 朗读（先停上一次，避免叠音）
 *   Shell.stopSpeaking()       停止朗读
 *   Shell.startListening()     开始语音识别，返回 false 表示本机不可用
 *   Shell.stopListening()      取消识别
 *   Shell.callNumber(phone)    打开系统拨号盘（不直接拨出，无需 CALL_PHONE）
 *   Shell.openUpdate(url)      下载 APK 并调起安装器
 *
 * 识别结果通过网页全局回调回传（见 frontend/src/shell.ts）：
 *   window.onShellAsrResult(text) / window.onShellAsrError(message)
 * 播报状态：window.onShellSpeakState('start' | 'done')
 */
class ShellBridge(
    private val activity: Activity,
    private val webView: WebView,
    private val speechInput: SpeechInput = SpeechInputFactory.create(activity),
    private val fallbackSpeechInput: SpeechInput = SystemSpeechInput(activity),
) {

    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var listening = false

    init {
        tts = TextToSpeech(activity) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                tts?.language = Locale.SIMPLIFIED_CHINESE
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) = notifySpeakState("start")

                    override fun onDone(utteranceId: String?) = notifySpeakState("done")

                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) = notifySpeakState("done")

                    override fun onError(utteranceId: String?, errorCode: Int) =
                        notifySpeakState("done")
                })
            } else {
                Log.w(TAG, "系统 TTS 初始化失败，播报不可用")
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

    // ---------------------------------------------------------------- 语音识别

    @JavascriptInterface
    fun startListening(): Boolean {
        if (listening) return false
        // JS 接口运行在 JavaBridge 线程，启动 Activity 必须回主线程
        listening = true
        activity.runOnUiThread { startListeningOnUiThread() }
        return true
    }

    private fun startListeningOnUiThread() {
        if (!listening) return

        val started = runCatching {
            speechInput.start(
                onResult = { text -> finishListening(text, null) },
                onError = { message -> finishListening(null, message) },
            )
        }.getOrElse { throwable ->
            Log.w(TAG, "语音识别（${speechInput.name}）启动异常，回退系统识别", throwable)
            false
        }

        if (started) {
            Log.i(TAG, "语音识别已启动：${speechInput.name}")
            return
        }

        if (speechInput !== fallbackSpeechInput) {
            Log.w(TAG, "${speechInput.name} 不可用，改用 ${fallbackSpeechInput.name}")
            val fallbackStarted = runCatching {
                fallbackSpeechInput.start(
                    onResult = { text -> finishListening(text, null) },
                    onError = { message -> finishListening(null, message) },
                )
            }.getOrDefault(false)
            if (fallbackStarted) {
                Log.i(TAG, "语音识别已启动：${fallbackSpeechInput.name}")
                return
            }
        }

        finishListening(null, "这台平板暂时用不了语音识别")
    }

    @JavascriptInterface
    fun stopListening() {
        if (!listening) return
        listening = false
        speechInput.stop()
        fallbackSpeechInput.stop()
    }

    /** 由 MainActivity.onActivityResult 转发；返回 true 表示已处理。 */
    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        val handled = speechInput.onActivityResult(requestCode, resultCode, data) ||
            fallbackSpeechInput.onActivityResult(requestCode, resultCode, data)
        if (handled) listening = false
        return handled
    }

    private fun finishListening(text: String?, error: String?) {
        listening = false
        if (text != null) {
            notifyJs("window.onShellAsrResult && window.onShellAsrResult(${JSONObject.quote(text)})")
        } else {
            notifyJs("window.onShellAsrError && window.onShellAsrError(${JSONObject.quote(error ?: "语音识别失败")})")
        }
    }

    private fun notifySpeakState(state: String) {
        notifyJs("window.onShellSpeakState && window.onShellSpeakState('$state')")
    }

    private fun notifyJs(script: String) {
        webView.post { webView.evaluateJavascript(script, null) }
    }

    // ---------------------------------------------------------------- 拨号 / 更新

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
        listening = false
        speechInput.stop()
        fallbackSpeechInput.stop()
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
    }

    companion object {
        private const val TAG = "HomecareShell"
    }
}
