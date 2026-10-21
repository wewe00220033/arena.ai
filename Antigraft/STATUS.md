# حالة Antigraft

- author: Antigraft
- commit الأساس: `fd22e65` (على فرع `feature/smart-resume-fresh-account`)
- الحالة: FLOOR_1_SEQUENTIAL_FIXED — تم إصلاح خلل الإحداثيات الراكدة في مسار الطابق الأول باعتماد مقطع البداية الأحادي start_stage والتسلسل الخطي الحتمي مع التحقق من عبور كل باب ومنع طلب الصندوق دون إثبات الدخول للغرفة المركزية، وصون حارس الطابق الثاني STOP_NOT_IMPLEMENTED، واجتياز 34/34 اختبار سلامة.
- المهمة الحالية والملفات المحجوزة: مهمة المنفّذ لإصلاح الطابق الأول اكتملت وموثقة؛ لا توجد ملفات محجوزة.
- حدود الاعتماد والتغطية:
  - ✅ **معتمد ومحصن:** قراءة الحالة الحية `read_progress()`، دالة القرار المجردة `choose_next_action()`، مسار مكافأة الطابق الأول الخطي التتابعي مع التحقق بعد كل باب، الاستئناف الذكي من كافة الطوابق والمحطات، خروج السطح والإيداع المشدد في البنك، وحزمة الـ 34 اختباراً.
  - ⚠️ **حدود الاستخدام (Important Limitation):** مسار غرفة صندوق الطابق الثاني يتوقف بـ `SafetyStop("STOP_NOT_IMPLEMENTED")` عند طلبه برمجياً لحين برمجته ومراجعته بعد اعتماد هذا الإصلاح. الحساب الجديد ما زال محظوراً.
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
  11. [2026-10-21-task-11-implementer-fix-floor-1-stale-coords-and-sequential-stages.md](reports/2026-10-21-task-11-implementer-fix-floor-1-stale-coords-and-sequential-stages.md)
- اختبار المحاكاة: PASS_SIMULATION (34/34 اختباراً في `test_safety.py`).
- الاختبار الحي: PASS_LIVE (محتويات البنك والـ Varbits الأربعة = 1 على الحساب التجريبي).
