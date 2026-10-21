# حالة Antigraft

- author: Antigraft
- commit الأساس: `1bcbb8b` (على فرع `feature/smart-resume-fresh-account`)
- الحالة: FLOOR_1_NEEDS_MODIFICATION — رصد خلل شروط المحطات التتابعية في مسار الطابق الأول (تخطي محطة 2 بسبب متغير الإحداثيات الراكد) ومطلوب تصحيحه من المنفذ قبل أي اختبار حي.
- المهمة الحالية والملفات المحجوزة: الوكيل المنفذ مكلف بتصحيح تسلسل محطات الطابق الأول في run_stronghold_bot.py.
- حدود الاعتماد والتغطية:
  - ✅ **معتمد ومحصن:** قراءة الحالة الحية `read_progress()`، دالة القرار المجردة `choose_next_action()`، الاستئناف الذكي، سلم الطابق الأول المباشر، وصندوق 20656 المعتمد، وحزمة الـ 30 اختباراً.
  - ⚠️ **حدود الاستخدام (Important Limitation):** مسار الطابق الأول يحتاج تعديلاً برمجياً لمنع تخطي المحطات بسبب الإحداثيات القديمة، ومسار الطابق الثاني لا يزال قيد الحظر بـ `SafetyStop("STOP_NOT_IMPLEMENTED")`. الحساب الجديد ما زال محظوراً.
- التقارير المعتمدة:
  1. [2026-10-21-task-01.md](reports/2026-10-21-task-01.md)
  2. [2026-10-21-task-02-breakthrough-boots-claimed.md](reports/2026-10-21-task-02-breakthrough-boots-claimed.md)
  3. [2026-10-21-task-03-bank-verified-and-code-hardened.md](reports/2026-10-21-task-03-bank-verified-and-code-hardened.md)
  4. [2026-10-21-task-04-reviewer-audit-selective-merge.md](reports/2026-10-21-task-04-reviewer-audit-selective-merge.md)
  5. [2026-10-21-task-05-baseline-adoption-and-fresh-account-roadmap.md](reports/2026-10-21-task-05-baseline-adoption-and-fresh-account-roadmap.md)
  6. [2026-10-21-task-06-reviewer-audit-baseline-and-fresh-account-readiness.md](reports/2026-10-21-task-06-reviewer-audit-baseline-and-fresh-account-readiness.md)
  7. [2026-10-21-task-07-implementation-of-smart-resume-and-state-machine.md](reports/2026-10-21-task-07-implementation-of-smart-resume-and-state-machine.md)
  8. [2026-10-21-task-08-reviewer-contract-audit-and-stop-not-implemented.md](reports/2026-10-21-task-08-reviewer-contract-audit-and-stop-not-implemented.md)
  9. [2026-10-21-task-09-implementer-floor-1-reward-path-and-tests.md](reports/2026-10-21-task-09-implementer-floor-1-reward-path-and-tests.md)
  10. [2026-10-21-task-10-reviewer-audit-floor-1-stale-coordinate-defect.md](reports/2026-10-21-task-10-reviewer-audit-floor-1-stale-coordinate-defect.md)
- اختبار المحاكاة: PASS_SIMULATION (30/30 اختباراً في `test_safety.py`).
- الاختبار الحي: PASS_LIVE (محتويات البنك والـ Varbits الأربعة = 1 على الحساب التجريبي).
