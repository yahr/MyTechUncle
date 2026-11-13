import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'core.dart';
import 'ds.dart';
import 'ds_bars.dart';
import 'screens.dart';
import 'store.dart';

final store = Store();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  store.init();
  listenCallState();
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: '기술고문 노트',
        debugShowCheckedModeBanner: false,
        theme: dsTheme(),
        home: const Home(),
      );
}

class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> with WidgetsBindingObserver {
  int tab = 0;
  Map perms = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _onResume();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed) {
      _onResume();
      native.invokeMethod<String>('callState').then((v) => callState.value = v ?? 'idle').catchError((_) => 'idle');
      store.refresh(); // 앱으로 돌아올 때마다 새로 받아 수신 카드 목록도 갱신
    }
  }

  // 권한 상태 확인 + 수신 카드를 눌러 들어왔으면 그 고객으로
  Future<void> _onResume() async {
    try {
      final p = await native.invokeMethod<Map>('permStatus');
      if (mounted) setState(() => perms = p ?? {});
      final id = await native.invokeMethod<int>('takeCustomerId');
      if (id != null && id > 0 && mounted) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomerPage(id: id)));
      }
      final shared = await native.invokeMethod<String>('takeSharedText');
      if (shared != null && shared.trim().isNotEmpty && mounted) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => SharedTextPage(text: shared.trim())));
      }
    } catch (_) {}
  }

  bool get cardReady => perms['phone'] == true && perms['callLog'] == true && perms['answer'] == true && perms['overlay'] == true;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: store,
        builder: (context, _) => Scaffold(
          appBar: DsAppBar(title: '기술고문 노트', back: false, actions: [
            if (store.loading) const SizedBox(width: 44, height: 44, child: Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)))),
            DsIconBtn(icon: LucideIcons.refreshCw, label: '새로 불러오기', onTap: store.refresh),
          ]),
          body: Column(children: [
            const SizedBox(height: 16), // 세무 앱처럼 상단바 아래 16
            if (perms.isNotEmpty && !cardReady) _PermBanner(perms: perms, onChanged: _onResume),
            if (store.error != null)
              Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8), child: Text(store.error!, style: const TextStyle(color: danger, fontSize: 13))),
            Expanded(child: switch (tab) { 0 => ApplicationsTab(), 1 => CustomersTab(), _ => IssuesTab() }), // const 를 쓰면 store 가 바뀌어도 다시 안 그려진다
          ]),
          bottomNavigationBar: DsTabBar(
            selected: tab,
            onSelected: (i) => setState(() => tab = i),
            items: const [(LucideIcons.inbox, '신청'), (LucideIcons.users, '고객'), (LucideIcons.listChecks, '이슈')],
          ),
        ),
      );
}

class _PermBanner extends StatelessWidget {
  const _PermBanner({required this.perms, required this.onChanged});
  final Map perms;
  final VoidCallback onChanged;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('전화 수신 카드를 켜 주세요', style: TextStyle(fontFamily: head, fontWeight: FontWeight.w600, fontSize: 18)),
              const SizedBox(height: 4),
              const Text('고객에게 전화가 오면 누구인지, 구독, 지난 상담이 화면 위에 떠요.', style: TextStyle(color: ink2)),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (perms['phone'] != true || perms['callLog'] != true || perms['answer'] != true)
                  FilledButton(onPressed: () async { await native.invokeMethod('requestPhone'); onChanged(); }, child: const Text('전화·통화 기록·전화 받기 권한')),
                if (perms['overlay'] != true)
                  FilledButton.tonal(onPressed: () => native.invokeMethod('openOverlaySettings'), child: const Text('다른 앱 위에 표시 켜기')),
              ]),
            ]),
          ),
        ),
      );
}

Future<void> callPhone(String? phone) async {
  final p = normalizePhone(phone);
  if (p.isNotEmpty) await launchUrl(Uri(scheme: 'tel', path: p));
}
