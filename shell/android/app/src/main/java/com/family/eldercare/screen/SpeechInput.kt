package com.family.eldercare.screen

import android.app.Activity
import android.content.Intent
import android.util.Log

/**
 * 语音识别的一层可替换抽象。
 *
 * 默认实现是系统 `RecognizerIntent`（华为平板自带，无需任何 AGC 配置）；
 * HMS ML Kit 实现放在 `src/hms/java`，只有构建时加 `-PhmsAsr=true` 才会编译进来。
 */
interface SpeechInput {
    /** 用于日志区分实际生效的实现。 */
    val name: String

    /**
     * 开始一次识别。返回 false 表示本机没有可用实现（此时桥会明确报错）。
     * 结果通过回调异步返回，回调只应触发一次。
     */
    fun start(onResult: (String) -> Unit, onError: (String) -> Unit): Boolean

    /** 结束当前识别；实现要保证之后的回调不会再触发。 */
    fun stop()

    /** 由 Activity 转发；返回 true 表示这个 requestCode 属于本实现。 */
    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean = false
}

object SpeechInputFactory {

    private const val TAG = "HomecareShell"

    /**
     * 选择实现：开关打开且类存在才用 HMS，否则一律回退系统识别。
     * 这样没有 `agconnect-services.json` 时构建和运行都不受影响。
     */
    fun create(activity: Activity): SpeechInput {
        if (!BuildConfig.HMS_ASR_ENABLED) return SystemSpeechInput(activity)
        return try {
            val clazz = Class.forName("com.family.eldercare.screen.asr.HmsSpeechInput")
            clazz.getConstructor(Activity::class.java)
                .newInstance(activity) as SpeechInput
        } catch (t: Throwable) {
            Log.w(TAG, "HMS 语音识别不可用（缺少依赖或 AGC 配置），回退系统识别", t)
            SystemSpeechInput(activity)
        }
    }
}
