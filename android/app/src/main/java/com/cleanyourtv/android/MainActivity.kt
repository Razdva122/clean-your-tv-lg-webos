package com.cleanyourtv.android

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.*
import android.webkit.*
import android.widget.FrameLayout
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.File
import java.util.UUID

class MainActivity : Activity() {
    private lateinit var web: WebView
    private val ui = Handler(Looper.getMainLooper())
    @Volatile private var inspecting = false
    private val entry = "file:///android_asset/ui/index.html"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val frame = FrameLayout(this)
        frame.setBackgroundColor(Color.rgb(29, 28, 26))
        web = WebView(this)
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        frame.addView(web)
        setContentView(frame)
        if (Build.VERSION.SDK_INT >= 30) window.setDecorFitsSystemWindows(false)
        if (Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(0) {
                web.evaluateJavascript("window.goBack && window.goBack()", null)
            }
        }
        frame.setOnApplyWindowInsetsListener { view, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.ime())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            }
            insets
        }
        web.setBackgroundColor(Color.rgb(29, 28, 26))
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        }
        web.addJavascriptInterface(Bridge(), "CYTV")
        web.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                // Android 7 can have an old, never-updated WebView. Show a useful
                // native message instead of leaving a blank page on syntax errors.
                web.evaluateJavascript("typeof Array.prototype.at === 'function' && typeof HTMLDialogElement !== 'undefined' && typeof CSS !== 'undefined' && CSS.supports('height', '100dvh')") { supported ->
                    if (supported != "true" && !isDestroyed) {
                        android.app.AlertDialog.Builder(this@MainActivity)
                            .setTitle("CYTV / WebView")
                            .setMessage(getString(R.string.webview_update))
                            .setPositiveButton("OK") { _, _ -> finish() }
                            .setCancelable(false).show()
                    }
                }
            }
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean = request?.url.toString() != entry
            override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse? {
                val url = request?.url.toString()
                if (url.startsWith("file:///android_asset/ui/")) return null
                return WebResourceResponse("text/plain", "utf-8", ByteArrayInputStream(ByteArray(0)))
            }
        }
        web.loadUrl(entry)
        Operation.listener = { event -> ui.post { emit(event) } }
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 7)
        }
    }

    private fun emit(event: String) {
        web.evaluateJavascript("window.receiveNative && window.receiveNative($event)", null)
    }

    inner class Bridge {
        @JavascriptInterface fun inspect(config: String) {
            synchronized(this@MainActivity) {
                if (inspecting || Operation.active) return
                inspecting = true
            }
            Thread({
                try {
                    require(config.length <= 4096)
                    if (!com.chaquo.python.Python.isStarted()) {
                        com.chaquo.python.Python.start(com.chaquo.python.android.AndroidPlatform(this@MainActivity))
                    }
                    val event = com.chaquo.python.Python.getInstance().getModule("android_bridge")
                        .callAttr("inspect_connection", config).toString()
                    ui.post { if (!isDestroyed) emit(event) }
                } catch (_: Exception) {
                    val host = try { JSONObject(config).optString("host") } catch (_: Exception) { "" }
                    val event = JSONObject().put("kind", "inspection").put("host", host)
                        .put("root_ssh", false).put("developer_ssh", false).put("root_port", 22).toString()
                    ui.post { if (!isDestroyed) emit(event) }
                } finally { inspecting = false }
            }, "cytv-inspect").start()
        }
        @JavascriptInterface fun snapshot(): String = Operation.snapshot()
        @JavascriptInterface fun hasKey(): Boolean = File(getSharedPreferences("private", MODE_PRIVATE).getString("identity", "") ?: "").isFile
        @JavascriptInterface fun start(config: String) {
            if (Operation.active) return
            // Limit and rebuild input; no filesystem paths or secrets cross this bridge.
            try {
                require(config.length <= 4096)
                val raw = JSONObject(config)
                val clean = JSONObject()
                for (key in arrayOf("host", "edition", "port", "language", "action", "useImportedKey", "connection", "root_variant")) {
                    if (raw.has(key)) clean.put(key, raw.get(key))
                }
                require(clean.optString("action") in arrayOf("install", "status", "doctor", "home-diagnostics", "recover", "restore", "uninstall"))
                ui.post {
                    val intent = Intent(this@MainActivity, InstallerService::class.java).putExtra("config", clean.toString())
                    if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent) else startService(intent)
                }
            } catch (_: Exception) { ui.post { emit("{\"kind\":\"error\",\"text\":\"Invalid request\"}") } }
        }
        @JavascriptInterface fun saveReport() {
            if (!Operation.active) ui.post {
                val report = diagnosticReport() ?: return@post
                startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "application/json"
                    putExtra(Intent.EXTRA_TITLE, report.name)
                }, 9)
            }
        }
        @JavascriptInterface fun answer(json: String) {
            val answer = JSONObject(json)
            Operation.answer(answer.getString("id"), if (answer.isNull("value")) null else answer.getString("value"))
        }
        @JavascriptInterface fun importKey() {
            if (!Operation.active) ui.post {
                startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "*/*"
                }, 8)
            }
        }
    }

    private fun diagnosticReport(): File? {
        val events = JSONArray(Operation.snapshot())
        for (i in events.length() - 1 downTo 0) {
            val event = JSONObject(events.getString(i))
            if (event.optString("kind") != "report-ready") continue
            val name = event.optString("name")
            if (!Regex("diagnostic-[a-f0-9]{12}\\.json").matches(name)) return null
            val directory = File(filesDir, "profiles/reports").canonicalFile
            val report = File(directory, name).canonicalFile
            return report.takeIf { it.parentFile == directory && it.isFile && it.length() <= 1048576 }
        }
        return null
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 9) {
            if (resultCode != RESULT_OK) return
            try {
                val report = diagnosticReport() ?: return
                val uri = data?.data ?: return
                contentResolver.openOutputStream(uri)?.use { output -> report.inputStream().use { it.copyTo(output) } }
                    ?: throw IllegalStateException("No output stream")
                emit("{\"kind\":\"report-saved\"}")
            } catch (_: Exception) { emit("{\"kind\":\"report-error\"}") }
            return
        }
        if (requestCode != 8 || resultCode != RESULT_OK || Operation.active) return
        try {
            val uri = data?.data ?: return
            val bytes = contentResolver.openInputStream(uri)?.use { it.readBytesBounded(65536) } ?: return
            require(bytes.isNotEmpty())
            val folder = File(filesDir, "identities").apply { mkdirs() }
            val file = File(folder, "key-${UUID.randomUUID()}")
            file.writeBytes(bytes)
            getSharedPreferences("private", MODE_PRIVATE).edit().putString("identity", file.absolutePath).apply()
            emit("{\"kind\":\"key-imported\"}")
        } catch (_: Exception) { emit("{\"kind\":\"key-error\"}") }
    }

    private fun java.io.InputStream.readBytesBounded(limit: Int): ByteArray {
        val result = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(4096)
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            require(result.size() + count <= limit)
            result.write(buffer, 0, count)
        }
        return result.toByteArray()
    }

    override fun onBackPressed() { web.evaluateJavascript("window.goBack && window.goBack()", null) }
    override fun onDestroy() {
        Operation.listener = null
        web.removeJavascriptInterface("CYTV")
        web.destroy()
        super.onDestroy()
    }
}
