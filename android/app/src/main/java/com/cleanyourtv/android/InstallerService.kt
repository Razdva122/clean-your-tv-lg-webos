package com.cleanyourtv.android

import android.app.*
import android.content.Intent
import android.os.*
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File
import java.util.UUID
import java.security.MessageDigest
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/** Process-owned operation state; Activity recreation never restarts installation. */
object Operation {
    private val events = mutableListOf<String>()
    private val answers = LinkedBlockingQueue<Pair<String, String?>>()
    @Volatile var active = false
        private set
    @Volatile var listener: ((String) -> Unit)? = null
    private var promptId: String? = null

    @Synchronized fun begin(config: String): Boolean {
        if (active) return false
        active = true
        events.clear()
        answers.clear()
        promptId = null
        emit(JSONObject().put("kind", "started").put("config", JSONObject(config)).toString())
        return true
    }

    @Synchronized fun emit(event: String) {
        val parsed = JSONObject(event)
        val checkIndex = if (parsed.optString("kind") == "check") {
            // Check IDs come from the fixed Python catalogue. Retain their
            // latest result when Activity recreation replays a long operation.
            events.indexOfFirst {
                val previous = JSONObject(it)
                previous.optString("kind") == "check" && previous.optString("checkId") == parsed.optString("checkId")
            }
        } else -1
        if (parsed.optString("kind") == "finished") {
            active = false
            promptId = null
        }
        if (checkIndex >= 0) events[checkIndex] = event else events.add(event)
        // Retain the first started event for Activity replay.
        if (events.size > 450) {
            // Keep the started event and any unanswered prompt available to a
            // recreated Activity, even when background logs fill the replay.
            val disposable = (1 until events.size).first {
                val saved = JSONObject(events[it])
                saved.optString("id") != promptId && saved.optString("kind") != "check"
            }
            events.removeAt(disposable)
        }
        listener?.invoke(event)
    }

    @Synchronized fun snapshot(): String = org.json.JSONArray(events).toString()

    fun request(event: String): String? {
        val id = UUID.randomUUID().toString()
        synchronized(this) { promptId = id }
        emit(JSONObject(event).put("id", id).toString())
        val deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(10)
        while (true) {
            val remaining = deadline - System.nanoTime()
            if (remaining <= 0) return null
            val answer = answers.poll(remaining, TimeUnit.NANOSECONDS) ?: return null
            if (answer.first == id) {
                synchronized(this) { promptId = null }
                emit(JSONObject().put("kind", "answered").put("id", id).toString())
                return answer.second
            }
        }
    }

    @Synchronized fun answer(id: String, value: String?) {
        if (id == promptId && active) answers.offer(id to value)
    }
}

class InstallerService : Service() {
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?) = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val config = intent?.getStringExtra("config") ?: return START_NOT_STICKY
        if (!Operation.begin(config)) return START_NOT_STICKY
        try {
            val selected = JSONObject(config).optString("language", "en")
            val configuration = android.content.res.Configuration(resources.configuration).apply {
                setLocale(java.util.Locale.forLanguageTag(selected))
            }
            val localized = createConfigurationContext(configuration)
            val notifications = getSystemService(NotificationManager::class.java)
            if (Build.VERSION.SDK_INT >= 26) {
                notifications.createNotificationChannel(NotificationChannel("installation", localized.getString(R.string.installation_channel), NotificationManager.IMPORTANCE_LOW))
            }
            val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
            val builder = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, "installation") else Notification.Builder(this)
            startForeground(1, builder.setSmallIcon(com.cleanyourtv.android.R.drawable.ic_cytv_notification)
                .setContentTitle("CYTV").setContentText(localized.getString(R.string.installation_progress))
                .setContentIntent(open).setOngoing(true).build())
            wakeLock = (getSystemService(POWER_SERVICE) as PowerManager)
                .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "CYTV:installation")
                .apply { acquire(TimeUnit.MINUTES.toMillis(25)) }
            Thread({ execute(config) }, "cytv-installer").start()
        } catch (error: Exception) {
            Operation.emit(JSONObject().put("kind", "error").put("text", error.javaClass.simpleName).toString())
            finish()
        }
        return START_NOT_STICKY
    }

    private fun execute(config: String) {
        try {
            if (!Python.isStarted()) Python.start(AndroidPlatform(this))
            // Preview APKs may be reinstalled with the same versionCode. Key the
            // extraction by its bundled manifest, never by the app version alone.
            val manifest = assets.open("payload/payload.json").use { it.readBytes() }
            val digest = MessageDigest.getInstance("SHA-256").digest(manifest)
                .joinToString("") { "%02x".format(it) }
            val payload = File(filesDir, "payload-$digest")
            if (!File(payload, ".ready").exists()) {
                if (payload.exists()) payload.deleteRecursively()
                copyAsset("payload", payload)
                File(payload, ".ready").writeText("ready")
            }
            val request = JSONObject(config)
            val savedKey = getSharedPreferences("private", MODE_PRIVATE).getString("identity", "") ?: ""
            val identity = if (request.optBoolean("useImportedKey") && File(savedKey).isFile) savedKey else ""
            Python.getInstance().getModule("android_bridge").callAttr("run", config,
                File(filesDir, "profiles").absolutePath, payload.absolutePath, identity, Callbacks())
        } catch (error: Exception) {
            Operation.emit(JSONObject().put("kind", "error").put("text", error.javaClass.simpleName).toString())
        } finally { finish() }
    }

    private fun copyAsset(path: String, target: File) {
        val children = assets.list(path) ?: emptyArray()
        if (children.isNotEmpty()) {
            target.mkdirs()
            children.forEach { copyAsset("$path/$it", File(target, it)) }
        } else {
            target.parentFile?.mkdirs()
            assets.open(path).use { input -> target.outputStream().use { input.copyTo(it) } }
        }
    }

    class Callbacks {
        fun emit(event: String) = Operation.emit(event)
        fun request(event: String): String? = Operation.request(event)
    }

    private fun finish() {
        if (Operation.active) Operation.emit("{\"kind\":\"finished\",\"code\":2}")
        if (wakeLock?.isHeld == true) wakeLock?.release()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onTimeout(startId: Int, fgsType: Int) {
        // The journal remains pending; never replay an install automatically.
        Operation.emit("{\"kind\":\"error\",\"text\":\"Android service timeout\"}")
        finish()
        android.os.Process.killProcess(android.os.Process.myPid())
    }
}
