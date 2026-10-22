# ملحق عقود التأسيس — مقترح Arena AI للمراجعة، غير منفذ

يرتبط بـ[تقرير التأسيس](../reports/2026-10-22-gist-foundation-review.md). لا يحل تلقائيًا محل وثائق الوكيل الآخر ولا يمنح إذن تنفيذ. الأسماء التالية مقترحة ويجب توحيدها قبل كتابة المحركات.

## 1. الملكية والحدود

| الشيء | مالكه | ما لا يملكه |
|---|---|---|
| حقيقة الحالة المرصودة | Game Adapter يقرأها مع وقت ومصدر وصلاحية | لا يملأ القراءة المفقودة بصفر |
| حالة الحساب الدائمة | Accounts Manager، كاتب واحد | لا يتعامل مع cache كحقيقة أحدث من قراءة اللعبة |
| تخصيص account/task/client | Supervisor بعد lease صالح | لا يغير client binding داخل session قديمة |
| الفعل داخل العميل | Worker المعين فقط، عبر Adapter | لا يبدل المهمة إلى أخرى بصمت ولا يقبل فعلًا لجلسة قديمة |
| تشخيص حادث | AI يقترح وفق capabilities | لا يعدل كودًا ولا ينفذ shell ولا يقرر صلاحية أفعال عالية الأثر |
| الموافقة البشرية | أمر مربوط بحادث/جلسة/version وله مدة صلاحية | لا تعني الموافقة نجاح الفعل أو إلغاء cooldown |
| العرض والاستعلام | Telegram من snapshot مؤرخ | لا يكتب قاعدة الحسابات ولا يستخدم eval للاستعلام |

## 2. الحد الأدنى لرسالة الإطلاق

مثال JSON صالح للقراءة وليس schema كاملًا، ويستخدم معرفات أمثلة فقط:

```json
{
  "schema_version": "1.0",
  "command_id": "launch-example-001",
  "account_id": "acc_example",
  "session_id": "session-example-001",
  "account_revision": 7,
  "lease_generation": 3,
  "client_instance_id": "client-example-001",
  "task": {
    "id": "stronghold_resume",
    "version": "review-required",
    "artifact_ref": "catalog-approved-artifact",
    "entrypoint_ref": "approved-entrypoint",
    "parameters": {}
  },
  "config_revision": "config-example-001",
  "limits": {
    "action_max_attempts": 3,
    "session_deadline_utc": "2026-10-23T12:00:00Z"
  },
  "result_ref": "sessions/session-example-001/result.json"
}
```

التحقق المطلوب: لا حقول ناقصة لازمة، لا unknown enum، IDs غير فارغة، generation/revision أعداد صحيحة لا bool، deadline صالح، artifact مثبت ومعتمد ومتوافق، result path داخل session root. لا تنفيذ لمسار/entrypoint حر وارد من رسالة خارجية. بيانات الحساب تُقرأ من قاعدة واحدة محلية كما اختار المستخدم؛ ليس مطلوبًا تكرارها في كل حدث أو صورة أو command line.

## 3. نتيجة مستقلة للمهمة والإغلاق

```json
{
  "schema_version": "1.0",
  "event_id": "result-example-001",
  "command_id": "launch-example-001",
  "account_id": "acc_example",
  "session_id": "session-example-001",
  "lease_generation": 3,
  "client_instance_id": "client-example-001",
  "base_account_revision": 7,
  "task_id": "stronghold_resume",
  "task_status": "INTERRUPTED",
  "reason_code": "STATE_UNAVAILABLE",
  "logout_status": "UNCONFIRMED",
  "last_verified_step": "READ_PROGRESS",
  "evidence_refs": [],
  "delta": {},
  "requires_reconciliation": true
}
```

حالات مقترحة للمهمة: `COMPLETED / INTERRUPTED / BLOCKED / FAILED`. حالات الإغلاق: `CONFIRMED / UNCONFIRMED / NOT_REQUESTED`. حالة كل قراءة/فعل منفصلة: `VALID / INVALID / UNKNOWN` و`SENT / VERIFIED / NOT_VERIFIED`. لا نعتبر HTTP 200 أو process exit أو إغلاق نافذة نجاح مهمة.

mapping CLI المقترح: 0 اكتمال مثبت، 2 انقطاع، 3 عائق، 4 فشل، 5 خطأ عقد/إطلاق. يجب اعتماد mapping نفسه في المشرف والاختبارات. غياب result بعد exit لا يساوي COMPLETED؛ ينتج `RECONCILIATION_REQUIRED`. ملف result يُنشر ذريًا بعد تحقق بنيته.

## 4. دورة الحساب وslot

```text
PENDING_DISCOVERY → DISCOVERING → READY
READY → LEASED → IN_SESSION
IN_SESSION → RESTING | BLOCKED_PENDING_TRIAGE | RECONCILIATION_REQUIRED
RESTING → READY فقط بعد available_after وباقي شروط الأهلية
BLOCKED_PENDING_TRIAGE → READY بعد حل مثبت وسياسة الاستحقاق
أي جلسة فقدت مرجعها/ربطها → RECONCILIATION_REQUIRED، لا READY تلقائية
MANUAL_HOLD يمنع الجدولة حتى رفعه صراحة
```

الحالة الدائمة ليست مكانًا لتخزين كل طور عملية؛ slot له حالة مستقلة `IDLE / STARTING / RUNNING / DRAINING / CLEANING / FAILED`. لا يعود IDLE قبل انتهاء PID وأبنائه وتسوية ملكية الحساب. انتهاء lease لا يجعل JVM القديمة مأمونة؛ generation القديم يُرفض حتى تُنهى العملية/يُعزل أثرها. على Windows يثبت اختبار طريقة cleanup الفعلية، لا نفترض أن قتل PID واحد يكفي.

## 5. كتابة الحالة وتكرار الأحداث

1. event يحمل event_id/account/session/generation/base_revision ووقت رصد ومصدرًا.
2. الكاتب الوحيد يفحص schema ثم صلاحية الملكية ثم dedup ثم revision.
3. stale/replayed event لا يطبق مرتين؛ يوثق سبب الرفض أو ينتظر reconciliation.
4. القفل يغطي read-validate-apply-write كاملًا؛ JSON صالح لا يكفي لإثبات عدم فقد تحديث.
5. نشر tmp فريد ثم atomic replace، مع سياسة متانة/نسخة احتياطية وتعافٍ معتمدة. يحتفظ سجل النتائج بما يسمح بمعرفة إن كانت transaction طُبقت بعد crash.
6. لا ندعي exactly-once للعبة. عند فقد الرد نقرأ الواقع ونثبت الأثر قبل retry؛ إذا تعذر ذلك نتوقف UNKNOWN بدل تكرار فعل مؤثر.

## 6. تجهيز المهمة والبنك

`prepare_loadout(task_requirements, observed_inventory, observed_equipment, bank_snapshot)`:

- policy واضحة `PRESERVE_SAFE / FULL_RESET`؛ full reset لا يُفرض أثناء كل خطوة.
- required/retained/protected items وany_of للأدوات، كميات، مهارات استخدام، وضع noted/unnoted، سعة لازمة واحتياطي مال/مواد.
- نقص supplies نتيجة `NOT_ELIGIBLE/SUPPLIES_MISSING` لا حادث AI بالضرورة؛ المخطط يختار بديلًا بعد رد صريح وبسقف يمنع دوران البدائل للأبد.
- نتحقق بعد كل إيداع/سحب/لبس، ثم bank closed فعلًا. أسماء أو IDs أدوات اختيار مرتبطة بإصدار cache، وليست ضمان تحديث سحريًا.
- bank snapshot له observed_at/completeness؛ بنك غير مفتوح/غير قابل للوصول = UNKNOWN، وليس صفر موجودات.

لا تعاملات ذرية داخل اللعبة؛ نسجل checkpoint ونصالح الأثر الجزئي عند إعادة التشغيل.

## 7. التوقيتات والإعدادات

- كل قيمة قابلة للضبط خارجيًا وفق طلب المستخدم، بأسماء ووحدات وحدود تحقق واضحة. لا أختار أرقامًا بديلة للتعارضات دون اعتماده.
- نفرق `interaction_delay_range` من `request_timeout` و`verification_deadline` و`session_deadline` و`cooldown_policy`؛ الانتظار ليس إثبات نجاح.
- config revision واحدة لكل transaction؛ تغييرات السلامة تتطبق حسب policy معلنة، والباقي عند action/session boundary.
- استخدم ساعة monotonic للمدد المحلية وUTC محفوظ للاستحقاق بين إعادة التشغيل؛ clock jump لا يفتح الحساب قبل أوانه.
- انتظار قابل للإلغاء؛ لا wait بلا حد، ولا retry budget يبدأ من الصفر عند كل استدعاء متكرر لنفس الحادث.

## 8. حوادث AI وأوامر Telegram

incident يحمل immutable context: account/session/client/generation/task/action + state revision + evidence timestamp. التشخيص المتأخر لا يُسقط على نافذة جديدة. الاقتراح يعبر allowlist وحدود parameters ويُعاد تحقق preconditions من قراءة حديثة قبل الفعل. لا تكفي confidence أو موافقة بشرية قديمة.

command/callback يحمل command_id وincident_id وplan_version وexpiry؛ التفويض يراجع user/chat والدور ثم dedup ثم compare-and-set. يمنع replay بعد restart، لا مجرد تعطيل زر في الواجهة. نجاح التطبيق لا يُعلن إلا بعد postcondition؛ إذا تعذر التحقق نرسل النتيجة UNKNOWN.

عند إغلاق جلسة متعثرة يُعاد التشخيص لخطة جلسة جديدة مُخصصة، وليس أمرًا لنافذة لم تعد موجودة. لا صلاحية AI تلقائية لتجاوز تحذيرات الخسارة أو تعديل الملفات؛ الأفعال المعتمدة محدودة ومراجعة مسبقًا.

## 9. مصفوفة قبول ملزمة قبل التوسع — مقترحة لا منفذة

| الاختبار | النتيجة المطلوبة |
|---|---|
| state/inventory ناقصة مع varbits مكتملة | لا COMPLETED ولا إيداع مزعوم |
| surface ومعه الحذاء | يصل لقرار بنك ويثبت الأثر النهائي |
| رد ضائع بعد عبور/سحب | reconciliation قبل أي تكرار |
| crash بعد تطبيق delta وقبل ACK | لا تكرار للمال/الوقت عند replay |
| slot انتقل من A إلى B ثم موافقة قديمة | تُرفض ولا فعل على B |
| عملية قديمة حية بعد supervisor restart | لا تشغيل حساب ثانٍ عليها ولا اعتبارها READY |
| task ساكنة قانونيًا | لا قتل خطأ بسبب الإحداثيات الثابتة |
| pause/stop أثناء wait/طلب جارٍ | توقف محدد بموعد وحالة معلنة |
| script جديد ناقص metadata | UNVERIFIED وليس RUNNABLE |
| config range متناقض/وحدة خاطئة | رفض config كاملًا والإبقاء على revision السابقة |
| Telegram/AI متعطل | التنفيذ المسموح مستمر، outbox محدود ودليل محلي باقٍ |
| رصيد يتجاوز عتبة تنبيه | تنبيه deduplicated؛ لا تغيير lifecycle لمجرد الرصيد |

**هذه معايير تصميم واختبار مستقبلية. لا تُحسب ضمن الـ44 اختبارًا الموجودين حاليًا.**
