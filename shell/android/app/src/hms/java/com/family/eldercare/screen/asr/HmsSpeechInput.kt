package com.family.eldercare.screen.asr

import android.app.Activity
import android.content.Intent
import android.util.Log
import com.family.eldercare.screen.SpeechInput
import com.huawei.hms.mlplugin.asr.MLAsrCaptureActivity
import com.huawei.hms.mlsdk.asr.MLAsrConstants

/**
 * HMS ML Kit 语音识别（插件式 UI）。
 *
 * 只有构建时加 `-PhmsAsr=true` 才会编译本文件并引入 `ml-computer-voice-asr-plugin`；
 * 默认构建不依赖华为仓库，也不会因为没有 `agconnect-services.json` 而失败。
 *
 * 运行前提（详见 docs/hms-asr-setup.md）：
 *   1. AGC 建应用、包名 com.family.eldercare.screen、填签名指纹
 *   2. 开通 ML Kit 语音识别，下载 agconnect-services.json 放到 app/ 目录
 *   3. 用 -PhmsAsr=true 构建
 *
 * 注意：插件 intent 的 extra 常量随 SDK 版本可能调整，升级 SDK 时请对照官方文档核对；
 * 若运行时初始化失败（常见于缺少 AGC 配置），start() 会抛异常，桥会自动回退系统识别。
 */
class HmsSpeechInput(private val activity: Activity) : SpeechInput {

    override val name: String = "hms-mlkit"

    private var onResult: ((String) -> Unit)? = null
    private var onError: ((String) -> Unit)? = null

    override fun start(onResult: (String) -> Unit, onError: (String) -> Unit): Boolean {
        val intent = Intent(activity, MLAsrCaptureActivity::class.java).apply {
            putExtra(MLAsrConstants.LANGUAGE, "zh-CN")
            putExtra(MLAsrConstants.FEATURE_WORDFLUX, MLAsrConstants.FEATURE_WORDFLUX_ASR_CAPTURE)
            putExtra(MLAsrConstants.ENABLE_PUNCTUATION, true)
        }
        this.onResult = onResult
        this.onError = onError
        return try {
            activity.startActivityForResult(intent, REQUEST_CODE)
            true
        } catch (t: Throwable) {
            Log.e(TAG, "HMS 语音识别启动失败，请检查 AGC 配置与依赖", t)
            this.onResult = null
            this.onError = null
            false
        }
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
            ?.getStringArrayListExtra(MLAsrConstants.RESULTS_RECOGNIZED)
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
        private const val TAG = "HomecareShell"
        const val REQUEST_CODE = 2002
    }
}
