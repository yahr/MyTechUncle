import 'package:flutter_test/flutter_test.dart';
import 'package:mytechuncle/core.dart';

void main() {
  final today = DateTime(2026, 10, 3);

  group('normalizePhone', () {
    test('하이픈·공백을 빼요', () => expect(normalizePhone('010-1234 5678'), '01012345678'));
    test('+82 국가번호를 0으로 바꿔요', () => expect(normalizePhone('+82 10-1234-5678'), '01012345678'));
    test('빈 값은 빈 문자열', () => expect(normalizePhone(null), ''));
  });

  group('subscriptionLabel', () {
    Map<String, dynamic> sub(String start, String end, {String product = 'annual', bool paid = true, String status = 'active'}) =>
        {'product': product, 'start_date': start, 'end_date': end, 'paid': paid, 'status': status};

    test('구독이 없으면', () => expect(subscriptionLabel([], today), '구독 없음'));
    test('이용 중이면 끝나는 날과 남은 날', () {
      expect(subscriptionLabel([sub('2026-10-01', '2027-09-30')], today), '연간 기술고문 · 2027-09-30까지 (D-362)');
    });
    test('마지막 날은 D-day', () {
      expect(subscriptionLabel([sub('2025-10-04', '2026-10-03')], today), '연간 기술고문 · 2026-10-03까지 (D-day)');
    });
    test('입금 전이면 표시', () {
      expect(subscriptionLabel([sub('2026-10-01', '2036-09-30', product: 'founder', paid: false)], today),
          'Founder 기술고문 · 2036-09-30까지 (D-3650) · 입금 대기');
    });
    test('끝난 구독만 있으면 가장 최근 만료일', () {
      expect(subscriptionLabel([sub('2024-01-01', '2024-12-31'), sub('2025-01-01', '2025-12-31')], today), '만료 · 2025-12-31');
    });
    test('시작 전 구독', () {
      expect(subscriptionLabel([sub('2026-10-10', '2027-10-09')], today), '연간 기술고문 · 2026-10-10 시작 예정');
    });
    test('해지한 구독은 빼요', () {
      expect(subscriptionLabel([sub('2026-10-01', '2027-09-30', status: 'cancelled')], today), '구독 없음');
    });
  });

  group('buildCallerIndex', () {
    final customers = [
      {'id': 1, 'company': 'R사', 'name': '홍길동', 'phone': '010-1111-2222'},
      {'id': 2, 'company': 'M사', 'name': '김대표', 'phone': ''},
    ];
    final subs = [
      {'customer_id': 1, 'product': 'annual', 'start_date': '2026-10-01', 'end_date': '2027-09-30', 'paid': true, 'status': 'active'},
    ];
    final cons = [
      {'customer_id': 1, 'date': '2026-09-14', 'title': '재고 연동 견적 검토'},
      {'customer_id': 1, 'date': '2026-09-28', 'title': 'ERP 도입 순서'},
      {'customer_id': 1, 'date': '2026-08-01', 'title': '첫 상담'},
      {'customer_id': 1, 'date': '2026-07-01', 'title': '가장 오래된 것'},
    ];
    final index = buildCallerIndex(customers, subs, cons, today);

    test('번호 없는 고객은 빼요', () => expect(index.keys, ['01011112222']));
    test('누구인지와 구독', () {
      expect(index['01011112222']!['title'], 'R사 홍길동');
      expect(index['01011112222']!['sub'], '연간 기술고문 · 2027-09-30까지 (D-362)');
      expect(index['01011112222']!['id'], 1);
    });
    test('최근 상담 3건을 최신순으로', () {
      expect(index['01011112222']!['lines'], ['09-28 ERP 도입 순서', '09-14 재고 연동 견적 검토', '08-01 첫 상담']);
    });
  });
}
