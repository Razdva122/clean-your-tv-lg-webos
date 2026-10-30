package com.cleanyourtv.android

import android.app.Activity
import android.app.Instrumentation
import android.os.Bundle
import com.chaquo.python.Python
import com.chaquo.python.PyException
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Native operation tests. No TV connection, credentials or production test hooks. */
class OperationChecks : Instrumentation() {
    private var upgradeMode: String? = null

    override fun onCreate(arguments: Bundle?) {
        super.onCreate(arguments)
        upgradeMode = arguments?.getString("upgrade")
        start()
    }

    override fun onStart() {
        val result = Bundle()
        try {
            if (upgradeMode != null) {
                checkUpgrade(upgradeMode!!)
                result.putString("stream", "PASS: upgrade fixture $upgradeMode; no TV commands\n")
                finish(Activity.RESULT_OK, result)
                return
            }
            checkChineseResources()
            for (edition in listOf("no-root", "root")) {
                checkReplay(edition)
            }
            result.putString("stream", "PASS: both editions, single operation, bounded replay, pending prompts and stale answers\n")
            finish(Activity.RESULT_OK, result)
        } catch (error: Throwable) {
            result.putString("stream", "FAIL: ${error.stackTraceToString()}\n")
            finish(Activity.RESULT_CANCELED, result)
        } finally {
            Operation.listener = null
            Operation.emit("{\"kind\":\"finished\",\"code\":130}")
        }
    }

    private fun checkChineseResources() {
        // Script qualifiers are supported on our minimum Android API 24. Check
        // platform region inference as well as explicit script precedence.
        for ((tag, traditional) in listOf(
            "zh" to false, "zh-CN" to false, "zh-SG" to false,
            "zh-TW" to true, "zh-HK" to true, "zh-MO" to true,
            "zh-Hant-CN" to true, "zh-Hans-TW" to false
        )) {
            val config = android.content.res.Configuration(targetContext.resources.configuration)
            config.setLocale(java.util.Locale.forLanguageTag(tag))
            val resources = targetContext.createConfigurationContext(config).resources
            check(resources.getString(R.string.installation_channel) == "CYTV") { tag }
            check(resources.getString(R.string.installation_progress) ==
                if (traditional) "電視操作進行中" else "电视操作进行中") { tag }
            check(resources.getString(R.string.webview_update).contains(
                if (traditional) "重新開啟" else "重新打开")) { tag }
        }
    }

    private fun events(): List<JSONObject> {
        val snapshot = JSONArray(Operation.snapshot())
        return (0 until snapshot.length()).map { JSONObject(snapshot.getString(it)) }
    }

    private fun checkUpgrade(mode: String) {
        check(mode in listOf("seed", "verify"))
        check(!Operation.active && events().isEmpty()) { "A new process must not resume installation automatically" }
        if (!Python.isStarted()) Python.start(AndroidPlatform(targetContext))
        val python = Python.getInstance()
        val key = File(targetContext.filesDir, "identities/android-stable-test-key")
        val marker = "TEST FIXTURE ONLY, NOT A PRIVATE KEY"
        val preferences = targetContext.getSharedPreferences("private", 0)
        val state = python.getModule("cytv.state")
        val store = state.callAttr("Store", File(targetContext.filesDir, "profiles").absolutePath)
        val profile = state.callAttr("target", "192.0.2.123", "root", 22, key.absolutePath)
        val directory = File(store.callAttr("device_dir", profile).toString())
        if (mode == "seed") {
            check(!key.exists()) { "Upgrade fixture already exists; verify it before starting another run" }
            key.parentFile!!.mkdirs()
            key.writeText(marker)
            check(preferences.edit().putString("stable-test-identity", key.absolutePath).commit())
            store.callAttr("save", profile)
            store.callAttr("begin", profile, "install")
        } else {
            check(targetContext.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE == 0) {
                "Upgrade target must be a non-debuggable release APK"
            }
            check(key.readText() == marker) { "Imported-key file did not survive APK update" }
            check(preferences.getString("stable-test-identity", "") == key.absolutePath) { "Private preferences lost" }
            // Store normalizes identities through pathlib.resolve; Android's
            // /data/user/0 and /data/data aliases can spell the same file differently.
            check(JSONObject(File(directory, "profile.json").readText()).getString("identity") == key.canonicalPath) {
                "Saved identity no longer resolves to the imported-key fixture"
            }
            val receipt = File(directory, "operation.json").readBytes()
            check(store.callAttr("pending", profile).callAttr("get", "stage").toString() == "pending")
            var blocked = false
            try {
                store.callAttr("begin", profile, "install")
            } catch (error: PyException) {
                check(error.message?.contains("Previous operation is unresolved") == true) { "Unexpected receipt error" }
                blocked = true
            }
            check(blocked) { "A pending operation must block another install after process death or upgrade" }
            check(File(directory, "operation.json").readBytes().contentEquals(receipt)) { "Pending receipt overwritten" }
            // Remove only this runner's reserved synthetic fixture after success.
            store.callAttr("finish", profile)
            File(directory, "profile.json").delete()
            directory.delete()
            key.delete()
            check(preferences.edit().remove("stable-test-identity").commit())
        }
    }

    private fun checkReplay(edition: String) {
        val config = JSONObject().put("host", "192.0.2.1").put("edition", edition)
            .put("action", "status").toString()
        check(Operation.begin(config)) { "First operation must start" }
        check(!Operation.begin(config)) { "Second operation must not replace the first" }
        val prompts = LinkedBlockingQueue<JSONObject>()
        Operation.listener = { raw ->
            val event = JSONObject(raw)
            if (event.optString("kind") == "secret") prompts.offer(event)
        }
        val executor = Executors.newSingleThreadExecutor()
        val pending = executor.submit<String?> { Operation.request("{\"kind\":\"secret\",\"secretType\":\"root\"}") }
        try {
            val prompt = prompts.poll(5, TimeUnit.SECONDS) ?: error("Prompt was not emitted")
            val id = prompt.getString("id")
            // A detached Activity misses live events. Its replacement must be
            // able to replay the pending question even after the log is bounded.
            Operation.listener = null
            Operation.emit("""{"kind":"check","checkId":"ssh","status":"running"}""")
            Operation.emit("""{"kind":"check","checkId":"node-version","status":"pending"}""")
            Operation.emit("""{"kind":"check","checkId":"ssh","status":"pass"}""")
            Operation.emit("""{"kind":"check","checkId":"node-version","status":"fail"}""")
            repeat(500) { Operation.emit("{\"kind\":\"log\",\"text\":\"line $it\"}") }
            val replay = events()
            check(replay.size <= 450) { "Replay must remain bounded" }
            check(replay.first().getJSONObject("config").getString("edition") == edition)
            check(replay.count { it.optString("kind") == "started" } == 1)
            check(replay.any { it.optString("id") == id }) { "Pending prompt lost during Activity replay" }
            val checks = replay.filter { it.optString("kind") == "check" }
            check(checks.map { it.getString("checkId") } == listOf("ssh", "node-version")) { "Keep check display order" }
            check(checks.count { it.optString("checkId") == "ssh" } == 1) { "Keep only the latest check result" }
            check(checks.single { it.optString("checkId") == "ssh" }.getString("status") == "pass")
            check(checks.single { it.optString("checkId") == "node-version" }.getString("status") == "fail")
            Operation.answer("stale-prompt-id", "wrong-answer")
            Operation.answer(id, "test-only-secret")
            check(pending.get(5, TimeUnit.SECONDS) == "test-only-secret") { "Stale answer accepted" }
            check(!Operation.snapshot().contains("test-only-secret")) { "Secret leaked into replay" }
            check(events().any { it.optString("kind") == "answered" && it.optString("id") == id })
        } finally {
            pending.cancel(true)
            executor.shutdownNow()
            Operation.listener = null
            Operation.emit("{\"kind\":\"finished\",\"code\":130}")
        }
        check(!Operation.active)
    }
}
