package com.lightez.mytechuncle

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var pendingCustomerId: Int? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        pendingCustomerId = intent.customerId()
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "mtu/caller").setMethodCallHandler { call, result ->
            when (call.method) {
                "permStatus" -> result.success(mapOf(
                    "phone" to granted(Manifest.permission.READ_PHONE_STATE),
                    "callLog" to granted(Manifest.permission.READ_CALL_LOG),
                    "overlay" to Settings.canDrawOverlays(this),
                ))
                "requestPhone" -> {
                    requestPermissions(arrayOf(Manifest.permission.READ_PHONE_STATE, Manifest.permission.READ_CALL_LOG), 1)
                    result.success(null)
                }
                "openOverlaySettings" -> {
                    startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
                    result.success(null)
                }
                "takeCustomerId" -> { result.success(pendingCustomerId); pendingCustomerId = null }
                else -> result.notImplemented()
            }
        }
    }

    // 수신 카드를 눌러 앱이 열리면 그 고객 id 를 Flutter 에 넘긴다
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.customerId()?.let { pendingCustomerId = it }
    }

    private fun Intent.customerId(): Int? = getIntExtra("customer_id", 0).takeIf { it > 0 }
    private fun granted(p: String) = checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED
}
