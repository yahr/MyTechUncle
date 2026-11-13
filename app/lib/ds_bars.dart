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
