package com.family.eldercare.screen

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * 开机自启。注意：Android 10+ 限制后台启动 Activity，
 * 华为设备还需在「设置 → 应用启动管理」里允许本应用自启动，见 docs/stage4-handoff.md。
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        if (action != Intent.ACTION_BOOT_COMPLETED && action != Intent.ACTION_MY_PACKAGE_REPLACED) {
            return
        }
        val launch = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        try {
            context.startActivity(launch)
        } catch (e: Exception) {
            Log.w("HomecareShell", "开机自启失败，需要家人手动打开一次", e)
        }
    }
}
