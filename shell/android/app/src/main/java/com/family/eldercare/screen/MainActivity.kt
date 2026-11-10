package com.family.eldercare.screen

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.TextView
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/**
 * 单 Activity + WebView 的薄壳：
 * - 全屏沉浸、屏幕常亮、返回键回到首页而非退出
 * - 只允许停留在本站，站外链接一律拦截
 * - 页面加载失败时显示大号「网络连接不上 / 重试」
 * - 启动时比对 /api/version 的 min_shell_version，落后则顶部提示家属安装新版
 * - 崩溃后尝试自动重启
 */
class MainActivity : Activity() {

    private lateinit var webView: WebView
    private lateinit var errorView: View
    private lateinit var errorText: TextView
    private lateinit var updateBanner: TextView
    private lateinit var bridge: ShellBridge

    private val handler = Handler(Looper.getMainLooper())
    private val executor = Executors.newSingleThreadExecutor()
    private val homeHost: String by lazy { Uri.parse(BuildConfig.SERVER_URL).host ?: "" }
    private var pendingPermission: PermissionRequest? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        webView = findViewById(R.id.web_view)
        errorView = findViewById(R.id.error_view)
        errorText = findViewById(R.id.error_text)
        updateBanner = findViewById(R.id.update_banner)
        findViewById<Button>(R.id.retry_button).setOnClickListener { reload() }

        bridge = ShellBridge(this, webView)
        configureWebView()
        enterImmersive()
        installCrashRestart()
        checkMinShellVersion()

        webView.loadUrl(BuildConfig.SERVER_URL)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enterImmersive()
    }

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else webView.loadUrl(BuildConfig.SERVER_URL)
    }

    override fun onDestroy() {
        bridge.shutdown()
        executor.shutdownNow()
        webView.destroy()
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (bridge.onActivityResult(requestCode, resultCode, data)) return
        super.onActivityResult(requestCode, resultCode, data)
    }

    // ---------------------------------------------------------------- WebView

    @SuppressLint("SetJavaScriptEnabled")
    private fun configureWebView() {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            allowFileAccess = false
            allowContentAccess = false
            setSupportZoom(false)
            builtInZoomControls = false
            userAgentString = userAgentString + " HomecareShell/" + BuildConfig.SHELL_VERSION
        }
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        webView.setBackgroundColor(Color.parseColor("#FBF5EA"))
        webView.addJavascriptInterface(bridge, "Shell")

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?,
            ): Boolean {
                val url = request?.url ?: return false
                // 站内跳转交给前端路由；站外一律拦截，避免跳出大屏应用
                return if (url.host == homeHost) false else true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                errorView.visibility = View.GONE
                webView.visibility = View.VISIBLE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                if (request?.isForMainFrame == true) {
                    showNetworkError(error?.description?.toString() ?: getString(R.string.offline_hint))
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest?) {
                val req = request ?: return
                if (req.origin?.host != homeHost) {
                    req.deny()
                    return
                }
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                    req.grant(req.resources)
                } else {
                    pendingPermission = req
                    requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQUEST_MIC)
                }
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQUEST_MIC) return
        val req = pendingPermission
        pendingPermission = null
        if (req == null) return
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            req.grant(req.resources)
        } else {
            req.deny()
        }
    }

    private fun reload() {
        errorView.visibility = View.GONE
        webView.visibility = View.VISIBLE
        webView.loadUrl(BuildConfig.SERVER_URL)
    }

    private fun showNetworkError(detail: String) {
        errorText.text = detail
        webView.visibility = View.GONE
        errorView.visibility = View.VISIBLE
    }

    // ---------------------------------------------------------------- Kiosk

    private fun enterImmersive() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.apply {
                hide(WindowInsets.Type.systemBars())
                systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    or View.SYSTEM_UI_FLAG_FULLSCREEN
                    or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                )
        }
    }

    // ---------------------------------------------------------------- 版本检查

    private fun checkMinShellVersion() {
        executor.execute {
            var minVersion: String? = null
            try {
                val url = URL(BuildConfig.SERVER_URL.trimEnd('/') + "/api/version")
                val conn = url.openConnection() as HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                conn.requestMethod = "GET"
                conn.setRequestProperty("Accept", "application/json")
                if (conn.responseCode == HttpURLConnection.HTTP_OK) {
                    val body = conn.inputStream.bufferedReader().use { it.readText() }
                    minVersion = JSONObject(body).optString("min_shell_version", "")
                }
                conn.disconnect()
            } catch (e: Exception) {
                Log.w(TAG, "版本检查失败", e)
            }

            val remote = minVersion
            handler.post {
                if (remote.isNullOrBlank()) return@post
                if (compareVersions(BuildConfig.SHELL_VERSION, remote) < 0) {
                    updateBanner.text = getString(R.string.update_required, remote)
                    updateBanner.visibility = View.VISIBLE
                    updateBanner.setOnClickListener {
                        bridge.openUpdate(
                            BuildConfig.SERVER_URL.trimEnd('/') + "/download/app.apk"
                        )
                    }
                }
            }
        }
    }

    private fun compareVersions(current: String, expected: String): Int {
        val a = current.split(".").mapNotNull { it.toIntOrNull() }
        val b = expected.split(".").mapNotNull { it.toIntOrNull() }
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return if (x < y) -1 else 1
        }
        return 0
    }

    // ---------------------------------------------------------------- 崩溃自启

    private fun installCrashRestart() {
        Thread.setDefaultUncaughtExceptionHandler { _, throwable ->
            Log.e(TAG, "未捕获异常，尝试重启", throwable)
            try {
                val intent = Intent(this, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                }
                startActivity(intent)
            } catch (e: Exception) {
                Log.w(TAG, "崩溃后重启失败", e)
            }
            handler.postDelayed({
                android.os.Process.killProcess(android.os.Process.myPid())
            }, 800)
            Thread.sleep(1000)
        }
    }

    companion object {
        private const val TAG = "HomecareShell"
        private const val REQUEST_MIC = 1001
    }
}
