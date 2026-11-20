package com.cleanyourtv.android

import android.app.Activity
import android.app.Instrumentation
import android.os.Bundle
import com.chaquo.python.Python
import com.chaquo.python.PyException
import com.chaquo.python.PyObject
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.InetAddress
import java.net.ServerSocket
import java.util.UUID
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
            checkBridge()
            checkBridgeCancellation()
            checkPayloadRetention()
            for (edition in listOf("no-root", "root")) {
                checkReplay(edition)
            }
            result.putString("stream", "PASS: both editions, single operation, bounded replay, pending prompts and stale answers\n" +
                "PASS: packaged Python bridge, loopback inspection and synthetic status terminal result\n" +

                "PASS: payload A/B/C retention, interrupted extraction, cleanup retry and private recovery data\n")
            finish(Activity.RESULT_OK, result)
        } catch (error: Throwable) {
            result.putString("stream", "FAIL: ${error.stackTraceToString()}\n")
            finish(Activity.RESULT_CANCELED, result)
        } finally {
            Operation.listener = null
            Operation.emit("{\"kind\":\"finished\",\"code\":130}")
        }
    }

    private fun checkPayloadRetention() {
        val fixture = File.createTempFile("payload-fixture-", ".dir", targetContext.filesDir)
        check(fixture.delete() && fixture.mkdir())
        try {
            val key = File(fixture, "identities/test-key")
            key.parentFile!!.mkdir()
            key.writeText("TEST FIXTURE ONLY")
            val state = Python.getInstance().getModule("cytv.state")
            val store = state.callAttr("Store", File(fixture, "profiles").absolutePath)
            val privateFiles = mutableListOf(key)
            for ((edition, port) in listOf("root" to 22, "no-root" to 9922)) {
                val profile = state.callAttr("target", "192.0.2.123", edition, port, key.absolutePath)
                store.callAttr("save", profile)
                store.callAttr("begin", profile, "install")
                val profileDir = File(store.callAttr("device_dir", profile).toString())
                privateFiles += File(profileDir, "profile.json")
                privateFiles += File(profileDir, "operation.json")
                privateFiles += File(profileDir, "known_hosts").apply { writeText("TEST SSH PIN") }
                if (edition == "no-root") {
                    privateFiles += File(profileDir, "capsule-${"a".repeat(32)}.json").apply {
                        writeText("""{"fixture":"original No-root operation bytes"}""")
                    }
                }
            }
            // Only digest-named directories in the extraction namespace are cache entries.
            val unrelated = File(fixture, "payload-other/notes").apply {
                parentFile!!.mkdir()
                writeText("TEST NOTES")
            }
            privateFiles += unrelated
            privateFiles += File(fixture, "payload-${"1".repeat(64)}").apply { writeText("TEST FILE") }
            val before = privateFiles.associateWith { it.readBytes() }
            fun manifest(id: String) = """{"fixture":"$id"}""".toByteArray()
            fun extract(id: String) = preparePayload(fixture, manifest(id)) { output ->
                check(output.mkdir())
                File(output, "payload.json").writeBytes(manifest(id))
                File(output, "payload-data").writeText(id)
            }

            val a = extract("A")
            var partial: File? = null
            val failed = runCatching {
                preparePayload(fixture, manifest("B")) { output ->
                    partial = output
                    check(output.mkdir())
                    File(output, "payload.json").writeBytes(manifest("B"))
                    File(output, ".ready").createNewFile()
                    throw IOException("synthetic interrupted copy")
                }
            }.exceptionOrNull()
            check(failed is IOException && failed.message == "synthetic interrupted copy")
            check(File(a, "payload-data").readText() == "A") { "Failed replacement lost the working payload" }

            val b = extract("B")
            check(b == partial && File(b, "payload-data").readText() == "B")
            check(!a.exists()) { "Successful replacement kept superseded payload A" }

            val bMarker = File(b, ".ready")
            check(bMarker.delete() && bMarker.mkdir())
            val blocked = File(bMarker, "blocked").apply { writeText("simulate a failed marker deletion") }
            val c = extract("C")
            check(b.isDirectory && File(b, "payload-data").readText() == "B")
            check(blocked.delete())
            check(preparePayload(fixture, manifest("C")) { error("Ready payload C was recopied") } == c)
            check(fixture.listFiles()!!.filter { it.isDirectory && it.name.matches(Regex("payload-[0-9a-f]{64}")) } ==
                listOf(c)) { "Superseded payload cleanup was not retried" }
            check(File(c, "payload-data").readText() == "C")
            for ((path, bytes) in before) {
                check(path.readBytes().contentEquals(bytes)) { "Changed private fixture file ${path.name}" }
            }
        } finally {
            fixture.deleteRecursively()
        }
    }

    private fun checkBridge() {
        if (!Python.isStarted()) Python.start(AndroidPlatform(targetContext))
        val python = Python.getInstance()
        val bridge = python.getModule("android_bridge")
        val directory = File(targetContext.cacheDir, "bridge-check-${UUID.randomUUID()}")
        check(directory.mkdir()) { "Could not create isolated operation state" }
        try {
            ServerSocket(0, 1, InetAddress.getByName("127.0.0.1")).use { fixture ->
                fixture.soTimeout = 15_000
                val server = Executors.newSingleThreadExecutor()
                val served = server.submit {
                    fixture.accept().use { client ->
                        client.getOutputStream().write("SSH-2.0-CYTVFixture\r\n".toByteArray())
                    }
                    // Terminate the status probe before SSH authentication.
                    fixture.accept().close()
                }
                try {
                    checkBridgeInspection(bridge, fixture.localPort)
                    val config = JSONObject().put("host", "127.0.0.1").put("port", fixture.localPort)
                        .put("edition", "root").put("action", "status").put("language", "en").toString()
                    check(Operation.begin(config))
                    val code = bridge.callAttr("run", config, directory.absolutePath,
                        File(directory, "unused-payload").absolutePath, "", InstallerService.Callbacks()).toInt()
                    served.get(5, TimeUnit.SECONDS)

                    val events = events()
                    check(events.any {
                        it.optString("kind") == "failure-help" && it.optString("code") == "ssh-protocol"
                    }) { "Synthetic status did not reach SSH negotiation" }
                    check(events.none { it.optString("kind") in listOf("secret", "trust", "question") }) {
                        "Synthetic status requested input"
                    }
                    val finished = events.filter { it.optString("kind") == "finished" }.single()
                    check(code == 1 && finished.getInt("code") == code && !Operation.active) {
                        "Synthetic status did not finish with the expected SSH failure"
                    }
                } finally {
                    server.shutdownNow()
                }
            }
        } finally {
            directory.deleteRecursively()
        }
    }

    private fun checkBridgeInspection(bridge: PyObject, port: Int) {
        val config = JSONObject().put("host", "127.0.0.1").put("port", port).toString()
        val localError = JSONObject(inspectionResult(config) {
            Python.getInstance().getModule("missing_inspection_fixture").toString()
        })
        check(localError.getString("kind") == "inspection-error")
        check(localError.getString("host") == "127.0.0.1")
        check(!localError.has("root_ssh") && !localError.has("developer_ssh"))
        val result = JSONObject(inspectionResult(config) {
            bridge.callAttr("inspect_connection", config).toString()
        })
        check(result.getString("kind") == "inspection")
        check(result.getString("host") == "127.0.0.1" && result.getInt("root_port") == port)
        check(result.getBoolean("root_ssh") && !result.getBoolean("developer_ssh"))
    }

    private fun checkBridgeCancellation() {
        val bridge = Python.getInstance().getModule("android_bridge")
        val request = JSONObject().put("host", "127.0.0.1").put("action", "install").put("edition", "root")
            .put("language", "en").toString()
        val profiles = File.createTempFile("bridge-fixture-", ".dir", targetContext.filesDir)
        check(profiles.delete() && profiles.mkdir())
        check(Operation.begin(request))
        Operation.listener = { raw ->
            val event = JSONObject(raw)
            if (event.getString("kind") == "question") Operation.answer(event.getString("id"), "n")
        }
        try {
            val code = bridge.callAttr("run", request, profiles.absolutePath,
                File(profiles, "unused-payload").absolutePath, "", InstallerService.Callbacks()).toInt()
            val resultEvents = events()
            check(resultEvents.count { it.optString("kind") == "question" } == 1)
            check(resultEvents.any { it.optString("text").trim() == "Cancelled. No TV changes were made." })
            check(code == 0 && resultEvents.last().getString("kind") == "finished" &&
                resultEvents.last().getInt("code") == code && !Operation.active)
        } finally {
            Operation.listener = null
            profiles.deleteRecursively()
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
