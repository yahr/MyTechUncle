// 가볍지이지 디자인 시스템 — 라이트 토큰(lightez-design-system tokens/resolved.json 의 light) + 앱 테마.
// 값은 원본 저장소에서만 바꾸고 여기엔 옮겨 적기만 한다.
// ponytail: 라이트만. 다크를 넣으려면 const 색을 쓰는 곳이 context 로 토큰을 받아야 한다.
import 'package:flutter/material.dart';

export 'package:lucide_icons_flutter/lucide_icons.dart'; // 세무 앱과 같은 선 아이콘

const mint = Color(0xFF0FA08D), //       bg-brand
    mintHover = Color(0xFF0B7F70), //     bg-brand-hover
    brandSoft = Color(0xFFE6FBF8), //     bg-brand-soft
    mintInk = Color(0xFF0B7F70), //       fg-brand
    ink = Color(0xFF16202B), //           fg-primary
    ink2 = Color(0xFF4C5866), //          fg-secondary
    muted = Color(0xFF616D7A), //         fg-muted
    disabled = Color(0xFF9BA6B2), //      fg-disabled
    page = Color(0xFFF7F9FB), //          bg-page
    surface = Color(0xFFFFFFFF), //       bg-surface
    subtle = Color(0xFFEEF1F5), //        bg-subtle
    stroke = Color(0xFFE1E6EC), //        stroke-default
    strokeStrong = Color(0xFFCBD3DB), //  stroke-strong
    focus = Color(0xFF17BFA9), //         stroke-focus
    strokeBrand = Color(0xFF17BFA9), //   stroke-brand
    danger = Color(0xFFC0392B), //        danger
    ok = Color(0xFF22A06B), //            ok
    okSoft = Color(0xFFEAF8EF), okInk = Color(0xFF1A7A52), okLine = Color(0xFFC6EBD3),
    warnSoft = Color(0xFFFFF7E8), warnInk = Color(0xFFA5661A), warnLine = Color(0xFFFBE7BF);

const head = 'A2z'; // 에이투지체 — 제목(t1~t4)·탭 글자(t9)에만. 본문은 시스템 서체

ThemeData dsTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: mint, onPrimary: Colors.white, primaryContainer: brandSoft, onPrimaryContainer: mintInk,
    secondary: mint, onSecondary: Colors.white, secondaryContainer: brandSoft, onSecondaryContainer: mintInk,
    error: danger, onError: Colors.white,
    surface: surface, onSurface: ink, onSurfaceVariant: ink2,
    outline: strokeStrong, outlineVariant: stroke,
    surfaceContainerLowest: surface, surfaceContainerLow: surface, surfaceContainer: surface,
    surfaceContainerHigh: subtle, surfaceContainerHighest: subtle, surfaceTint: Colors.transparent,
  );
  final base = ThemeData(colorScheme: scheme);
  final r12 = RoundedRectangleBorder(borderRadius: BorderRadius.circular(12));
  const btnSize = Size(64, 44); // .btn 40 이지만 눌리는 것은 44 이상
  return base.copyWith(
    scaffoldBackgroundColor: page,
    splashFactory: InkRipple.splashFactory, // 세무 앱과 같은 눌림 효과
    textTheme: base.textTheme.copyWith(
      headlineSmall: const TextStyle(fontFamily: head, fontWeight: FontWeight.w700, fontSize: 22, height: 1.4, color: ink), // t3
      titleLarge: const TextStyle(fontFamily: head, fontWeight: FontWeight.w600, fontSize: 18, height: 1.45, color: ink), // t4
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: surface, foregroundColor: ink, elevation: 0, scrolledUnderElevation: 0, centerTitle: false, toolbarHeight: 56,
      shape: Border(bottom: BorderSide(color: stroke)),
      titleTextStyle: TextStyle(fontFamily: head, fontWeight: FontWeight.w600, fontSize: 18, color: ink), // t4
    ),
    cardTheme: CardThemeData(color: surface, elevation: 1, shadowColor: const Color(0x4016202B), margin: EdgeInsets.zero, // sh-1
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: stroke))),
    navigationBarTheme: NavigationBarThemeData( // .tabbar — 높이 56, 선택은 글자색만
      height: 56, backgroundColor: surface, elevation: 0, surfaceTintColor: Colors.transparent, indicatorColor: Colors.transparent,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      overlayColor: const WidgetStatePropertyAll(Colors.transparent),
      iconTheme: WidgetStateProperty.resolveWith((s) => IconThemeData(size: 22, color: s.contains(WidgetState.selected) ? mintInk : ink2)),
      labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(fontFamily: head, fontSize: 12,
          color: s.contains(WidgetState.selected) ? mintInk : ink2, fontWeight: s.contains(WidgetState.selected) ? FontWeight.w600 : FontWeight.w500)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true, fillColor: surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: strokeStrong)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: strokeStrong)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: focus, width: 2)),
    ),
    filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(shape: r12, minimumSize: btnSize, textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(shape: r12, minimumSize: btnSize, foregroundColor: ink, side: const BorderSide(color: strokeStrong),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
    textButtonTheme: TextButtonThemeData(style: TextButton.styleFrom(shape: r12, foregroundColor: mintInk)),
    floatingActionButtonTheme: FloatingActionButtonThemeData(backgroundColor: mint, foregroundColor: Colors.white, elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
    chipTheme: base.chipTheme.copyWith( // .chip — 32, 선택은 연민트 바탕 + 민트 테두리·글자
      shape: const StadiumBorder(),
      side: WidgetStateBorderSide.resolveWith((s) => BorderSide(color: s.contains(WidgetState.selected) ? strokeBrand : stroke)),
      color: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? brandSoft : surface),
      showCheckmark: false, padding: const EdgeInsets.symmetric(horizontal: 4), labelPadding: const EdgeInsets.symmetric(horizontal: 8),
      // 상태별 TextStyle(WidgetStateTextStyle)은 기기가 다크 모드일 때 흰 글자로 나와서 고정 색 둘로 나눈다(2026-11-13 갤럭시에서 확인)
      labelStyle: const TextStyle(fontSize: 13, color: ink2, fontWeight: FontWeight.w500),
      secondaryLabelStyle: const TextStyle(fontSize: 13, color: mintInk, fontWeight: FontWeight.w600), // 선택됨
    ),
    // 굵기 위계: 상세 큰 제목 700 · 화면·섹션 제목 600(에이투지체) · 목록 제목·본문 강조 500(본문 서체, .list-row .title)
    listTileTheme: const ListTileThemeData(titleTextStyle: TextStyle(fontWeight: FontWeight.w500, fontSize: 16, color: ink)),
    bottomSheetTheme: const BottomSheetThemeData(backgroundColor: surface, surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24)))),
    dialogTheme: DialogThemeData(backgroundColor: surface, surfaceTintColor: Colors.transparent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
    dividerTheme: const DividerThemeData(color: stroke, space: 1),
    snackBarTheme: SnackBarThemeData(behavior: SnackBarBehavior.floating, backgroundColor: ink, shape: r12),
  );
}
