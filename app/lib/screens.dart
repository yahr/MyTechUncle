import 'package:flutter/material.dart';

import 'core.dart';
import 'main.dart';
import 'store.dart';

const statusNames = {'new': '신규', 'contacted': '연락함', 'consulted': '첫 상담 완료', 'member': '회원 전환', 'hold': '보류', 'closed': '종료'};
String _today() => DateTime.now().toIso8601String().substring(0, 10);

Widget _empty(String text) => Center(child: Padding(padding: const EdgeInsets.all(32), child: Text(text, style: const TextStyle(color: ink2), textAlign: TextAlign.center)));

Widget _chip(String text, {bool strong = false}) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: strong ? const Color(0xFFE6FBF8) : const Color(0xFFF0F3F6), borderRadius: BorderRadius.circular(99)),
      child: Text(text, style: TextStyle(fontSize: 12, color: strong ? mintInk : ink2, fontWeight: FontWeight.w600)),
    );

void _toast(BuildContext context, String msg) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

// ---------------- 신청 ----------------
class ApplicationsTab extends StatefulWidget {
  const ApplicationsTab({super.key});
  @override
  State<ApplicationsTab> createState() => _ApplicationsTabState();
}

class _ApplicationsTabState extends State<ApplicationsTab> {
  String filter = 'open';
  @override
  Widget build(BuildContext context) {
    final rows = store.applications.where((a) => switch (filter) {
          'open' => !['member', 'closed'].contains(a['status']),
          'all' => true,
          _ => a['status'] == filter,
        }).toList();
    return Column(children: [
      SizedBox(
        height: 48,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
          for (final f in {'open': '진행 중', ...statusNames, 'all': '전체'}.entries)
            Padding(padding: const EdgeInsets.only(right: 8), child: ChoiceChip(label: Text(f.value), selected: filter == f.key, onSelected: (_) => setState(() => filter = f.key))),
        ]),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: store.refresh,
          child: rows.isEmpty
              ? ListView(children: [_empty(store.loading ? '불러오는 중이에요' : '신청이 없어요')])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final a = rows[i], c = store.customer(a['customer_id']);
                    return Card(
                      child: ListTile(
                        title: Text('${c?['company'] ?? '-'} ${c?['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: Text('${a['slot'] ?? ''} · ${productNames[a['product']] ?? ''}\n${a['topic'] ?? ''}', maxLines: 3, overflow: TextOverflow.ellipsis),
                        isThreeLine: true,
                        trailing: _chip(statusNames[a['status']] ?? '${a['status']}', strong: a['status'] == 'new'),
                        onTap: () => _applicationSheet(context, a),
                      ),
                    );
                  },
                ),
        ),
      ),
    ]);
  }
}

void _applicationSheet(BuildContext context, Rec a) {
  final c = store.customer(a['customer_id']);
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${c?['company'] ?? '-'} ${c?['name'] ?? ''}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text('${a['slot'] ?? ''} · ${productNames[a['product']] ?? ''}', style: const TextStyle(color: ink2)),
          const SizedBox(height: 12),
          Text('${a['topic'] ?? ''}'),
          const SizedBox(height: 16),
          const Text('상태', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final s in statusNames.entries)
              ChoiceChip(
                label: Text(s.value),
                selected: a['status'] == s.key,
                onSelected: (_) async {
                  Navigator.pop(ctx);
                  try {
                    await store.save('applications', {'id': a['id'], 'status': s.key});
                    if (context.mounted) _toast(context, '${s.value}(으)로 바꿨어요');
                  } catch (e) {
                    if (context.mounted) _toast(context, '$e');
                  }
                },
              ),
          ]),
          const SizedBox(height: 16),
          if (c != null)
            Row(children: [
              Expanded(child: OutlinedButton.icon(onPressed: () => callPhone(c['phone']), icon: const Icon(Icons.call), label: const Text('전화하기'))),
              const SizedBox(width: 8),
              Expanded(
                  child: FilledButton(
                      onPressed: () {
                        Navigator.pop(ctx);
                        Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomerPage(id: c['id'])));
                      },
                      child: const Text('고객 보기'))),
            ]),
        ]),
      ),
    ),
  );
}

// ---------------- 고객 ----------------
class CustomersTab extends StatefulWidget {
  const CustomersTab({super.key});
  @override
  State<CustomersTab> createState() => _CustomersTabState();
}

class _CustomersTabState extends State<CustomersTab> {
  String q = '';
  @override
  Widget build(BuildContext context) {
    final rows = store.customers.where((c) => q.isEmpty || '${c['company']} ${c['name']} ${c['phone']}'.contains(q)).toList()
      ..sort((a, b) => '${a['company']}'.compareTo('${b['company']}'));
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
        child: TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: '회사·이름·번호로 찾기', isDense: true), onChanged: (v) => setState(() => q = v.trim())),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: store.refresh,
          child: rows.isEmpty
              ? ListView(children: [_empty(store.loading ? '불러오는 중이에요' : '고객이 없어요')])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final c = rows[i];
                    return Card(
                      child: ListTile(
                        title: Text('${c['company'] ?? ''} ${c['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: Text(subscriptionLabel(ofCustomer(store.subscriptions, c['id']), DateTime.now())),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomerPage(id: c['id']))),
                      ),
                    );
                  },
                ),
        ),
      ),
    ]);
  }
}

class CustomerPage extends StatelessWidget {
  const CustomerPage({super.key, required this.id});
  final dynamic id;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: store,
        builder: (context, _) {
          final c = store.customer(id);
          if (c == null) return Scaffold(appBar: AppBar(), body: _empty('고객을 찾지 못했어요'));
          final subs = ofCustomer(store.subscriptions, id)..sort((a, b) => '${b['start_date']}'.compareTo('${a['start_date']}'));
          final cons = sortedConsultations(ofCustomer(store.consultations, id));
          return Scaffold(
            appBar: AppBar(actions: [
              IconButton(tooltip: '고객 정보 수정', icon: const Icon(Icons.edit_outlined), onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomerForm(row: c)))),
            ]),
            bottomNavigationBar: const _CallBar(),
            floatingActionButton: FloatingActionButton.extended(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConsultationForm(customerId: c['id']))),
              icon: const Icon(Icons.edit_note),
              label: const Text('상담 기록'),
            ),
            body: ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 96), children: [
              Text('${c['company'] ?? ''}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
              Text('${c['name'] ?? ''}${(c['industry'] ?? '') == '' ? '' : ' · ${c['industry']}'}', style: const TextStyle(color: ink2, fontSize: 16)),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if ('${c['phone'] ?? ''}'.isNotEmpty) OutlinedButton.icon(onPressed: () => callPhone(c['phone']), icon: const Icon(Icons.call, size: 18), label: Text('${c['phone']}')),
                if ('${c['email'] ?? ''}'.isNotEmpty) _chip('${c['email']}'),
              ]),
              if ('${c['memo'] ?? ''}'.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 12), child: Text('${c['memo']}', style: const TextStyle(color: ink2))),
              const SizedBox(height: 24),
              _Section(
                title: '구독',
                action: TextButton.icon(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SubscriptionForm(customerId: c['id']))), icon: const Icon(Icons.add), label: const Text('구독 추가')),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  _chip(subscriptionLabel(subs, DateTime.now()), strong: true),
                  for (final s in subs)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${productNames[s['product']] ?? s['product']} · ${s['start_date']} ~ ${s['end_date']}'),
                      subtitle: Text('${s['amount'] ?? '-'}원 · ${s['paid'] == true ? '입금 확인' : '입금 대기'}${s['status'] == 'cancelled' ? ' · 해지' : ''}'),
                      trailing: const Icon(Icons.edit_outlined, size: 18),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SubscriptionForm(customerId: c['id'], row: s))),
                    ),
                ]),
              ),
              const SizedBox(height: 16),
              _Section(
                title: '상담 내역 ${cons.length}건',
                child: cons.isEmpty
                    ? const Text('아직 기록이 없어요. 통화 뒤 "상담 기록"으로 남겨 주세요.', style: TextStyle(color: ink2))
                    : Column(children: [
                        for (final r in cons)
                          InkWell(
                            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConsultationForm(customerId: c['id'], row: r))),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                SizedBox(width: 84, child: Text('${r['date'] ?? ''}', style: const TextStyle(color: mintInk, fontWeight: FontWeight.w700, fontSize: 13))),
                                Expanded(
                                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                    Text('${r['title'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                                    if ('${r['content'] ?? ''}'.isNotEmpty) Text('${r['content']}'),
                                    if ('${r['next_action'] ?? ''}'.isNotEmpty) Text('다음 할 일: ${r['next_action']}', style: const TextStyle(color: ink2)),
                                  ]),
                                ),
                              ]),
                            ),
                          ),
                      ]),
              ),
            ]),
          );
        },
      );
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child, this.action});
  final String title;
  final Widget child;
  final Widget? action;
  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [Expanded(child: Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700))), if (action != null) action!]),
            const SizedBox(height: 8),
            child,
          ]),
        ),
      );
}

// ---------------- 입력 폼 ----------------
/// 칸 정의 하나로 그리는 공용 폼. 저장하면 이전 화면으로 돌아가요.
class _FormPage extends StatefulWidget {
  const _FormPage({required this.title, required this.table, required this.fields, this.row, this.extra = const {}});
  final String title, table;
  final List<(String key, String label, {bool multiline, bool number})> fields;
  final Rec? row;
  final Rec extra;
  @override
  State<_FormPage> createState() => _FormPageState();
}

class _FormPageState extends State<_FormPage> {
  late final ctl = {for (final f in widget.fields) f.$1: TextEditingController(text: '${widget.row?[f.$1] ?? widget.extra[f.$1] ?? ''}')};
  bool saving = false;

  Future<void> _save() async {
    setState(() => saving = true);
    final row = <String, dynamic>{...widget.extra, for (final e in ctl.entries) e.key: e.value.text.trim()};
    if (widget.row != null) row['id'] = widget.row!['id'];
    try {
      await store.save(widget.table, row);
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) _toast(context, '$e');
    }
    if (mounted) setState(() => saving = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.title)),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          for (final f in widget.fields)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TextField(
                controller: ctl[f.$1],
                minLines: f.multiline ? 4 : 1,
                maxLines: f.multiline ? 12 : 1,
                keyboardType: f.number ? TextInputType.number : (f.multiline ? TextInputType.multiline : TextInputType.text),
                decoration: InputDecoration(labelText: f.$2),
              ),
            ),
          const SizedBox(height: 8),
          FilledButton(onPressed: saving ? null : _save, child: Text(saving ? '저장하는 중' : '저장')),
        ]),
      );
}

class CustomerForm extends StatelessWidget {
  const CustomerForm({super.key, this.row});
  final Rec? row;
  @override
  Widget build(BuildContext context) => _FormPage(
        title: row == null ? '고객 추가' : '고객 정보 수정',
        table: 'customers',
        row: row,
        fields: const [
          ('company', '회사', multiline: false, number: false),
          ('name', '이름 (직함)', multiline: false, number: false),
          ('phone', '휴대폰', multiline: false, number: true),
          ('email', '이메일', multiline: false, number: false),
          ('industry', '업종', multiline: false, number: false),
          ('memo', '메모 (쓰는 시스템, 직원 수 등)', multiline: true, number: false),
        ],
      );
}

class ConsultationForm extends StatelessWidget {
  const ConsultationForm({super.key, required this.customerId, this.row});
  final dynamic customerId;
  final Rec? row;
  @override
  Widget build(BuildContext context) => _FormPage(
        title: row == null ? '상담 기록' : '상담 기록 수정',
        table: 'consultations',
        row: row,
        extra: {'customer_id': customerId, if (row == null) 'date': _today()},
        fields: const [
          ('date', '날짜 (YYYY-MM-DD)', multiline: false, number: false),
          ('title', '주제 한 줄', multiline: false, number: false),
          ('content', '나눈 이야기', multiline: true, number: false),
          ('next_action', '다음 할 일', multiline: false, number: false),
        ],
      );
}

class SubscriptionForm extends StatefulWidget {
  const SubscriptionForm({super.key, required this.customerId, this.row});
  final dynamic customerId;
  final Rec? row;
  @override
  State<SubscriptionForm> createState() => _SubscriptionFormState();
}

class _SubscriptionFormState extends State<SubscriptionForm> {
  late String product = '${widget.row?['product'] ?? 'annual'}';
  late bool paid = widget.row?['paid'] == true;
  late bool cancelled = widget.row?['status'] == 'cancelled';
  late final start = TextEditingController(text: '${widget.row?['start_date'] ?? _today()}');
  late final end = TextEditingController(text: '${widget.row?['end_date'] ?? ''}');
  late final amount = TextEditingController(text: '${widget.row?['amount'] ?? ''}');
  bool saving = false;

  @override
  void initState() {
    super.initState();
    if (widget.row == null) _fill();
  }

  // 상품을 고르면 끝나는 날·금액을 채워요 (연간 1년, Founder 10년)
  void _fill() {
    final s = DateTime.tryParse(start.text);
    if (s != null) {
      final years = product == 'founder' ? 10 : 1;
      end.text = DateTime(s.year + years, s.month, s.day - 1).toIso8601String().substring(0, 10);
    }
    amount.text = product == 'founder' ? '1000000' : '300000';
  }

  Future<void> _save() async {
    setState(() => saving = true);
    try {
      await store.save('subscriptions', {
        if (widget.row != null) 'id': widget.row!['id'],
        'customer_id': widget.customerId,
        'product': product,
        'start_date': start.text.trim(),
        'end_date': end.text.trim(),
        'amount': amount.text.trim(),
        'paid': paid,
        'status': cancelled ? 'cancelled' : 'active',
      });
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) _toast(context, '$e');
    }
    if (mounted) setState(() => saving = false);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(widget.row == null ? '구독 추가' : '구독 수정')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          SegmentedButton<String>(
            segments: const [ButtonSegment(value: 'annual', label: Text('연간 기술고문')), ButtonSegment(value: 'founder', label: Text('Founder'))],
            selected: {product},
            onSelectionChanged: (v) => setState(() {
              product = v.first;
              _fill();
            }),
          ),
          const SizedBox(height: 16),
          TextField(controller: start, decoration: const InputDecoration(labelText: '시작일 (YYYY-MM-DD)'), onChanged: (_) {
            if (widget.row == null) setState(_fill);
          }),
          const SizedBox(height: 12),
          TextField(controller: end, decoration: const InputDecoration(labelText: '종료일 (YYYY-MM-DD)')),
          const SizedBox(height: 12),
          TextField(controller: amount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: '금액 (원)')),
          SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('입금 확인'), value: paid, onChanged: (v) => setState(() => paid = v)),
          if (widget.row != null) SwitchListTile(contentPadding: EdgeInsets.zero, title: const Text('해지'), value: cancelled, onChanged: (v) => setState(() => cancelled = v)),
          const SizedBox(height: 8),
          FilledButton(onPressed: saving ? null : _save, child: Text(saving ? '저장하는 중' : '저장')),
        ]),
      );
}

/// 전화가 울리면 [거절][받기], 통화 중이면 [통화 끊기]. 통화가 없으면 아무것도 안 보여요.
class _CallBar extends StatelessWidget {
  const _CallBar();

  Future<void> _do(BuildContext context, String method, String fail) async {
    final ok = await native.invokeMethod<bool>(method).catchError((_) => false);
    if (ok != true && context.mounted) _toast(context, fail);
  }

  @override
  Widget build(BuildContext context) => ValueListenableBuilder<String>(
        valueListenable: callState,
        builder: (context, state, _) {
          if (state == 'idle') return const SizedBox.shrink();
          const red = Color(0xFFC0392B), green = Color(0xFF22A06B);
          ButtonStyle style(Color c) => FilledButton.styleFrom(backgroundColor: c, minimumSize: const Size.fromHeight(56),
              textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700));
          return SafeArea(
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
              decoration: const BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: Color(0xFFE1E6EC)))),
              child: state == 'ringing'
                  ? Row(children: [
                      Expanded(child: FilledButton.icon(style: style(red), onPressed: () => _do(context, 'endCall', '거절하지 못했어요. 통화 화면에서 거절해 주세요'),
                          icon: const Icon(Icons.call_end), label: const Text('거절'))),
                      const SizedBox(width: 12),
                      Expanded(child: FilledButton.icon(style: style(green), onPressed: () => _do(context, 'answerCall', '받지 못했어요. 통화 화면에서 받아 주세요'),
                          icon: const Icon(Icons.call), label: const Text('받기'))),
                    ])
                  : FilledButton.icon(style: style(red), onPressed: () => _do(context, 'endCall', '끊지 못했어요. 통화 화면에서 끊어 주세요'),
                      icon: const Icon(Icons.call_end), label: const Text('통화 끊기')),
            ),
          );
        },
      );
}
