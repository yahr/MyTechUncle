import 'package:flutter/material.dart';

import 'core.dart';
import 'ds.dart';
import 'ds_bars.dart';
import 'main.dart';
import 'store.dart';
import 'summary.dart';

const statusNames = {'new': '신규', 'contacted': '연락함', 'consulted': '첫 상담 완료', 'member': '회원 전환', 'hold': '보류', 'closed': '종료'};
String _today() => DateTime.now().toIso8601String().substring(0, 10);

/// 불러오는 중이면 글자 한 줄, 아니면 세무 앱과 같은 점선 빈 화면(DsNotice)
Widget _empty(String title, String message, {IconData icon = LucideIcons.inbox, bool error = false}) => store.loading && !error
    ? const Padding(padding: EdgeInsets.all(32), child: Text('불러오는 중이에요', textAlign: TextAlign.center, style: TextStyle(color: ink2)))
    : Padding(padding: const EdgeInsets.fromLTRB(16, 0, 16, 16), child: DsNotice(title: title, message: message, icon: icon, error: error));

/// DS .badge(점 + 연한 바탕·테두리). tone: 'warn' 진행·대기, 'ok' 완료·이용 중, 'neutral' 그 밖. null 이면 .tag(점 없음)
Widget _chip(String text, {String? tone}) {
  final (bg, fg, line) = switch (tone) { 'warn' => (warnSoft, warnInk, warnLine), 'ok' => (okSoft, okInk, okLine), _ => (subtle, ink2, tone == null ? subtle : stroke) };
  return Container(
    height: 24, padding: const EdgeInsets.symmetric(horizontal: 8),
    decoration: BoxDecoration(color: bg, border: Border.all(color: line), borderRadius: BorderRadius.circular(99)),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      if (tone != null) ...[Container(width: 6, height: 6, decoration: BoxDecoration(color: fg, shape: BoxShape.circle)), const SizedBox(width: 6)],
      Text(text, style: TextStyle(fontSize: 13, color: fg, fontWeight: tone == null ? FontWeight.w400 : FontWeight.w600)),
    ]),
  );
}

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
              ? ListView(children: [_empty('보여 줄 신청이 없어요', '무료 상담 예약이 들어오면 여기에 모여요. 위 칩으로 다른 상태도 볼 수 있어요.')])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final a = rows[i], c = store.customer(a['customer_id']);
                    return Card(
                      child: ListTile(
                        title: Text('${c?['company'] ?? '-'} ${c?['name'] ?? ''}'),
                        subtitle: Text('${a['slot'] ?? ''} · ${productNames[a['product']] ?? ''}\n${a['topic'] ?? ''}', maxLines: 3, overflow: TextOverflow.ellipsis),
                        isThreeLine: true,
                        trailing: _chip(statusNames[a['status']] ?? '${a['status']}', tone: a['status'] == 'new' ? 'warn' : 'neutral'),
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
  showDsSheet(
    context,
    title: '${c?['company'] ?? '-'} ${c?['name'] ?? ''}',
    children: (ctx) => [
      const SizedBox(height: 4),
      Text('${a['slot'] ?? ''} · ${productNames[a['product']] ?? ''}', style: const TextStyle(fontSize: 14, color: ink2)),
      if ('${a['topic'] ?? ''}'.isNotEmpty) ...[const SizedBox(height: 16), const DsLabel('상담 주제'), const SizedBox(height: 4), Text('${a['topic']}', style: const TextStyle(fontSize: 15, height: 1.6))],
      const SizedBox(height: 16),
      const DsLabel('상태'),
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
      if (c != null)
        DsSheetActions([
          OutlinedButton.icon(onPressed: () => callPhone(c['phone']), icon: const Icon(LucideIcons.phone, size: 20), label: const Text('전화하기')),
          FilledButton(
              onPressed: () {
                Navigator.pop(ctx);
                Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomerPage(id: c['id'])));
              },
              child: const Text('고객 보기')),
        ]),
    ],
  );
}

// ---------------- 이슈 ----------------
class IssuesTab extends StatefulWidget {
  const IssuesTab({super.key});
  @override
  State<IssuesTab> createState() => _IssuesTabState();
}

class _IssuesTabState extends State<IssuesTab> {
  String filter = 'active'; // 'active' | 'all' | 단계 키
  @override
  Widget build(BuildContext context) {
    final keys = issueStages.keys.toList();
    final counts = List.filled(6, 0);
    for (final i in store.issues) {
      counts[issueStageIndex(i['status'])]++;
    }
    final rows = store.issues.where((i) => switch (filter) {
          'all' => true,
          'active' => issueActive(i['status']),
          _ => keys[issueStageIndex(i['status'])] == filter,
        }).toList();
    final quip = issueQuips[issueStages.containsKey(filter) ? filter : 'received']!;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                for (var n = 0; n < 6; n++)
                  Expanded(
                    child: InkWell(
                      borderRadius: BorderRadius.circular(10),
                      onTap: () => setState(() => filter = keys[n]),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(color: filter == keys[n] ? brandSoft : null, borderRadius: BorderRadius.circular(10)),
                        child: Column(children: [
                          Text(issueStages[keys[n]]!, style: const TextStyle(fontSize: 11, color: ink2, fontWeight: FontWeight.w500)),
                          const SizedBox(height: 2),
                          Text('${counts[n]}', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: counts[n] > 0 ? mintInk : disabled)),
                        ]),
                      ),
                    ),
                  ),
              ]),
              Padding(padding: const EdgeInsets.fromLTRB(8, 8, 8, 4), child: Text(quip, style: const TextStyle(color: ink2, fontSize: 13))),
            ]),
          ),
        ),
      ),
      SizedBox(
        height: 48,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16), children: [
          for (final f in const {'active': '진행 중', 'all': '전체'}.entries)
            Padding(padding: const EdgeInsets.only(right: 8), child: ChoiceChip(label: Text(f.value), selected: filter == f.key, onSelected: (_) => setState(() => filter = f.key))),
        ]),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: store.refresh,
          child: rows.isEmpty
              ? ListView(children: [_empty('보여 줄 이슈가 없어요', '카톡방에서 "/해줘 내용"을 보내면 여기에 모여요.', icon: LucideIcons.listChecks)])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final r = rows[i], idx = issueStageIndex(r['status']);
                    return Card(
                      child: ListTile(
                        title: Text('${r['text'] ?? ''}', maxLines: 3, overflow: TextOverflow.ellipsis),
                        subtitle: Text('${r['room'] ?? ''} · ${r['sender'] ?? ''} · ${r['created_at'] ?? ''}'),
                        trailing: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.end, children: [
                          _chip(issueStages[keys[idx]]!, tone: idx <= 2 ? 'warn' : 'ok'),
                          const SizedBox(height: 6),
                          Row(mainAxisSize: MainAxisSize.min, children: [
                            for (var n = 0; n < 6; n++)
                              Container(
                                margin: EdgeInsets.only(left: n == 0 ? 0 : 3),
                                width: 6,
                                height: 6,
                                decoration: BoxDecoration(shape: BoxShape.circle, color: n <= idx ? mint : stroke),
                              ),
                          ]),
                        ]),
                        onTap: () => _issueSheet(context, r),
                      ),
                    );
                  },
                ),
        ),
      ),
    ]);
  }
}

void _issueSheet(BuildContext context, Rec r) {
  final keys = issueStages.keys.toList(), idx = issueStageIndex(r['status']);
  Future<void> move(BuildContext ctx, String key) async {
    Navigator.pop(ctx);
    try {
      await store.save('issues', {'id': r['id'], 'status': key});
      if (context.mounted) _toast(context, '${issueStages[key]}(으)로 옮겼어요');
    } catch (e) {
      if (context.mounted) _toast(context, '$e');
    }
  }

  showDsSheet(
    context,
    title: '${r['text'] ?? ''}',
    children: (ctx) => [
      const SizedBox(height: 4),
      Text('${r['room'] ?? ''} · ${r['sender'] ?? ''} · ${r['created_at'] ?? ''}', style: const TextStyle(fontSize: 14, color: ink2)),
      const SizedBox(height: 8),
      Text(issueQuips[keys[idx]]!, style: const TextStyle(fontSize: 14, color: mintInk)),
      const SizedBox(height: 16),
      const DsLabel('단계'),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final s in issueStages.entries) ChoiceChip(label: Text(s.value), selected: keys[idx] == s.key, onSelected: (_) => move(ctx, s.key)),
      ]),
      DsSheetActions([
        OutlinedButton(onPressed: () => Navigator.pop(ctx), child: const Text('닫기')),
        if (idx < keys.length - 1) FilledButton(onPressed: () => move(ctx, keys[idx + 1]), child: const Text('다음 단계로')),
      ]),
    ],
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
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const CustomerForm())),
            icon: const Icon(LucideIcons.userPlus, size: 24),
            label: const Text('고객 추가'),
          ),
          const SizedBox(height: 12),
          TextField(decoration: const InputDecoration(prefixIcon: Icon(LucideIcons.search, size: 20), hintText: '회사·이름·번호로 찾기', isDense: true), onChanged: (v) => setState(() => q = v.trim())),
        ]),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: store.refresh,
          child: rows.isEmpty
              ? ListView(children: [(q.isNotEmpty ? _empty('찾는 고객이 없어요', '회사·이름·번호를 다시 확인해 주세요.', icon: LucideIcons.search) : _empty('아직 고객이 없어요', '위의 "고객 추가"로 첫 고객을 등록해 주세요.', icon: LucideIcons.users))])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 96),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final c = rows[i];
                    return Card(
                      child: ListTile(
                        title: Text('${c['company'] ?? ''} ${c['name'] ?? ''}'),
                        subtitle: Text(subscriptionLabel(ofCustomer(store.subscriptions, c['id']), DateTime.now())),
                        trailing: const Icon(LucideIcons.chevronRight),
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

/// 다른 앱에서 공유받은 텍스트를 어느 고객 상담 기록에 넣을지 고르는 화면
class SharedTextPage extends StatefulWidget {
  const SharedTextPage({super.key, required this.text});
  final String text;
  @override
  State<SharedTextPage> createState() => _SharedTextPageState();
}

class _SharedTextPageState extends State<SharedTextPage> {
  String q = '';

  Widget _tile(Map<String, dynamic> c) => Card(
        child: ListTile(
          title: Text('${c['company'] ?? ''} ${c['name'] ?? ''}'.trim()),
          subtitle: Text('${c['phone'] ?? ''}'),
          trailing: const Icon(LucideIcons.chevronRight),
          onTap: () => Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ConsultationForm(customerId: c['id'], draft: widget.text))),
        ),
      );

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: store,
        builder: (context, _) {
          final guess = guessCustomer(widget.text, store.customers);
          final rows = store.customers.where((c) => c != guess && (q.isEmpty || '${c['company']} ${c['name']} ${c['phone']}'.contains(q))).toList()
            ..sort((a, b) => '${a['company']}'.compareTo('${b['company']}'));
          return Scaffold(
            appBar: const DsAppBar(title: '공유받은 내용'),
            body: ListView(padding: EdgeInsets.fromLTRB(16, 0, 16, 32 + MediaQuery.paddingOf(context).bottom), children: [
              Card(child: Padding(padding: const EdgeInsets.all(12), child: Text(widget.text, maxLines: 6, overflow: TextOverflow.ellipsis, style: const TextStyle(color: ink2)))),
              const Padding(padding: EdgeInsets.only(top: 16, bottom: 8), child: Text('누구와 나눈 이야기인가요', style: TextStyle(fontFamily: head, fontSize: 18, fontWeight: FontWeight.w600))),
              TextField(decoration: const InputDecoration(prefixIcon: Icon(LucideIcons.search), hintText: '회사·이름·번호로 찾기', isDense: true), onChanged: (v) => setState(() => q = v.trim())),
              const SizedBox(height: 8),
              if (store.customers.isEmpty)
                _empty('아직 고객이 없어요', '고객 탭에서 먼저 추가해 주세요.', icon: LucideIcons.users)
              else ...[
                if (guess != null) ...[
                  const Padding(padding: EdgeInsets.symmetric(vertical: 4), child: Text('이 고객 같아요', style: TextStyle(color: mintInk, fontWeight: FontWeight.w600))),
                  _tile(guess),
                  const SizedBox(height: 8),
                ],
                for (final c in rows) _tile(c),
              ],
            ]),
          );
        },
      );
}

class CustomerPage extends StatelessWidget {
  const CustomerPage({super.key, required this.id});
  final dynamic id;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: store,
        builder: (context, _) {
          final c = store.customer(id);
          if (c == null) return Scaffold(appBar: const DsAppBar(), body: Padding(padding: const EdgeInsets.only(top: 16), child: _empty('고객을 찾지 못했어요', '목록을 새로 불러온 뒤 다시 열어 주세요.', error: true)));
          final subs = ofCustomer(store.subscriptions, id)..sort((a, b) => '${b['start_date']}'.compareTo('${a['start_date']}'));
          final cons = sortedConsultations(ofCustomer(store.consultations, id));
          return Scaffold(
            appBar: DsAppBar(title: '고객', actions: [
              DsIconBtn(icon: LucideIcons.pencil, label: '고객 정보 수정', onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CustomerForm(row: c)))),
            ]),
            bottomNavigationBar: const _CallBar(),
            body: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 32), children: [
              DsCard(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  // 배지가 길면(구독 기간·D-day) 제목 아래 줄로 내려간다 — Row 로 두면 회사명이 한 글자씩 꺾였다(2026-11-13 갤럭시)
                  Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
                    Text('${c['company'] ?? ''}', style: const TextStyle(fontFamily: head, fontSize: 22, fontWeight: FontWeight.w700, height: 1.4)),
                    _chip(subscriptionLabel(subs, DateTime.now()), tone: subs.isEmpty ? 'neutral' : 'ok'),
                  ]),
                  const SizedBox(height: 12),
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Expanded(child: DsKv('대표', Text('${c['name'] ?? '-'}'))),
                    Expanded(child: DsKv('업종', Text('${(c['industry'] ?? '') == '' ? '-' : c['industry']}'))),
                  ]),
                  const SizedBox(height: 16),
                  Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Expanded(
                      child: DsKv('전화', '${c['phone'] ?? ''}'.isEmpty
                          ? const Text('-')
                          : InkWell(
                              onTap: () => callPhone(c['phone']),
                              child: Text('${c['phone']}', style: const TextStyle(color: mintInk, decoration: TextDecoration.underline, decorationColor: mintInk)),
                            )),
                    ),
                    Expanded(child: DsKv('이메일', Text('${(c['email'] ?? '') == '' ? '-' : c['email']}', maxLines: 1, overflow: TextOverflow.ellipsis))),
                  ]),
                  if ('${c['memo'] ?? ''}'.isNotEmpty) ...[const SizedBox(height: 16), DsKv('메모', Text('${c['memo']}'))],
                  const SizedBox(height: 16),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    FilledButton.icon(
                        onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConsultationForm(customerId: c['id']))),
                        icon: const Icon(LucideIcons.notebookPen, size: 20),
                        label: const Text('상담 기록')),
                    OutlinedButton.icon(
                        onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => RecordingPickerPage(customer: c))),
                        icon: const Icon(LucideIcons.mic, size: 20),
                        label: const Text('녹음 요약')),
                  ]),
                ]),
              ),
              const SizedBox(height: 16),
              _Section(
                title: '구독',
                action: TextButton.icon(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SubscriptionForm(customerId: c['id']))), icon: const Icon(LucideIcons.plus), label: const Text('구독 추가')),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  if (subs.isEmpty) const Text('아직 구독이 없어요. 입금을 확인하면 "구독 추가"로 남겨 주세요.', style: TextStyle(color: muted, fontSize: 14)),
                  for (final s in subs)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${productNames[s['product']] ?? s['product']} · ${s['start_date']} ~ ${s['end_date']}'),
                      subtitle: Text('${formatWon(s['amount'])} · ${s['paid'] == true ? '입금 확인' : '입금 대기'}${s['status'] == 'cancelled' ? ' · 해지' : ''}'),
                      trailing: const Icon(LucideIcons.pencil, size: 18),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SubscriptionForm(customerId: c['id'], row: s))),
                    ),
                ]),
              ),
              const SizedBox(height: 16),
              _Section(
                title: '상담 내역 ${cons.length}건',
                child: cons.isEmpty
                    ? const Text('아직 기록이 없어요. 통화 뒤 "상담 기록"으로 남겨 주세요.', style: TextStyle(color: muted, fontSize: 14))
                    : Column(children: [
                        for (final r in cons)
                          InkWell(
                            onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ConsultationForm(customerId: c['id'], row: r))),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                SizedBox(width: 84, child: Text('${r['date'] ?? ''}', style: const TextStyle(color: mintInk, fontWeight: FontWeight.w500, fontSize: 13))),
                                Expanded(
                                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                    Text('${r['title'] ?? ''}'),
                                    if ('${r['content'] ?? ''}'.isNotEmpty) Text('${r['content']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: ink2)), // 전문은 눌러서 연다
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
  Widget build(BuildContext context) => DsCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Expanded(child: Text(title, style: const TextStyle(fontFamily: head, fontSize: 18, fontWeight: FontWeight.w600))), if (action != null) action!]),
          const SizedBox(height: 12),
          child,
        ]),
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
        appBar: DsAppBar(title: widget.title),
        body: ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.paddingOf(context).bottom), children: [
          for (final f in widget.fields)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: DsField(
                label: f.$2,
                controller: ctl[f.$1]!,
                minLines: f.multiline ? 4 : 1,
                maxLines: f.multiline ? 12 : 1,
                keyboardType: f.number ? TextInputType.number : (f.multiline ? TextInputType.multiline : TextInputType.text),
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
  const ConsultationForm({super.key, required this.customerId, this.row, this.draft});
  final dynamic customerId;
  final Rec? row;
  final String? draft; // 녹음 요약으로 채운 '나눈 이야기' 초안(저장 전에 고쳐요)
  @override
  Widget build(BuildContext context) => _FormPage(
        title: row == null ? '상담 기록' : '상담 기록 수정',
        table: 'consultations',
        row: row,
        extra: {'customer_id': customerId, if (row == null) 'date': _today(), if (draft != null) 'content': draft},
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
        appBar: DsAppBar(title: widget.row == null ? '구독 추가' : '구독 수정'),
        body: ListView(padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.paddingOf(context).bottom), children: [
          SegmentedButton<String>(
            segments: const [ButtonSegment(value: 'annual', label: Text('연간 기술고문')), ButtonSegment(value: 'founder', label: Text('Founder'))],
            selected: {product},
            showSelectedIcon: false, // .seg — 체크 표시 없이 바탕·글자색으로
            onSelectionChanged: (v) => setState(() {
              product = v.first;
              _fill();
            }),
          ),
          const SizedBox(height: 16),
          DsField(label: '시작일', hint: 'YYYY-MM-DD', controller: start, onChanged: (_) {
            if (widget.row == null) setState(_fill);
          }),
          const SizedBox(height: 16),
          DsField(label: '종료일', hint: 'YYYY-MM-DD', controller: end),
          const SizedBox(height: 16),
          DsField(label: '금액 (원)', controller: amount, keyboardType: TextInputType.number),
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
          // 쉴 때도 아랫 안전 영역만큼은 자리를 잡는다 — 0 이면 Scaffold 가 본문 아래 여백을 빼서 내용이 시스템 막대 밑으로 들어간다
          if (state == 'idle') return const SafeArea(top: false, child: SizedBox(width: double.infinity));
          const red = danger, green = ok;
          ButtonStyle style(Color c) => FilledButton.styleFrom(backgroundColor: c, minimumSize: const Size.fromHeight(56),
              textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700));
          return SafeArea(
            child: Container(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
              decoration: const BoxDecoration(color: surface, border: Border(top: BorderSide(color: stroke))),
              child: state == 'ringing'
                  ? Row(children: [
                      Expanded(child: FilledButton.icon(style: style(red), onPressed: () => _do(context, 'endCall', '거절하지 못했어요. 통화 화면에서 거절해 주세요'),
                          icon: const Icon(LucideIcons.phoneOff), label: const Text('거절'))),
                      const SizedBox(width: 12),
                      Expanded(child: FilledButton.icon(style: style(green), onPressed: () => _do(context, 'answerCall', '받지 못했어요. 통화 화면에서 받아 주세요'),
                          icon: const Icon(LucideIcons.phone), label: const Text('받기'))),
                    ])
                  : FilledButton.icon(style: style(red), onPressed: () => _do(context, 'endCall', '끊지 못했어요. 통화 화면에서 끊어 주세요'),
                      icon: const Icon(LucideIcons.phoneOff), label: const Text('통화 끊기')),
            ),
          );
        },
      );
}
