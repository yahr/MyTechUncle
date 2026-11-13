// 앱바 · 탭바 — 세무 앱(lightez-tax-app lib/widgets/ds_bars.dart)과 같은 모양. DS .appbar · .tabbar · .icon-btn.
// 눌리는 것은 44×44, 앱바 56, 탭바 56 + 아랫 안전 영역.
import 'package:flutter/material.dart';

import 'ds.dart';

class DsIconBtn extends StatelessWidget {
  const DsIconBtn({super.key, required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        label: label,
        child: Tooltip(
          message: label,
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(12),
            child: SizedBox(width: 44, height: 44, child: Center(child: Icon(icon, size: 24, color: ink))),
          ),
        ),
      );
}

/// .appbar — 아래 1px 선, 왼쪽 깃털 마크(하위 화면은 뒤로), 제목(에이투지체 t4), 오른쪽 아이콘 버튼.
class DsAppBar extends StatelessWidget implements PreferredSizeWidget {
  const DsAppBar({super.key, this.title = '', this.back = true, this.actions = const []});
  final String title;
  final bool back;
  final List<Widget> actions;

  @override
  Size get preferredSize => const Size.fromHeight(56);

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(color: surface, border: Border(bottom: BorderSide(color: stroke))),
        child: SafeArea(
          bottom: false,
          child: SizedBox(
            height: 55,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(children: [
                if (back)
                  DsIconBtn(icon: LucideIcons.chevronLeft, label: '뒤로', onTap: () => Navigator.of(context).maybePop())
                else
                  SizedBox(width: 44, height: 44, child: Center(child: Image.asset('assets/logo.png', width: 28, height: 28))),
                const SizedBox(width: 4),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontFamily: head, fontSize: 18, fontWeight: FontWeight.w600, height: 1.45, color: ink)),
                  ),
                ),
                ...actions,
              ]),
            ),
          ),
        ),
      );
}

/// .tabbar — 위 1px 선, 흰 바탕, 선 아이콘 24 + 에이투지체 12. 현재 탭은 민트 글자 + 600, 알약 표시 없음.
class DsTabBar extends StatelessWidget {
  const DsTabBar({super.key, required this.items, required this.selected, required this.onSelected});
  final List<(IconData, String)> items;
  final int selected;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(color: surface, border: Border(top: BorderSide(color: stroke))),
        child: SafeArea(
          top: false,
          child: Row(children: [
            for (var i = 0; i < items.length; i++)
              Expanded(
                child: Semantics(
                  button: true,
                  selected: i == selected,
                  label: items[i].$2,
                  child: InkWell(
                    onTap: () => onSelected(i),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 55),
                      child: Column(mainAxisSize: MainAxisSize.min, mainAxisAlignment: MainAxisAlignment.center, children: [
                        Icon(items[i].$1, size: 24, color: i == selected ? mintInk : ink2),
                        const SizedBox(height: 2),
                        ExcludeSemantics(
                          child: Text(items[i].$2,
                              style: TextStyle(fontFamily: head, fontSize: 12, height: 1.45,
                                  color: i == selected ? mintInk : ink2, fontWeight: i == selected ? FontWeight.w600 : FontWeight.w500)),
                        ),
                      ]),
                    ),
                  ),
                ),
              ),
          ]),
        ),
      );
}

/// .card — 흰 바탕 + 1px 테두리 + r-lg + sh-1, 안쪽 20. 세무 앱 widgets/ds_card.dart 와 같다.
class DsCard extends StatelessWidget {
  const DsCard({super.key, required this.child, this.padding = const EdgeInsets.all(20)});
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: padding,
        decoration: BoxDecoration(
          color: surface,
          border: Border.all(color: stroke),
          borderRadius: BorderRadius.circular(16),
          boxShadow: const [BoxShadow(color: Color(0x0F16202B), offset: Offset(0, 1), blurRadius: 2)],
        ),
        child: child,
      );
}

class _DashedRRect extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()..addRRect(RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(16)).deflate(0.5));
    final paint = Paint()
      ..color = strokeStrong
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    for (final m in path.computeMetrics()) {
      for (var d = 0.0; d < m.length; d += 6) {
        canvas.drawPath(m.extractPath(d, d + 3), paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}

/// .empty — 점선 상자, 아이콘 48 · 제목(에이투지체 t4) · 되는 방법(t7 흐림). 세무 앱 widgets/notice.dart 의 Notice 와 같다.
class DsNotice extends StatelessWidget {
  const DsNotice({super.key, required this.title, required this.message, this.icon = LucideIcons.inbox, this.error = false});
  final String title;
  final String message;
  final IconData icon;
  final bool error;

  @override
  Widget build(BuildContext context) => CustomPaint(
        foregroundPainter: _DashedRRect(),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 16),
          decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(16)),
          child: Column(children: [
            Icon(error ? LucideIcons.circleAlert : icon, size: 48, color: error ? danger : muted),
            const SizedBox(height: 16),
            Text(title, textAlign: TextAlign.center, style: const TextStyle(fontFamily: head, fontSize: 18, fontWeight: FontWeight.w600, height: 1.45, color: ink)),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14, height: 1.55, color: muted)),
          ]),
        ),
      );
}

/// 라벨(t8 보조색) 위 · 값(t6) 아래. 세무 앱 업무 상세의 '업체 / 담당' 칸.
class DsKv extends StatelessWidget {
  const DsKv(this.label, this.value, {super.key});
  final String label;
  final Widget value;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, height: 1.5, color: ink2)),
        const SizedBox(height: 4),
        DefaultTextStyle.merge(style: const TextStyle(fontSize: 15, height: 1.6, color: ink), child: value),
      ]);
}
