import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'core.dart';
import 'screens.dart';
import 'store.dart';

final store = Store();

const mint = Color(0xFF0FA08D), mintInk = Color(0xFF0B7F70), ink = Color(0xFF16202B), ink2 = Color(0xFF4C5866), page = Color(0xFFF7F9FB);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  store.init();
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: '기술고문 노트',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: mint, primary: mint, surface: Colors.white),
          scaffoldBackgroundColor: page,
          appBarTheme: const AppBarTheme(backgroundColor: page, foregroundColor: ink, elevation: 0, centerTitle: false),
          cardTheme: CardThemeData(color: Colors.white, elevation: 0, margin: EdgeInsets.zero,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Color(0xFFE1E6EC)))),
          inputDecorationTheme: InputDecorationTheme(border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)), filled: true, fillColor: Colors.white),
        ),
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
    if (s == AppLifecycleState.resumed) _onResume();
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
    } catch (_) {}
  }

  bool get cardReady => perms['phone'] == true && perms['callLog'] == true && perms['overlay'] == true;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: store,
        builder: (context, _) => Scaffold(
          appBar: AppBar(
            title: const Text('기술고문 노트', style: TextStyle(fontWeight: FontWeight.w700)),
            actions: [
              if (store.loading) const Padding(padding: EdgeInsets.all(16), child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
              IconButton(tooltip: '새로 불러오기', onPressed: store.refresh, icon: const Icon(Icons.refresh)),
            ],
          ),
          body: Column(children: [
            if (perms.isNotEmpty && !cardReady) _PermBanner(perms: perms, onChanged: _onResume),
            if (store.error != null)
              Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 8), child: Text(store.error!, style: const TextStyle(color: Color(0xFFC0392B), fontSize: 13))),
            Expanded(child: tab == 0 ? const ApplicationsTab() : const CustomersTab()),
          ]),
          floatingActionButton: tab == 1
              ? FloatingActionButton.extended(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const CustomerForm())),
                  icon: const Icon(Icons.person_add_alt),
                  label: const Text('고객 추가'))
              : null,
          bottomNavigationBar: NavigationBar(
            selectedIndex: tab,
            onDestinationSelected: (i) => setState(() => tab = i),
            destinations: const [
              NavigationDestination(icon: Icon(Icons.inbox_outlined), label: '신청'),
              NavigationDestination(icon: Icon(Icons.people_outline), label: '고객'),
            ],
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
              const Text('전화 수신 카드를 켜 주세요', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              const SizedBox(height: 4),
              const Text('고객에게 전화가 오면 누구인지, 구독, 지난 상담이 화면 위에 떠요.', style: TextStyle(color: ink2)),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (perms['phone'] != true || perms['callLog'] != true)
                  FilledButton(onPressed: () async { await native.invokeMethod('requestPhone'); onChanged(); }, child: const Text('전화·통화 기록 권한')),
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
