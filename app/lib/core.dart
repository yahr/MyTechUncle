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

// ---------------- 통화 녹음 ----------------

/// 파일 이름이 이 고객 것인지: 전화번호 끝 8자리가 이름 속 숫자에 있거나, 고객 이름(첫 낱말)이 들어 있으면 true.
/// 번호의 하이픈·공백·+82 는 무시해요. 날짜·시간 숫자는 밑줄로 갈라져 있어 번호와 섞이지 않아요.
bool recordingMatches(String fileName, {String? phone, String? name}) {
  final p = normalizePhone(phone);
  if (p.length >= 8) {
    final digits = fileName.replaceAll(RegExp(r'(?<=\d)[-\s](?=\d)'), '');
    if (digits.contains(p.substring(p.length - 8))) return true;
  }
  final n = (name ?? '').split(RegExp(r'[\s()]+')).where((t) => t.isNotEmpty).firstOrNull ?? '';
  return n.length >= 2 && fileName.contains(n);
}

/// 공유된 텍스트에서 고객을 짐작해요. 번호(끝 8자리) 일치가 이름(첫 낱말, 2글자 이상) 일치보다 먼저예요.
Map<String, dynamic>? guessCustomer(String text, List<Map<String, dynamic>> customers) {
  final digits = text.replaceAll(RegExp(r'(?<=\d)[-\s](?=\d)'), '');
  for (final c in customers) {
    final p = normalizePhone('${c['phone'] ?? ''}');
    if (p.length >= 8 && digits.contains(p.substring(p.length - 8))) return c;
  }
  for (final c in customers) {
    final n = '${c['name'] ?? ''}'.split(RegExp(r'[\s()]+')).where((t) => t.isNotEmpty).firstOrNull ?? '';
    if (n.length >= 2 && text.contains(n)) return c;
  }
  return null;
}

/// 녹음 목록(최신순)을 '이 고객' 것 전부 + 나머지 최근 [limit]개로 나눠요.
({List<Map<String, dynamic>> mine, List<Map<String, dynamic>> others}) groupRecordings(List<Map<String, dynamic>> recs,
    {String? phone, String? name, int limit = 20}) {
  final mine = recs.where((r) => recordingMatches('${r['name']}', phone: phone, name: name)).toList();
  final others = recs.where((r) => !mine.contains(r)).take(limit).toList();
  return (mine: mine, others: others);
}

/// 새 상담 내역 '나눈 이야기' 칸 초안: 요약 + 받아쓴 원문
String consultationDraft(String summary, String transcript) {
  final s = summary.trim(), t = transcript.trim();
  return t.isEmpty ? s : '$s\n\n— 받아쓴 원문 —\n$t';
}

String formatDuration(Duration d) {
  final s = _2(d.inSeconds % 60), m = d.inHours > 0 ? _2(d.inMinutes % 60) : '${d.inMinutes % 60}';
  return d.inHours > 0 ? '${d.inHours}:$m:$s' : '$m:$s';
}

// ---------------- 이슈 상태 6단계 ----------------

/// 이슈 상태 6단계 (키 → 이름). 순서가 곧 진행 순서.
const issueStages = {
  'received': '일거리', 'reviewed': '업무', 'doing': '직업', 'done': '월급', 'feedback': '전문가', 'pride': '프라이드',
};

/// 단계별 위트 한 줄
const issueQuips = {
  'received': '누가 뭘 해 달래요. 아직은 심부름이에요.',
  'reviewed': '뭘 원하는지 알아들었어요. 이제 업무예요.',
  'doing': '손대고 있어요. 이게 밥벌이예요.',
  'done': '끝냈어요. 이걸로 밥을 먹어요.',
  'feedback': '고객이 한마디 남겼어요. 다음엔 더 잘해요.',
  'pride': '그래서 이 일을 해요.',
};

/// status → 0..5. 옛 값 'open'→0, 'closed'→3, 모르는 값→0
int issueStageIndex(dynamic status) {
  final i = issueStages.keys.toList().indexOf('$status');
  return i >= 0 ? i : (status == 'closed' ? 3 : 0);
}

/// 아직 안 끝난 이슈인가 (일거리·업무·직업)
bool issueActive(dynamic status) => issueStageIndex(status) <= 2;

/// 금액 300000 → '300,000원'. 비었거나 숫자가 아니면 '-'.
String formatWon(Object? v) {
  final n = num.tryParse('${v ?? ''}'.trim());
  if (n == null) return '-';
  final i = n.round();
  final s = i.abs().toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+$)'), (_) => ',');
  return '${i < 0 ? '-' : ''}$s원';
}
