// 통화 녹음 요약: 갤럭시 통화 녹음 중 하나를 골라 n8n 으로 보내고, 요약을 새 상담 기록 초안으로 열어요.
// 버튼을 눌렀을 때만 동작하고, 녹음 원본은 휴대폰에만 둬요(앱은 고른 한 건을 캐시에 잠깐 복사했다가 지워요).
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import 'core.dart';
import 'main.dart';
import 'screens.dart';
import 'store.dart';

class SummaryError implements Exception {
  SummaryError(this.message);
  final String message;
  @override
  String toString() => message;
}

/// 파일을 /summarize 로 보내 {transcript, summary} 를 받아요. 업로드가 끝나면(성공·실패 모두) 캐시 파일을 지워요.
Future<({String transcript, String summary})> summarizeRecording(String path, {required String customerName, required String company}) async {
  try {
    final r = await Future(() async {
      final req = http.MultipartRequest('POST', Uri.parse('$apiBase/summarize'))
        ..headers['X-MTU-Token'] = apiToken
        ..fields['customer_name'] = customerName
        ..fields['company'] = company
        ..files.add(await http.MultipartFile.fromPath('audio', path));
      return http.Response.fromStream(await req.send());
    }).timeout(const Duration(minutes: 3));
    dynamic body;
    try {
      body = jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {}
    if (r.statusCode != 200 || body is! Map || '${body['summary'] ?? ''}'.trim().isEmpty) {
      final why = body is Map && body['error'] != null ? ' (${body['error']})' : '';
      throw SummaryError('서버에서 요약하지 못했어요$why. 잠시 뒤 다시 해 주세요 (${r.statusCode})');
    }
    return (transcript: '${body['transcript'] ?? ''}', summary: '${body['summary']}');
  } on TimeoutException {
    throw SummaryError('시간이 오래 걸려 멈췄어요. 녹음이 길거나 서버가 바빠요. 잠시 뒤 다시 해 주세요');
  } on SocketException {
    throw SummaryError('인터넷에 연결되지 않았어요. 연결을 확인하고 다시 해 주세요');
  } on http.ClientException {
    throw SummaryError('서버에 연결하지 못했어요. 인터넷 연결을 확인하고 다시 해 주세요');
  } finally {
    try {
      File(path).deleteSync();
    } catch (_) {}
  }
}

class RecordingPickerPage extends StatefulWidget {
  const RecordingPickerPage({super.key, required this.customer});
  final Rec customer;
  @override
  State<RecordingPickerPage> createState() => _RecordingPickerPageState();
}

class _RecordingPickerPageState extends State<RecordingPickerPage> with WidgetsBindingObserver {
  bool loading = true, denied = false;
  String? error;
  List<Rec> mine = [], others = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load(ask: true);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // 설정에서 권한을 켜고 돌아오면 다시 불러와요
  @override
  void didChangeAppLifecycleState(AppLifecycleState s) {
    if (s == AppLifecycleState.resumed && denied) _load(ask: false);
  }

  Future<void> _load({required bool ask}) async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      var ok = await native.invokeMethod<bool>('audioGranted') ?? false;
      if (!ok && ask) ok = await native.invokeMethod<bool>('requestAudio') ?? false;
      if (!ok) {
        setState(() {
          denied = true;
          loading = false;
        });
        return;
      }
      final raw = await native.invokeMethod<List>('listRecordings') ?? [];
      final recs = [for (final r in raw) Rec.from(r as Map)];
      final g = groupRecordings(recs, phone: '${widget.customer['phone'] ?? ''}', name: '${widget.customer['name'] ?? ''}');
      setState(() {
        denied = false;
        mine = g.mine;
        others = g.others;
        loading = false;
      });
    } catch (e) {
      setState(() {
        error = '녹음 목록을 읽지 못했어요 ($e)';
        loading = false;
      });
    }
  }

  Future<void> _pick(Rec rec) async {
    final nav = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const PopScope(
        canPop: false,
        child: AlertDialog(
          content: Row(children: [
            SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 3)),
            SizedBox(width: 20),
            Expanded(child: Text('통화 내용을 받아쓰고 요약하는 중이에요. 최대 3분 걸려요')),
          ]),
        ),
      ),
    );
    String msg;
    try {
      final path = await native.invokeMethod<String>('copyRecording', {'id': rec['id']});
      if (path == null) throw SummaryError('녹음 파일을 열지 못했어요');
      final res = await summarizeRecording(path,
          customerName: '${widget.customer['name'] ?? ''}', company: '${widget.customer['company'] ?? ''}');
      nav.pop(); // 진행 표시
      nav.pushReplacement(MaterialPageRoute(
          builder: (_) => ConsultationForm(customerId: widget.customer['id'], draft: consultationDraft(res.summary, res.transcript))));
      return;
    } on SummaryError catch (e) {
      msg = e.message;
    } on PlatformException catch (e) {
      msg = '녹음 파일을 열지 못했어요 (${e.message ?? e.code})';
    } catch (e) {
      msg = '요약하지 못했어요 ($e)';
    }
    nav.pop(); // 진행 표시
    messenger.showSnackBar(SnackBar(content: Text(msg), duration: const Duration(seconds: 6)));
  }

  String _when(Rec r) {
    final d = DateTime.fromMillisecondsSinceEpoch((r['dateMs'] as num).toInt());
    String two(int n) => n.toString().padLeft(2, '0');
    final ms = (r['durationMs'] as num?)?.toInt() ?? 0;
    return '${d.year}-${two(d.month)}-${two(d.day)} ${two(d.hour)}:${two(d.minute)}${ms > 0 ? ' · ${formatDuration(Duration(milliseconds: ms))}' : ''}';
  }

  Widget _tile(Rec r) => Card(
        child: ListTile(
          title: Text(_when(r), style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text('${r['name']}', maxLines: 2, overflow: TextOverflow.ellipsis),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => _pick(r),
        ),
      );

  Widget _head(String t) => Padding(padding: const EdgeInsets.fromLTRB(4, 16, 4, 8), child: Text(t, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: mintInk)));

  @override
  Widget build(BuildContext context) {
    final c = widget.customer;
    Widget body;
    if (loading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (denied) {
      body = Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Text('통화 녹음 파일을 읽으려면 "음악 및 오디오" 권한이 필요해요.\n버튼을 누를 때만 고른 녹음 하나를 요약에 쓰고, 원본은 휴대폰에만 남아요.',
                textAlign: TextAlign.center, style: TextStyle(color: ink2)),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => native.invokeMethod('openAppSettings'), child: const Text('설정에서 권한 켜기')),
            TextButton(onPressed: () => _load(ask: true), child: const Text('다시 요청하기')),
          ]),
        ),
      );
    } else if (error != null) {
      body = Center(child: Padding(padding: const EdgeInsets.all(32), child: Text(error!, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFFC0392B)))));
    } else if (mine.isEmpty && others.isEmpty) {
      body = const Center(
          child: Padding(
              padding: EdgeInsets.all(32),
              child: Text('통화 녹음을 찾지 못했어요.\n갤럭시 전화 앱에서 통화 자동 녹음이 켜져 있는지 확인해 주세요.', textAlign: TextAlign.center, style: TextStyle(color: ink2))));
    } else {
      body = ListView(padding: const EdgeInsets.fromLTRB(16, 0, 16, 32), children: [
        if (mine.isNotEmpty) ...[_head('이 고객 ${mine.length}건'), for (final r in mine) ...[_tile(r), const SizedBox(height: 8)]],
        if (mine.isEmpty) Padding(padding: const EdgeInsets.fromLTRB(4, 12, 4, 0), child: Text('파일 이름에 ${c['name'] ?? '고객'} 이름이나 번호가 들어 있는 녹음이 없어요. 아래에서 골라 주세요.', style: const TextStyle(color: ink2))),
        if (others.isNotEmpty) ...[_head('최근 녹음'), for (final r in others) ...[_tile(r), const SizedBox(height: 8)]],
      ]);
    }
    return Scaffold(appBar: AppBar(title: Text('녹음 요약 · ${c['name'] ?? ''}')), body: body);
  }
}
