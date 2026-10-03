package com.lightez.mytechuncle

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.provider.Settings
import android.telephony.TelephonyManager
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject

/**
 * 전화가 오면 앱이 저장해 둔 caller_index(번호 → 고객 요약)에서 찾아 화면 위에 카드를 띄운다.
 * 인터넷 없이 동작. 통화가 끝나면(IDLE) 카드를 닫는다. 등록된 고객 번호가 아니면 아무것도 하지 않는다.
 */
class CallReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val ctx = context.applicationContext
        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
        callStateName(state)?.let { MainActivity.onCallState(it) }
        when (state) {
            TelephonyManager.EXTRA_STATE_RINGING -> {
                // 번호는 READ_CALL_LOG 권한이 있을 때만 들어온다(번호 없는 방송이 한 번 더 온다)
                val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER) ?: return
                val info = lookup(ctx, number) ?: return
                CallerCard.show(ctx, info)
            }
            TelephonyManager.EXTRA_STATE_IDLE -> CallerCard.hide(ctx)
        }
    }

    private fun lookup(ctx: Context, number: String): JSONObject? {
        val raw = ctx.getSharedPreferences("FlutterSharedPreferences", Context.MODE_PRIVATE)
            .getString("flutter.caller_index", null) ?: return null
        return runCatching { JSONObject(raw).optJSONObject(normalize(number)) }.getOrNull()
    }

    companion object {
        // lib/core.dart normalizePhone 과 같은 규칙
        fun normalize(raw: String): String {
            var d = raw.filter { it.isDigit() }
            if (d.startsWith("82") && d.length >= 11) d = "0" + d.substring(2)
            return d
        }
    }
}

object CallerCard {
    private var view: View? = null

    fun show(ctx: Context, info: JSONObject) {
        if (!Settings.canDrawOverlays(ctx)) return
        hide(ctx)
        val dp = { v: Int -> TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), ctx.resources.displayMetrics).toInt() }
        fun text(s: String, size: Float, color: Int, bold: Boolean = false) = TextView(ctx).apply {
            text = s; textSize = size; setTextColor(color)
            if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        val card = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(14), dp(18), dp(14))
            background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius = dp(18).toFloat(); setStroke(dp(2), Color.parseColor("#0FA08D")) }
            elevation = dp(8).toFloat()
            addView(text("나의 기술고문 아저씨 고객", 12f, Color.parseColor("#0B7F70"), bold = true))
            addView(text(info.optString("title"), 20f, Color.parseColor("#16202B"), bold = true))
            addView(text(info.optString("sub"), 14f, Color.parseColor("#0B7F70")))
            val lines = info.optJSONArray("lines")
            if (lines == null || lines.length() == 0) addView(text("상담 내역 없음", 13f, Color.parseColor("#4C5866")))
            else for (i in 0 until lines.length()) addView(text("· " + lines.getString(i), 13f, Color.parseColor("#4C5866")))
            addView(text("눌러서 열기 · 길게 눌러 닫기", 11f, Color.parseColor("#8A94A0")))
            setOnClickListener {
                ctx.startActivity(Intent(ctx, MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    putExtra("customer_id", info.optInt("id"))
                })
                hide(ctx)
            }
            setOnLongClickListener { hide(ctx); true }
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED,
            PixelFormat.TRANSLUCENT,
        ).apply { gravity = Gravity.TOP; x = 0; y = dp(100); horizontalMargin = 0.04f }
        runCatching { (ctx.getSystemService(Context.WINDOW_SERVICE) as WindowManager).addView(card, params); view = card }
    }

    fun hide(ctx: Context) {
        view?.let { v -> runCatching { (ctx.getSystemService(Context.WINDOW_SERVICE) as WindowManager).removeView(v) } }
        view = null
    }
}
