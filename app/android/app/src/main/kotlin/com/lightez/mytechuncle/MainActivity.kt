package com.lightez.mytechuncle

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.telecom.TelecomManager
import android.telephony.TelephonyManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var pendingCustomerId: Int? = null

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
                    else -> result.notImplemented()
                }
            }
        }
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
