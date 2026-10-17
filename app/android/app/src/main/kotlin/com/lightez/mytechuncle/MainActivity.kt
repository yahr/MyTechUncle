package com.lightez.mytechuncle

import android.Manifest
import android.annotation.SuppressLint
import android.content.ContentUris
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.provider.Settings
import android.telecom.TelecomManager
import android.telephony.TelephonyManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import kotlin.concurrent.thread

class MainActivity : FlutterActivity() {
    private var pendingCustomerId: Int? = null
    private var pendingAudioResult: MethodChannel.Result? = null

    companion object {
        var channel: MethodChannel? = null
        var callState: String = "idle" // CallReceiver 가 갱신: ringing / offhook / idle
        var current: MainActivity? = null

        /** 전화 상태가 바뀌면 열려 있는 화면에 알린다 */
        fun onCallState(state: String) {
            callState = state
            channel?.invokeMethod("callState", state)
            if (state == "idle") current?.setShowWhenLocked(false)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        current = this
        fromCall(intent)
    }

    override fun onDestroy() {
        if (current === this) current = null
        super.onDestroy()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        pendingCustomerId = intent.customerId()
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "mtu/caller").apply {
            setMethodCallHandler { call, result ->
                when (call.method) {
                    "permStatus" -> result.success(mapOf(
                        "phone" to granted(Manifest.permission.READ_PHONE_STATE),
                        "callLog" to granted(Manifest.permission.READ_CALL_LOG),
                        "answer" to granted(Manifest.permission.ANSWER_PHONE_CALLS),
                        "overlay" to Settings.canDrawOverlays(this@MainActivity),
                    ))
                    "requestPhone" -> {
                        requestPermissions(arrayOf(Manifest.permission.READ_PHONE_STATE, Manifest.permission.READ_CALL_LOG,
                            Manifest.permission.ANSWER_PHONE_CALLS), 1)
                        result.success(null)
                    }
                    "openOverlaySettings" -> {
                        startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
                        result.success(null)
                    }
                    "takeCustomerId" -> { result.success(pendingCustomerId); pendingCustomerId = null }
                    "callState" -> result.success(callState)
                    "answerCall" -> result.success(telecom { acceptRingingCall(); true })
                    "endCall" -> result.success(telecom { endCall() })
                    "audioGranted" -> result.success(granted(audioPermission))
                    "requestAudio" -> {
                        if (granted(audioPermission)) result.success(true)
                        else {
                            pendingAudioResult = result
                            requestPermissions(arrayOf(audioPermission), 2)
                        }
                    }
                    "openAppSettings" -> {
                        startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
                        result.success(null)
                    }
                    "listRecordings" -> background(result) { listRecordings() }
                    "copyRecording" -> {
                        val id = (call.argument<Number>("id"))?.toLong() ?: -1L
                        background(result) { copyRecording(id) }
                    }
                    else -> result.notImplemented()
                }
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 2) {
            pendingAudioResult?.success(grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED)
            pendingAudioResult = null
        }
    }

    // ---- 통화 녹음 요약: 버튼을 눌렀을 때만 쓴다. 원본은 건드리지 않고, 고른 한 건만 캐시로 복사한다 ----
    private val audioPermission
        get() = if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO else Manifest.permission.READ_EXTERNAL_STORAGE

    private fun background(result: MethodChannel.Result, block: () -> Any?) {
        thread {
            try {
                val v = block()
                runOnUiThread { result.success(v) }
            } catch (e: Exception) {
                runOnUiThread { result.error("fail", e.message, null) }
            }
        }
    }

    /** 통화 녹음 폴더(갤럭시 Recordings/Call, 옛 기기 Call/·Recordings/, T전화 TPhoneCallRecords)의 오디오 목록, 최신순 */
    private fun listRecordings(): List<Map<String, Any?>> {
        val out = mutableListOf<Map<String, Any?>>()
        val cols = arrayOf(MediaStore.Audio.Media._ID, MediaStore.Audio.Media.DISPLAY_NAME, MediaStore.Audio.Media.DATE_MODIFIED,
            MediaStore.Audio.Media.DURATION, MediaStore.Audio.Media.SIZE)
        val rp = MediaStore.Audio.Media.RELATIVE_PATH
        val where = "($rp LIKE ? OR $rp LIKE ? OR $rp = ? OR $rp LIKE ?)"  // T전화(SKT)는 Recordings/·Music/ 아래 TPhoneCallRecords
        contentResolver.query(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, cols, where, arrayOf("Recordings/Call%", "Call%", "Recordings/", "%TPhoneCallRecords%"),
            "${MediaStore.Audio.Media.DATE_MODIFIED} DESC")?.use { c ->
            while (c.moveToNext() && out.size < 500) {
                out.add(mapOf("id" to c.getLong(0), "name" to c.getString(1), "dateMs" to c.getLong(2) * 1000,
                    "durationMs" to c.getLong(3), "size" to c.getLong(4)))
            }
        }
        return out
    }

    /** 고른 녹음 한 건을 앱 캐시로 복사하고 경로를 돌려준다(업로드 뒤 Flutter 가 지운다) */
    private fun copyRecording(id: Long): String {
        val uri = ContentUris.withAppendedId(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, id)
        var name = "rec"
        contentResolver.query(uri, arrayOf(MediaStore.Audio.Media.DISPLAY_NAME), null, null, null)?.use { if (it.moveToFirst()) name = it.getString(0) }
        val ext = name.substringAfterLast('.', "m4a").filter { it.isLetterOrDigit() }.ifEmpty { "m4a" }
        val dir = File(cacheDir, "recordings").apply { mkdirs() }
        val file = File(dir, "rec_$id.$ext")
        (contentResolver.openInputStream(uri) ?: throw IllegalStateException("파일을 열지 못했어요")).use { input ->
            file.outputStream().use { input.copyTo(it) }
        }
        return file.absolutePath
    }

    // 수신 카드를 눌러 앱이 열리면 그 고객 id 를 Flutter 에 넘긴다
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.customerId()?.let { pendingCustomerId = it }
        fromCall(intent)
    }

    // 카드에서 열었을 때만 잠금 화면 위로 보인다(통화가 끝나면 다시 끈다)
    private fun fromCall(intent: Intent?) {
        if (intent?.customerId() != null && callState != "idle") {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        }
    }

    @SuppressLint("MissingPermission")
    private fun telecom(block: TelecomManager.() -> Boolean): Boolean =
        granted(Manifest.permission.ANSWER_PHONE_CALLS) &&
            runCatching { (getSystemService(TELECOM_SERVICE) as TelecomManager).block() }.getOrDefault(false)

    private fun Intent.customerId(): Int? = getIntExtra("customer_id", 0).takeIf { it > 0 }
    private fun granted(p: String) = checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED
}

/** TelephonyManager 상태 문자열 → 화면에서 쓰는 이름 */
fun callStateName(s: String?): String? = when (s) {
    TelephonyManager.EXTRA_STATE_RINGING -> "ringing"
    TelephonyManager.EXTRA_STATE_OFFHOOK -> "offhook"
    TelephonyManager.EXTRA_STATE_IDLE -> "idle"
    else -> null
}
