package com.family.eldercare.screen

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent

/**
 * 系统语音识别：`ACTION_RECOGNIZE_SPEECH`。
 *
 * 华为平板自带识别面板，中文可用，不需要 AGC / HMS 依赖，适合先做真机验证。
 * 局限：识别界面由系统提供，字号不可控；部分机型首次使用会要求下载离线语音包。
 */
class SystemSpeechInput(private val activity: Activity) : SpeechInput {

    override val name: String = "system-recognizer"

    private var onResult: ((String) -> Unit)? = null
    private var onError: ((String) -> Unit)? = null

    override fun start(onResult: (String) -> Unit, onError: (String) -> Unit): Boolean {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "zh-CN")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "请说话")
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        if (intent.resolveActivity(activity.packageManager) == null) {
            return false
        }
        this.onResult = onResult
        this.onError = onError
        activity.startActivityForResult(intent, REQUEST_CODE)
        return true
    }

    override fun stop() {
        onResult = null
        onError = null
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != REQUEST_CODE) return false
        val result = onResult
        val error = onError
        onResult = null
        onError = null

        val text = data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()
            ?.trim()
            .orEmpty()

        when {
            resultCode != Activity.RESULT_OK -> error?.invoke("已取消语音输入")
            text.isEmpty() -> error?.invoke("没有听清，请再说一次")
            else -> result?.invoke(text)
        }
        return true
    }

    companion object {
        const val REQUEST_CODE = 2001
    }
}
