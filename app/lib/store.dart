// n8n 앱 API 연결 + 휴대폰 저장(오프라인·전화 수신 카드용)
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'core.dart';

const apiBase = String.fromEnvironment('API_BASE');
const apiToken = String.fromEnvironment('API_TOKEN');
const native = MethodChannel('mtu/caller');

typedef Rec = Map<String, dynamic>;

class Store extends ChangeNotifier {
  List<Rec> customers = [], applications = [], subscriptions = [], consultations = [];
  bool loading = false;
  String? error;
  DateTime? syncedAt;

  Map<String, String> get _headers => {'X-MTU-Token': apiToken, 'Content-Type': 'application/json'};

  Future<void> init() async {
    final p = await SharedPreferences.getInstance();
    final cached = p.getString('data_cache');
    if (cached != null) _apply(jsonDecode(cached));
    await refresh();
  }

  Future<void> refresh() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final r = await http.get(Uri.parse('$apiBase/data'), headers: _headers).timeout(const Duration(seconds: 20));
      if (r.statusCode != 200) throw '서버 응답 ${r.statusCode}';
      final data = jsonDecode(utf8.decode(r.bodyBytes));
      _apply(data);
      syncedAt = DateTime.now();
      final p = await SharedPreferences.getInstance();
      await p.setString('data_cache', jsonEncode(data));
      await p.setString('caller_index', jsonEncode(buildCallerIndex(customers, subscriptions, consultations, DateTime.now())));
    } catch (e) {
      error = '불러오지 못했어요. 저장된 내용을 보여 드려요 ($e)';
    }
    loading = false;
    notifyListeners();
  }

  /// row['id'] 가 있으면 수정, 없으면 추가. 저장 뒤 다시 불러와요.
  Future<Rec> save(String table, Rec row) async {
    final r = await http
        .post(Uri.parse('$apiBase/save'), headers: _headers, body: jsonEncode({'table': table, 'row': row}))
        .timeout(const Duration(seconds: 20));
    final body = r.bodyBytes.isEmpty ? {} : jsonDecode(utf8.decode(r.bodyBytes));
    if (r.statusCode != 200 || body is! Map || body['id'] == null) throw '저장하지 못했어요 (${r.statusCode})';
    await refresh();
    return Rec.from(body);
  }

  void _apply(dynamic d) {
    List<Rec> rows(String k) => [for (final r in (d[k] as List? ?? [])) Rec.from(r)];
    customers = rows('customers');
    applications = rows('applications')..sort((a, b) => '${b['createdAt']}'.compareTo('${a['createdAt']}'));
    subscriptions = rows('subscriptions');
    consultations = rows('consultations');
  }

  Rec? customer(dynamic id) => customers.where((c) => '${c['id']}' == '$id').firstOrNull;
}
