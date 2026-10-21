# تسليم Antigraft إلى Arena AI

## ما تم في هذه الجولة (Baseline Hardening & Scope Boundary)
1. **تحصين فحص البنك (`verify_bank_has_boots`):**
   - تم تشديد الفحص ليشترط مطابقة الاسم الصريحة (`name == "fancy boots"`) أو المعرّف (`id == 9005`) مع إلزام كمية موجبة (`qty > 0`).
   - استبعاد أي مطابقة جزئية بالـ substring ورفض الكمية صفر أو القيم السالبة أو غير الصحيحة.
2. **التمييز الدقيق لرصيد الذهب:**
   - التمييز الصريح بين فشل الاستعلام (`الرصيد غير معروف (فشل استعلام البنك)`)، وبين انعدام الذهب بالخزينة (`0 GP (لم يُرصد ذهب في الخزينة)`).
3. **التحقق من نقر ويدجت الجزمة في المهد:**
   - التأكد من أن استجابة استدعاء `POST /widgets/click` ترجع `clicked == True`.
4. **تحديث وتوسيع حزمة الاختبارات (17 Tests):**
   - تحديث `test_verify_bank_has_boots` لاختبار كافة الحالات المشددة الجديدة بنجاح تام (17/17 OK).
5. **اعتماد خط الأساس الرسمي (Baseline v1.0):**
   - تثبيت هذه النسخة كخط أساس معروف ومحصن ومختبر هندسياً.
   - الإقرار والتوثيق الكامل لحدود النسخة: **لا تدعم تشغيل حساب جديد من الصفر دون إضافة مسارات الصناديق في الطابقين 1 و 2** لأن بوابات الاختصار ترفض العبور قبل فتح الصناديق.

## الاختبارات والنسخة
- تقارير المهمة:
  - [reports/2026-10-21-task-01.md](reports/2026-10-21-task-01.md)
  - [reports/2026-10-21-task-02-breakthrough-boots-claimed.md](reports/2026-10-21-task-02-breakthrough-boots-claimed.md)
  - [reports/2026-10-21-task-03-bank-verified-and-code-hardened.md](reports/2026-10-21-task-03-bank-verified-and-code-hardened.md)
  - [reports/2026-10-21-task-04-reviewer-audit-selective-merge.md](reports/2026-10-21-task-04-reviewer-audit-selective-merge.md)
  - [reports/2026-10-21-task-05-baseline-adoption-and-fresh-account-roadmap.md](reports/2026-10-21-task-05-baseline-adoption-and-fresh-account-roadmap.md)
  - [reports/2026-10-21-task-06-reviewer-audit-baseline-and-fresh-account-readiness.md](reports/2026-10-21-task-06-reviewer-audit-baseline-and-fresh-account-readiness.md)
  - [reports/2026-10-21-task-07-reviewer-stop-gate-fresh-account-readiness.md](reports/2026-10-21-task-07-reviewer-stop-gate-fresh-account-readiness.md)
- اختبار المحاكاة: `PASS_SIMULATION` (17/17).
- الاختبار الحي: `PASS_LIVE` (البنك يحوي Fancy boots id 9005 بكمية 1، الذهب 28 GP، الـ Varbits الأربعة = 1).
- حالة الاعتماد: `BASELINE_V1.0_CERTIFIED` & `STOP_GATE_PENDING_FRESH_CODE`.

## المطلوب من Arena AI والوكيل المنفذ
1. **الوكيل المنفذ:** البدء الفوري في كتابة كود وبرمجة مسارات وأبواب صناديق الطابقين 1 و 2 داخل الفرع `feature/smart-resume-fresh-account`، وتوسيع `test_safety.py` لمحاكاتها.
2. **الوكيل المراجع:** التدقيق المستقل ومطابقة إحداثيات ومسارات الصناديق فور كتابتها.
3. **توجيه المستخدم (زيزو):** تم إبلاغ زيزو رسمياً بعدم إنشاء حساب جديد حالياً حتى لا يضيع وقته في الجزيرة على الفاضي، ولن يُطلب منه إنشاء الحساب إلا بعد اكتمال واختبار الكود بنسبة 100%.
