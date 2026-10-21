# 📋 تقرير المهمة رقم 13 — تنفيذ مسار مكافأة الطابق الثاني (Floor 2) وحزمة الاختبارات الشاملة (44/44) 🏛️🌽
**التاريخ:** 2026-10-21  
**الدور:** المنفّذ (Antigraft Implementer)  
**الفرع:** `feature/smart-resume-fresh-account`  
**commit الأساس:** `92bb1e3`  
**الحالة الفنية:** `FLOOR_2_IMPLEMENTED_AWAITING_REVIEWER`  

---

## 🎯 1. ملخص ما تم إنجازه في مهمة Task 13

استجابة للتكليف الرقابي الصادر في Task 12 وقرار توحيد تدفق العمل بين الوكلاء:
1. **تم تنفيذ مسار مكافأة الطابق الثاني بالكامل (`CLAIM_FLOOR_2_REWARD`):**
   - استبدال حارس التوقف المؤقت `STOP_NOT_IMPLEMENTED` بمسار تتابعي خطي حتمي يستند إلى الدليل المرجعي المستخرج من بايت-كود كلاسات `microbot-2.6.34.jar`.
   - تحديد نقطة البداية الحية (`start_stage`) بدقة لمنع التكرار ودعم الاستئناف الذكي من أي غرفة من غرف الطابق الثاني.
   - التحقق الصارم بعد كل باب من أبواب `Rickety door` الأربعة، والتوقف الفوري بـ `SafetyStop` عند فشل العبور.
   - منع طلب أو لمس كيس الحبوب (`Grain of Plenty: 19000`) إلا بعد ثبوت الوجود داخل الغرفة المركزية (`x >= 2017 and y <= 5230`).
   - التفاعل مع الكيس بـ `"Search"` وحل الأسئلة الأمنية وتأكيد مكافأة 3,000 GP وتفعيل `Varbit 2310 == 1`.
2. **تطوير مسار النزول للطابق الثالث (`FLOOR_2_TO_FLOOR_3`):**
   - حل معضلة بوابة الاختصار `19005`: إذا كان اللاعب في الغرفة المركزية بعد استلام المكافأة (`px < 2035`)، لا يحاول استدعاء البوابة البعيدة الواقعة في غرفة البداية، بل يتوجه مباشرة 5 مربعات لسلم النزول `19004` عند `(2026, 5219)` وينزل للطابق الثالث.
   - إذا كان الحساب قديماً وبدأ عند المدخل (`px >= 2035 and py >= 5238`) يستخدم بوابة الاختصار `19005`.
3. **توسيع حزمة الاختبارات من 34 إلى 44 اختباراً شاملاً:**
   - إضافة اختبار المسار الكامل للطابق الثاني بمحاكاة مكانية متغيرة.
   - إضافة اختبارات فشل عبور الأبواب ومنع التفاعل مع الكيس.
   - إضافة اختبار الاستئناف من منتصف الطابق الثاني (Stage 2).
   - إضافة اختبار الغرفة المركزية المباشر.
   - إضافة اختبار فشل الأبواب واستنفاذ الكيس.
   - إضافة اختبار النزول المباشر لسلم 19004.
   - إضافة اختبار الرحلة الكاملة من الصفر حتى البنك (`test_full_journey_step_by_step_progression`) عبر الـ 11 مرحلة.
   - **النتيجة:** 44/44 اختباراً ناجحاً بنسبة 100% في 0.528 ثانية.
4. **المزامنة والتطابق البايتي 100%:**
   - تطابق تام في SHA-256 بين `arena.ai/OSRS_Bot` و `games/OSRS/OSRS_Bot` و `OSRS_Bot`.

---

## 📜 2. كتلة الدليل المرجعي (Ground Truth Evidence — Bolla Law #8)

### أ. كيس مكافأة الطابق الثاني وسلالم النزول والـ Varbit:
- **المصدر المعتمد:** بايت-كود `StrongholdOfSecurity.class` المستخرج من `microbot-2.6.34.jar` (والمرجع الموثق في `شاطر.md` السطور 2300-2345):
  ```java
  private static final int[] REWARD_BITS = {
      VarbitID.SOS_EMOTE_FLAP,   // 2309
      VarbitID.SOS_EMOTE_DOH,    // 2310 (Floor 2)
      VarbitID.SOS_EMOTE_IDEA,   // 2311
      VarbitID.SOS_EMOTE_STAMP   // 2312
  };
  private static final int[] REWARD_IDS = {
      ObjectID.SOS_WAR_CHEST,    // 20656 (Floor 1)
      ObjectID.SOS_FAM_SACK,     // 19000 (Floor 2: Grain of Plenty)
      ObjectID.SOS_PEST_CHEST,   // 23709 (Floor 3)
      ObjectID.SOS_DEATH_PRAM    // 23731 (Floor 4)
  };
  private static final WorldPoint[] REWARDS = {
      point(1907, 5222), point(2021, 5216), point(2144, 5280), point(2344, 5214)
  };
  private static final WorldPoint[] REWARD_STANDS = {
      point(1906, 5222), point(2021, 5218), point(2144, 5281), point(2343, 5215)
  };
  private static final int[] DOWN_IDS = {
      ObjectID.SOS_WAR_LADD_DOWN,   // 20785
      ObjectID.SOS_FAM_LADD_DOWN,   // 19004 (Floor 2 descent ladder)
      ObjectID.SOS_PEST_LADD_DOWN   // 23706
  };
  private static final WorldPoint[] DOWN_STANDS = {
      point(1903, 5222), point(2026, 5219), point(2147, 5284)
  };
  ```

### ب. محطات المسار وأبواب الطابق الثاني (Rickety door):
- **المصدر المعتمد:** مصفوفة `setupSteps` لكلاس الحصن (PC=212..513):
  ```text
  1. النزول في غرفة البداية: (2042, 5245)
  2. المشي لباب الغرفة: (2034, 5244) -> Pass "Rickety door" -> التحقق من x <= 2034
  3. محطة الممر الشرقي: (2030, 5236) ثم (2027, 5236) -> Pass "Rickety door" -> التحقق من y >= 5241
  4. محطة الغرفة الشمالية: (2025, 5245) ثم (2020, 5244) ثم (2019, 5237) -> Pass "Rickety door" -> التحقق من x <= 2016
  5. محطة الممر الغربي: (2014, 5237) -> (2013, 5244) -> (2005, 5244) -> (2005, 5230) -> (2007, 5228) -> (2011, 5228) -> (2014, 5231) -> (2014, 5228) -> Pass "Rickety door" -> التحقق من x >= 2017 و y <= 5230
  6. الوصول لكيس الحبوب في الغرفة المركزية: (2021, 5218) -> Search Sack 19000
  ```

---

## ⚙️ 3. التعديلات البرمجية في كود التشغيل (`run_stronghold_bot.py`)

### أ. دالة `CLAIM_FLOOR_2_REWARD`:
```python
    elif action == "CLAIM_FLOOR_2_REWARD":
        print("\n--- عبور الطابق الثاني (Catacomb of Famine) وحصد مكافأة 3,000 GP وحركة Slap head ---")
        st = api_get("/state")
        pos = st.get("player", {}).get("position", {}) if isinstance(st, dict) else {}
        px, py = pos.get("x", 0), pos.get("y", 0)

        # 1. تحديد المرحلة الابتدائية بناءً على موقع اللاعب الفعلي في الغرف الموثقة
        if 2035 <= px <= 2050 and 5238 <= py <= 5250:
            start_stage = 0  # غرفة البداية (سلم النزول وبوابة الاختصار 19005)
        elif 2027 <= px <= 2036 and 5230 <= py <= 5240:
            start_stage = 1  # الممر الشرقي
        elif 2016 <= px <= 2026 and 5237 <= py <= 5250:
            start_stage = 2  # الغرفة الشمالية
        elif 2000 <= px <= 2016 and 5225 <= py <= 5250:
            start_stage = 3  # الممر الغربي ومدخل الغرفة المركزية
        elif 2017 <= px <= 2035 and 5210 <= py <= 5230:
            start_stage = 4  # الغرفة المركزية (غرفة كيس الحبوب Grain of Plenty)
        else:
            raise SafetyStop(f"موقع اللاعب في الطابق الثاني خارج النطاق الموثق للمحطات: {(px, py)}")
```

### ب. المقاطع الخطية التتابعية والتحقق الصارم:
- **المقطع 1:** السير إلى `(2034, 5244)`، عبور `Rickety door`، فحص `after_pos["x"] <= 2034`.
- **المقطع 2:** السير إلى `(2030, 5236)` ثم `(2027, 5236)`، عبور `Rickety door`، فحص `after_pos["y"] >= 5241`.
- **المقطع 3:** السير إلى `(2025, 5245)` -> `(2020, 5244)` -> `(2019, 5237)`، عبور `Rickety door`، فحص `after_pos["x"] <= 2016`.
- **المقطع 4:** عبور محطات الممر الغربي الثمانية، عبور `Rickety door`، فحص `after_pos["x"] >= 2017 and after_pos["y"] <= 5230`.
- **الوصول والتفاعل:** السير إلى `(2021, 5218)`، التفاعل مع `Grain of Plenty: 19000` بإجراء `"Search"` وحل الأسئلة حتى ثبوت `Varbit 2310 == 1`.

### ج. دالة `FLOOR_2_TO_FLOOR_3`:
```python
    elif action == "FLOOR_2_TO_FLOOR_3":
        print("\n--- عبور الطابق الثاني إلى سلم النزول للطابق الثالث ---")
        st = api_get("/state")
        pos = st.get("player", {}).get("position", {}) if isinstance(st, dict) else {}
        px = pos.get("x", 0)
        py = pos.get("y", 0)
        # إذا كان اللاعب في غرفة البداية (بعيد عن الغرفة المركزية)، يستخدم بوابة الاختصار
        if px >= 2035 and py >= 5238:
            interact_object(19005, "Use")
            time.sleep(2)
            handle_dialogue_and_modals()
        walk_to(2026, 5219, plane=0, timeout=35)
        print("🖐️ النزول عبر سلم الطابق الثاني (19004)...")
        for attempt in range(4):
            interact_object(19004, "Climb-down")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
                st = api_get("/state")
                if 2110 <= st.get("player", {}).get("position", {}).get("x", 0) <= 2185:
                    print("📍 تم النزول للطابق الثالث بنجاح!")
                    return True
        return False
```

---

## 🧪 4. نتائج حزمة الاختبارات الشاملة (`test_safety.py`)

تمت توسيع الحزمة من 34 إلى **44 اختباراً شاملاً**:
- 10 اختبارات وحدة مخصصة للطابق الثاني تغطي كافة سيناريوهات الحركة، الأبواب، فشل العبور، منع الكيس، والاستئناف الميداني.
- اختبار رحلة كاملة يختبر خطوة بخطوة الانتقال السلس عبر الـ 11 حالة للرحلة الكاملة.
- جميع الاختبارات الـ 44 تنجح في 0.528 ثانية.

```text
Ran 44 tests in 0.528s
OK
```

---

## 🔒 5. موقف بوابات الإنجاز (Milestone Gates Status)

1. **البوابة 1 (تنفيذ الطابق الثاني ومراجعته):**
   - **المنفّذ (Antigraft):** تم التنفيذ البرمجي بالكامل + 44 اختباراً ناجحاً.
   - **المراجع (Arena AI):** جاهز الآن للتدقيق وسحب الكود وقراءة التقرير من المستودع.
2. **البوابة 2 (فحص الرحلة كوحدة واحدة):**
   - تم تضمين اختبار تتابعي للرحلة الكاملة من الصفر حتى البنك (`test_full_journey_step_by_step_progression`).
   - بانتظار مراجعة وتأكيد الوكيل المراجع قبل أي تجربة حية.
3. **البوابة 3 (تجربة حية مراقبة على حساب جديد):**
   - **محظورة حالياً** — لا يُطلب من زيزو أي حساب جديد أو تشغيل حي حتى اعتماد البوابتين 1 و 2.

---

## 📦 6. البصمات التشفيرية والتطابق (SHA-256 Hashes)

| الملف | SHA-256 Hash |
|---|---|
| `arena.ai/OSRS_Bot/run_stronghold_bot.py` | `c54144e32ab5e76d11b32598099e1f1c3b6b41b3f3eabac112033974413efbdb` |
| `games/OSRS/OSRS_Bot/run_stronghold_bot.py` | `c54144e32ab5e76d11b32598099e1f1c3b6b41b3f3eabac112033974413efbdb` |
| `OSRS_Bot/run_stronghold_bot.py` | `c54144e32ab5e76d11b32598099e1f1c3b6b41b3f3eabac112033974413efbdb` |
| `arena.ai/OSRS_Bot/test_safety.py` | `237d80ed3e97041ca8d7087bf26c9fe50010aca92256394b85f68765b5e16a6b` |
| `games/OSRS/OSRS_Bot/test_safety.py` | `237d80ed3e97041ca8d7087bf26c9fe50010aca92256394b85f68765b5e16a6b` |
| `OSRS_Bot/test_safety.py` | `237d80ed3e97041ca8d7087bf26c9fe50010aca92256394b85f68765b5e16a6b` |
