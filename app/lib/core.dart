// 화면과 전화 수신 카드가 같이 쓰는 순수 로직 (test/core_test.dart)

const productNames = {'annual': '연간 기술고문', 'founder': 'Founder 기술고문', 'free': '무료 상담'};

String normalizePhone(String? raw) {
  var d = (raw ?? '').replaceAll(RegExp(r'\D'), '');
  if (d.startsWith('82') && d.length >= 11) d = '0${d.substring(2)}';
  return d;
}

DateTime? _date(dynamic s) => DateTime.tryParse('${s ?? ''}');
String _ymd(DateTime d) => '${d.year}-${_2(d.month)}-${_2(d.day)}';
String _2(int n) => n.toString().padLeft(2, '0');

/// 그 고객의 지금 구독 한 줄. 이용 중 > 시작 예정 > 만료 > 없음 순.
String subscriptionLabel(List<Map<String, dynamic>> subs, DateTime today) {
  final day = DateTime(today.year, today.month, today.day);
  final live = subs.where((s) => s['status'] != 'cancelled' && _date(s['start_date']) != null && _date(s['end_date']) != null).toList();
  String name(Map s) => productNames[s['product']] ?? '${s['product']}';

  final active = live.where((s) => !_date(s['start_date'])!.isAfter(day) && !_date(s['end_date'])!.isBefore(day)).toList()
    ..sort((a, b) => _date(b['end_date'])!.compareTo(_date(a['end_date'])!));
  if (active.isNotEmpty) {
    final s = active.first, end = _date(s['end_date'])!;
    final left = end.difference(day).inDays;
    return '${name(s)} · ${_ymd(end)}까지 (${left == 0 ? 'D-day' : 'D-$left'})${s['paid'] == true ? '' : ' · 입금 대기'}';
  }
  final future = live.where((s) => _date(s['start_date'])!.isAfter(day)).toList()
    ..sort((a, b) => _date(a['start_date'])!.compareTo(_date(b['start_date'])!));
  if (future.isNotEmpty) return '${name(future.first)} · ${_ymd(_date(future.first['start_date'])!)} 시작 예정';
  if (live.isNotEmpty) {
    final last = live.map((s) => _date(s['end_date'])!).reduce((a, b) => a.isAfter(b) ? a : b);
    return '만료 · ${_ymd(last)}';
  }
  return '구독 없음';
}

List<Map<String, dynamic>> ofCustomer(List<Map<String, dynamic>> rows, dynamic id) =>
    rows.where((r) => '${r['customer_id']}' == '$id').toList();

/// 상담 내역 최신순
List<Map<String, dynamic>> sortedConsultations(List<Map<String, dynamic>> cons) =>
    [...cons]..sort((a, b) => '${b['date']}'.compareTo('${a['date']}'));

/// 전화 수신 카드용 색인: 번호 → {id, title, sub, lines(최근 3건)}
Map<String, Map<String, dynamic>> buildCallerIndex(List<Map<String, dynamic>> customers, List<Map<String, dynamic>> subs,
    List<Map<String, dynamic>> cons, DateTime today) {
  final out = <String, Map<String, dynamic>>{};
  for (final c in customers) {
    final phone = normalizePhone(c['phone']);
    if (phone.isEmpty) continue;
    final lines = sortedConsultations(ofCustomer(cons, c['id']))
        .take(3)
        .map((r) => '${'${r['date']}'.length >= 10 ? '${r['date']}'.substring(5, 10) : r['date']} ${r['title'] ?? ''}'.trim())
        .toList();
    out[phone] = {
      'id': c['id'],
      'title': '${c['company'] ?? ''} ${c['name'] ?? ''}'.trim(),
      'sub': subscriptionLabel(ofCustomer(subs, c['id']), today),
      'lines': lines,
    };
  }
  return out;
}
