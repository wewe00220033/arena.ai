import urllib.request
import json
import time
import os
import sys

# دعم ترميز UTF-8 على ويندوز لمنع أخطاء charmap cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ==============================================================================
# OSRS Standalone Autonomous Bot — Stronghold of Security (10,000 GP + Boots)
# يعمل محلياً 100% بدون نت ولا ذكاء اصطناعي وبدون استهلاك أي كوتا!
# ==============================================================================

TOKEN_PATH = os.environ.get("OSRS_AGENT_TOKEN_PATH", os.path.expanduser("~/.runelite/.agent-token"))
TOKEN = ""
HEADERS = {"X-Agent-Token": TOKEN, "Content-Type": "application/json"}
BASE_URL = "http://127.0.0.1:8081"

def api_get(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def api_post(endpoint, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", data=body, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def ensure_login():
    st = api_get("/state")
    if not st.get("loggedIn"):
        print("🔄 الحساب غير مسجل الدخول، جاري تسجيل الدخول التلقائي...")
        res = api_post("/login", {"wait": True, "timeout": 30})
        print("✅ نتيجة تسجيل الدخول:", res.get("message"))
        time.sleep(2)

# استيراد المساعد المعزول لحل الأسئلة الأمنية
try:
    from osrs_ai_solver import solve_security_dialogue, select_best_answer
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from osrs_ai_solver import solve_security_dialogue, select_best_answer

# استيراد حارس الأمان ووحدة التحكم المركزية
try:
    from safety import SafetyStop, SafetyController
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from safety import SafetyStop, SafetyController

controller = SafetyController(api_get, api_post)

STRONGHOLD_DOORS = [23653, 23654, 23727, 23728, 17009, 17100, 19206, 19207]
STRONGHOLD_DOOR_NAMES = ["Oozing barrier", "Portal of Death", "Gate of War", "Rickety door"]

def is_all_rewards_claimed():
    """التحقق الصريح من استلام كافة مكافآت الطوابق الأربعة (Varbits 2309..2312)"""
    vbs = [api_get(f"/varbits?id={vid}").get("value", 0) for vid in (2309, 2310, 2311, 2312)]
    return all(v == 1 for v in vbs)

def verify_bank_has_boots(bank_data):
    """التحقق الصريح والمشدد من وجود Fancy boots بكمية موجبة داخل بيانات البنك"""
    if not isinstance(bank_data, dict):
        return False
    items = bank_data.get("items")
    if not isinstance(items, list):
        return False
    for it in items:
        if not isinstance(it, dict):
            continue
        iid = it.get("id")
        name = str(it.get("name", "")).strip().casefold()
        qty = it.get("quantity", 0)
        if (iid == 9005 or name == "fancy boots") and isinstance(qty, int) and qty > 0:
            return True
    return False

def handle_dialogue_and_modals():
    """التعامل مع شاشات الحوار والأسئلة مع فحص الأمان الدوري"""
    controller.check()
    # 1. شباك التحذير للسلالم (groupId: 579, childId: 17)
    api_post("/widgets/click", {"groupId": 579, "childId": 17})

    handled = False
    for _ in range(5):
        d = api_get("/dialogue")
        if not d.get("inDialogue"):
            break
        handled = True

        if d.get("hasOptions") or d.get("hasSelectAnOption"):
            raw_opts = d.get("options", [])
            q = d.get("question", "") or d.get("dialogueText", "")

            # استبعاد رسائل الانتظار قبل اتخاذ القرار
            opts = [o for o in raw_opts if isinstance(o, str) and o.strip().lower().rstrip(".!?") not in ("please wait", "click here to continue")]
            if not opts:
                time.sleep(0.5)
                continue

            selected = solve_security_dialogue(q, opts)
            if selected:
                print(f"💬 اختيار الإجابة: {selected}")
                api_post("/dialogue/select", {"option": selected})
                time.sleep(1.2)
            else:
                raise SafetyStop(f"إجابة غير معروفة؛ أجب يدوياً ثم أعد التشغيل: {opts}")

        elif d.get("hasContinue"):
            api_post("/dialogue/continue", {})
            time.sleep(0.8)

    return handled

def check_and_eat_food():
    """فحص الدم والأكل التلقائي لو الـ HP نزل عن 8 عبر controller.check()"""
    controller.check()

def try_pass_door(door_name="Oozing barrier"):
    """تفاعل صريح مع الباب والتحقق من تغير الموضع لتأكيد العبور دون قفزات عشوائية"""
    before = controller.check()
    for action in ("Pass-through", "Open"):
        result = api_post("/objects/interact", {"name": door_name, "action": action})
        if result.get("success") is True:
            for _ in range(8):
                time.sleep(0.5)
                handle_dialogue_and_modals()
                after = controller.check()
                if after != before:
                    print(f"🚪 تم عبور الباب بنجاح ({door_name})!")
                    return True
            raise SafetyStop(f"لم تُرصد حركة بعد التفاعل مع الباب ({door_name})")
    raise SafetyStop(f"فشل التفاعل مع الباب ({door_name})")

def try_open_nearby_doors():
    # الحظر الصارم لفتح أبواب عشوائية قد تُعيد اللاعب للخلف
    raise SafetyStop("المسار متوقف؛ يلزم فحص الباب والمسار يدوياً، لن نختار باباً عشوائياً")

def walk_to(x, y, plane=0, timeout=75):
    """المشي الآمن مع المراقبة الدورية لحالة الأمان والحوارات"""
    controller.check()
    controller.require(api_post("/walk", {"x": x, "y": y, "plane": plane, "wait": False}), "المشي")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pos = controller.check()
        if pos[2] == plane and max(abs(pos[0] - x), abs(pos[1] - y)) <= 1:
            print(f"📍 وصل إلى جوار الهدف: {pos}")
            return True
        handle_dialogue_and_modals()
        time.sleep(0.5)
    raise SafetyStop(f"انتهت مهلة المشي إلى {(x, y, plane)}؛ لن تُنفذ الخطوة التالية")

def interact_object(obj_id, action):
    """التفاعل الصريح مع كائن محدد والتحقق من نجاحه"""
    controller.check()
    if obj_id == 23732 and action == "Climb-up":
        controller.allow_surface_exit = True
    result = api_post("/objects/interact", {"id": obj_id, "action": action})
    controller.require(result, f"التفاعل مع الكائن {obj_id}")
    time.sleep(0.6)
    handle_dialogue_and_modals()
    return result

# ==============================================================================
# منطق قراءة الحالة والقرار الذكي (Smart State Machine & Resume Logic)
# ==============================================================================

def read_progress():
    """قراءة وتحقق صارم من حالة اللعبة والموقع والمكافآت والشنطة والدم دون افتراضات مسبقة"""
    st = api_get("/state")
    if not isinstance(st, dict) or "error" in st:
        return {"status": "UNKNOWN", "reason": "فشل قراءة /state من خادم اللعبة"}
    
    player = st.get("player")
    if not isinstance(player, dict):
        return {"status": "UNKNOWN", "reason": "بيانات اللاعب غير متوفرة في /state"}

    pos = player.get("position")
    if not isinstance(pos, dict):
        return {"status": "UNKNOWN", "reason": "بيانات موضع اللاعب غير متوفرة"}

    px = pos.get("x")
    py = pos.get("y")
    plane = pos.get("plane", 0)

    if not isinstance(px, int) or not isinstance(py, int):
        return {"status": "UNKNOWN", "reason": "إحداثيات اللاعب غير صالحة"}

    # تصنيف المنطقة جغرافياً بدقة بحدود x و y معاً
    if py < 5000:
        region = "SURFACE"
    elif 1855 <= px <= 1935 and 5180 <= py <= 5250:
        region = "FLOOR_1"
    elif 1980 <= px <= 2060 and 5180 <= py <= 5250:
        region = "FLOOR_2"
    elif 2110 <= px <= 2185 and 5240 <= py <= 5315:
        region = "FLOOR_3"
    elif 2300 <= px <= 2380 and 5180 <= py <= 5260:
        region = "FLOOR_4"
    else:
        region = "UNKNOWN_REGION"

    # قراءة الـ Varbits الأربعة مع التحقق من صحتها
    varbits = {}
    for vid in (2309, 2310, 2311, 2312):
        res = api_get(f"/varbits?id={vid}")
        if not isinstance(res, dict) or "value" not in res:
            return {"status": "UNKNOWN", "reason": f"فشل قراءة Varbit {vid}"}
        val = res.get("value")
        if val not in (0, 1):
            return {"status": "UNKNOWN", "reason": f"قيمة Varbit {vid} غير صالحة: {val}"}
        varbits[vid] = val

    # قراءة الحقيبة
    inv_data = api_get("/inventory")
    items = inv_data.get("items", []) if isinstance(inv_data, dict) and isinstance(inv_data.get("items"), list) else []
    has_boots_inv = any(
        (it.get("id") == 9005 or str(it.get("name", "")).strip().lower() == "fancy boots")
        and isinstance(it.get("quantity", 0), int) and it.get("quantity", 0) > 0
        for it in items if isinstance(it, dict)
    )

    # قراءة مستوى الدم
    skills_data = api_get("/skills")
    hp = None
    if isinstance(skills_data, dict) and isinstance(skills_data.get("skills"), list):
        for s in skills_data.get("skills", []):
            if isinstance(s, dict) and s.get("name") == "Hitpoints":
                hp = s.get("boostedLevel", s.get("level"))
                break

    return {
        "status": "VALID",
        "logged_in": st.get("loggedIn", True),
        "position": {"x": px, "y": py, "plane": plane},
        "region": region,
        "varbits": varbits,
        "all_claimed": all(varbits[k] == 1 for k in (2309, 2310, 2311, 2312)),
        "inventory": items,
        "has_boots_in_inventory": has_boots_inv,
        "hp": hp
    }

def choose_next_action(progress):
    """
    دالة قرار مجردة وخالية تماماً من استدعاءات API أو حركة.
    تحدد الخطوة التالية بدقة وفقاً لجدول القرار الصغير في عقد التنفيذ (IMPLEMENTATION_CONTRACT).
    """
    if not isinstance(progress, dict) or progress.get("status") != "VALID":
        reason = progress.get("reason", "قراءة ناقصة أو غير صالحة") if isinstance(progress, dict) else "بيانات غير صالحة"
        return {"action": "STOP", "reason": f"قراءة ناقصة أو موقع غير معروف: {reason}"}

    region = progress.get("region")
    if region == "UNKNOWN_REGION":
        pos = progress.get("position", {})
        return {"action": "STOP", "reason": f"اللاعب في موقع غير معروف داخل الحصن: ({pos.get('x')}, {pos.get('y')})"}

    varbits = progress.get("varbits", {})
    all_claimed = progress.get("all_claimed", False)

    # 1. على السطح
    if region == "SURFACE":
        if all_claimed:
            if progress.get("has_boots_in_inventory"):
                return {"action": "GO_TO_BANK", "reason": "كافة المكافآت مكتملة والجزمة في الحقيبة؛ التوجه للبنك للإيداع"}
            return {"action": "STOP_COMPLETED", "reason": "كافة مكافآت الحصن مكتملة واللاعب على السطح؛ لا داعي لدخول الكهف"}
        else:
            return {"action": "ENTER_STRONGHOLD", "reason": "اللاعب على السطح وتوجد مكافآت غير مستلمة؛ التوجه للمدخل والنزول"}

    # 2. الطابق الأول (Vault of War)
    if region == "FLOOR_1":
        if varbits.get(2309) == 0:
            return {"action": "CLAIM_FLOOR_1_REWARD", "reason": "مكافأة الطابق الأول ناقصة؛ التوجه لصندوق Gift of Peace"}
        else:
            return {"action": "FLOOR_1_TO_FLOOR_2", "reason": "مكافأة الطابق الأول مستلمة؛ التوجه لسلم النزول للطابق الثاني"}

    # 3. الطابق الثاني (Catacomb of Famine)
    if region == "FLOOR_2":
        if varbits.get(2309) == 0:
            return {"action": "STOP", "reason": "داخل الطابق الثاني مع نقص مكافأة الطابق الأول؛ تراجع يدوي مطلوب"}
        if varbits.get(2310) == 0:
            return {"action": "CLAIM_FLOOR_2_REWARD", "reason": "مكافأة الطابق الثاني ناقصة؛ التوجه لصندوق Grain of Plenty"}
        else:
            return {"action": "FLOOR_2_TO_FLOOR_3", "reason": "مكافأة الطابق الثاني مستلمة؛ التوجه لسلم النزول للطابق الثالث"}

    # 4. الطابق الثالث (Pit of Pestilence)
    if region == "FLOOR_3":
        if varbits.get(2309) == 0 or varbits.get(2310) == 0:
            return {"action": "STOP", "reason": "داخل الطابق الثالث مع نقص مكافأة سابقة؛ تراجع يدوي مطلوب"}
        if varbits.get(2311) == 0:
            return {"action": "CLAIM_FLOOR_3_REWARD", "reason": "مكافأة الطابق الثالث ناقصة؛ التوجه لصندوق الـ 5,000 GP"}
        else:
            return {"action": "FLOOR_3_TO_FLOOR_4", "reason": "مكافأة الطابق الثالث مستلمة؛ التوجه لسلم النزول للطابق الرابع"}

    # 5. الطابق الرابع (Sepulchre of Death)
    if region == "FLOOR_4":
        if any(varbits.get(k) == 0 for k in (2309, 2310, 2311)):
            return {"action": "STOP", "reason": "داخل الطابق الرابع مع نقص مكافأة سابقة؛ تراجع يدوي مطلوب"}
        if varbits.get(2312) == 0:
            return {"action": "CLAIM_FLOOR_4_REWARD", "reason": "مكافأة Fancy boots ناقصة؛ التوجه للمهد لاختيار وحصد الجزمة"}
        else:
            return {"action": "EXIT_FLOOR_4_TO_SURFACE", "reason": "كافة مكافآت الحصن مستلمة والجزمة محصودة؛ الخروج عبر البوابة إلى السطح"}

    return {"action": "STOP", "reason": "حالة غير متوقعة"}

def execute_step(action):
    """تنفيذ إجراء واحد محدد ثم العودة لإعادة قراءة الحالة الحية"""
    if action == "ENTER_STRONGHOLD":
        print("\n--- التوجه لمدخل الـ Stronghold في قرية البرابرة ---")
        if not walk_to(3080, 3419, plane=0, timeout=160):
            walk_to(3080, 3419, plane=0, timeout=80)
        print("🖐️ النزول عبر فتحة الصخور (20790)...")
        for attempt in range(5):
            interact_object(20790, "Climb-down")
            for _ in range(8):
                time.sleep(1)
                handle_dialogue_and_modals()
                st = api_get("/state")
                if st.get("player", {}).get("position", {}).get("y", 0) >= 5000:
                    print("📍 تم النزول داخل الكهف بنجاح!")
                    return True
        return False

    elif action == "CLAIM_FLOOR_1_REWARD":
        print("\n--- عبور الطابق الأول (Vault of War) وحصد مكافأة 2,000 GP وحركة Flap ---")
        st = api_get("/state")
        pos = st.get("player", {}).get("position", {}) if isinstance(st, dict) else {}
        px = pos.get("x", 0)
        py = pos.get("y", 0)

        # السير عبر المحطات والأبواب المعتمدة فقط إذا كان اللاعب خارج الغرفة المركزية
        if px < 1895 or py > 5235:
            # محطة 1: بوابة مخرج غرفة البداية
            if px < 1865 and py >= 5232:
                walk_to(1859, 5232, plane=0, timeout=25)
                try_pass_door("Gate of War")

            # محطة 2: الغرفة الجنوبية الغربية
            if px < 1875 and py < 5235:
                walk_to(1864, 5227, plane=0, timeout=15)
                walk_to(1870, 5227, plane=0, timeout=15)
                try_pass_door("Gate of War")

            # محطة 3: الممر الشمالي
            if px < 1895 and py >= 5235:
                walk_to(1875, 5239, plane=0, timeout=20)
                walk_to(1880, 5240, plane=0, timeout=15)
                walk_to(1883, 5243, plane=0, timeout=15)
                try_pass_door("Gate of War")

            # محطة 4: الغرفة الشمالية الشرقية ومدخل الغرفة المركزية
            if px >= 1895 and py > 5235:
                walk_to(1912, 5242, plane=0, timeout=20)
                walk_to(1912, 5237, plane=0, timeout=15)
                walk_to(1905, 5234, plane=0, timeout=15)
                try_pass_door("Gate of War")

        # الوصول لموقع الصندوق في قلب الغرفة المركزية (Gift of Peace: 20656)
        walk_to(1906, 5222, plane=0, timeout=20)

        print("🖐️ التفاعل مع صندوق Gift of Peace (20656)...")
        for attempt in range(5):
            interact_object(20656, "Open")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
            if api_get("/varbits?id=2309").get("value", 0) == 1:
                print("💰 مبروووك! تم استلام مكافأة الطابق الأول (2,000 GP + Flap emote) بنجاح!")
                return True
        raise SafetyStop("فشل حصد مكافأة الطابق الأول بعد التفاعل مع الصندوق (Gift of Peace: 20656)")

    elif action == "FLOOR_1_TO_FLOOR_2":
        print("\n--- عبور الطابق الأول إلى سلم النزول للطابق الثاني ---")
        st = api_get("/state")
        pos = st.get("player", {}).get("position", {}) if isinstance(st, dict) else {}
        px = pos.get("x", 0)
        # إذا كان اللاعب في غرفة البداية (بعيد عن الغرفة المركزية)، يستخدم بوابة الاختصار
        if px < 1880:
            interact_object(20786, "Use")
            time.sleep(2)
            handle_dialogue_and_modals()
        walk_to(1903, 5222, plane=0, timeout=35)
        print("🖐️ النزول عبر سلم الطابق الأول (20785)...")
        for attempt in range(4):
            interact_object(20785, "Climb-down")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
                st = api_get("/state")
                if 1980 <= st.get("player", {}).get("position", {}).get("x", 0) <= 2060:
                    print("📍 تم النزول للطابق الثاني بنجاح!")
                    return True
        return False

    elif action == "CLAIM_FLOOR_2_REWARD":
        print("\n⚠️ تنبيه: مسار صندوق الطابق الثاني (Grain of Plenty) قيد التوثيق الميداني المعتمد.")
        raise SafetyStop("STOP_NOT_IMPLEMENTED: مسار صندوق الطابق الثاني غير معتمد بعد؛ افتح الصندوق يدوياً ثم أعد تشغيل البوت للاستئناف")

    elif action == "FLOOR_2_TO_FLOOR_3":
        print("\n--- عبور الطابق الثاني إلى سلم النزول للطابق الثالث ---")
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

    elif action == "CLAIM_FLOOR_3_REWARD":
        print("\n--- عبور متاهة الطابق الثالث بمحطات وسيطة وحصد 5,000 GP ---")
        walk_to(2132, 5258, plane=0, timeout=25)
        try_pass_door("Oozing barrier")
        walk_to(2132, 5260, plane=0, timeout=15)
        try_pass_door("Oozing barrier")
        walk_to(2132, 5277, plane=0, timeout=30)
        try_pass_door("Oozing barrier")
        walk_to(2144, 5281, plane=0, timeout=30)
        for attempt in range(4):
            interact_object(23709, "Open")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
            if api_get("/varbits?id=2311").get("value", 0) == 1:
                print("💰 مبروووك! تم استلام الـ 5,000 GP بنجاح!")
                return True
        raise SafetyStop("فشل حصد مكافأة الطابق الثالث بعد التفاعل مع الصندوق")

    elif action == "FLOOR_3_TO_FLOOR_4":
        print("\n--- النزول للطابق الرابع عبر السلم (23706) ---")
        walk_to(2147, 5284, plane=0, timeout=30)
        for attempt in range(5):
            interact_object(23706, "Climb-down")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
                st = api_get("/state")
                if 2300 <= st.get("player", {}).get("position", {}).get("x", 0) <= 2380:
                    print("📍 تم النزول للطابق الرابع بنجاح!")
                    return True
        return False

    elif action == "CLAIM_FLOOR_4_REWARD":
        print("\n--- التوجه لمهد الحياة (Cradle of Life) لحصد Fancy Boots ---")
        walk_to(2359, 5230, plane=0, timeout=20)
        try_pass_door("Portal of Death")
        walk_to(2359, 5234, plane=0, timeout=10)
        try_pass_door("Portal of Death")
        walk_to(2341, 5238, plane=0, timeout=25)
        walk_to(2341, 5226, plane=0, timeout=20)
        try_pass_door("Portal of Death")
        walk_to(2341, 5222, plane=0, timeout=10)
        try_pass_door("Portal of Death")
        walk_to(2343, 5215, plane=0, timeout=15)

        for attempt in range(5):
            interact_object(23731, "Search")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
                click_res = api_post("/widgets/click", {"groupId": 270, "childId": 15})
                if isinstance(click_res, dict) and click_res.get("clicked") is True:
                    print("👟 تم النقر بنجاح على ويدجت اختيار Fancy boots!")
            if api_get("/varbits?id=2312").get("value", 0) == 1:
                print("👟 مبروووك! تم اختيار وحصد Fancy Boots بنجاح!")
                return True
        raise SafetyStop("فشل حصد مكافأة الطابق الرابع (Fancy Boots)")

    elif action == "EXIT_FLOOR_4_TO_SURFACE":
        print("\n--- الصعود للسطح عبر الحبل العظمي (Bone Chain: 23732) ---")
        walk_to(2349, 5215, plane=0, timeout=20)
        for attempt in range(4):
            interact_object(23732, "Climb-up")
            for _ in range(6):
                time.sleep(1)
                handle_dialogue_and_modals()
                st = api_get("/state")
                if st.get("player", {}).get("position", {}).get("y", 0) < 5000:
                    print("📍 تم الصعود لسطح الأرض بنجاح!")
                    return True
        return False

    elif action == "GO_TO_BANK":
        print("\n--- التوجه لبنك الـ Grand Exchange لحفظ الأرباح والجزمة ---")
        walk_to(3164, 3487, plane=0, timeout=75)
        controller.require(api_post("/bank/open", {}), "فتح البنك")
        time.sleep(2)
        controller.require(api_post("/bank/deposit", {"all": True}), "طلب الإيداع")
        time.sleep(1)

        bank_data = api_get("/bank")
        if not isinstance(bank_data, dict) or "items" not in bank_data or not isinstance(bank_data.get("items"), list):
            has_boots = False
            coin_display = "الرصيد غير معروف (فشل استعلام البنك)"
        else:
            has_boots = verify_bank_has_boots(bank_data)
            items = bank_data.get("items", [])
            coin_qty = next((it.get("quantity") for it in items if it.get("id") == 995 and isinstance(it.get("quantity"), int)), None)
            coin_display = f"{coin_qty} GP" if coin_qty is not None else "0 GP (لم يُرصد ذهب في الخزينة)"

        api_post("/bank/close", {})
        print("\n" + "=" * 65)
        if has_boots:
            print("✅ تم التحقق الفعلي من وجود Fancy boots بكمية صالحة داخل البنك!")
        else:
            print("⚠️ تنبيه: لم يتم رصد Fancy boots داخل بيانات البنك بعد الإيداع!")
        print(f"💰 رصيد الذهب المسجل بالبنك: {coin_display}.")
        print("=" * 65)
        return has_boots

    return False

def main():
    print("=" * 65)
    print("🚀 مرحباً بك في البوت المستقل الشامل لـ Stronghold of Security")
    print("💰 الهدف: جمع 10,000 GP + Fancy Boots وحفظها في البنك")
    print("⚡ نظام الاستئناف المرن: قراءة الحالة -> قرار -> تنفيذ -> إعادة قراءة")
    print("=" * 65)

    ensure_login()
    api_post("/bank/close", {})

    # فحص أولي سريع إذا كان الحساب قد أتم الحصن بالكامل وموجود على السطح
    st_init = api_get("/state")
    pos_init = st_init.get("player", {}).get("position", {}) if isinstance(st_init, dict) else {}
    px_init = pos_init.get("x", 0) if isinstance(pos_init, dict) else 0
    py_init = pos_init.get("y", 0) if isinstance(pos_init, dict) else 0
    if is_all_rewards_claimed() and py_init < 5000:
        print("\n" + "=" * 65)
        print("🎉 مهمة Stronghold of Security مكتملة رسمياً 100% على هذا الحساب!")
        print("✅ كافة الطوابق الـ 4 مكتملة (Varbits 2309..2312 = 1).")
        print(f"📍 موقع اللاعب الحالي على السطح: ({px_init}, {py_init})؛ لا داعي لدخول الكهف مجدداً.")
        print("=" * 65)
        return True

    max_steps = 30
    steps_taken = 0

    while steps_taken < max_steps:
        steps_taken += 1
        progress = read_progress()
        decision = choose_next_action(progress)
        action = decision.get("action")
        reason = decision.get("reason", "")
        print(f"\n🧭 [دورة {steps_taken}]: القرار الحالي -> {action}")
        print(f"📋 السبب المعتمد: {reason}")

        if action == "STOP_COMPLETED":
            print("\n" + "=" * 65)
            print("🎉 مهمة Stronghold of Security مكتملة رسمياً 100% على هذا الحساب!")
            print("✅ كافة الطوابق الـ 4 مكتملة (Varbits 2309..2312 = 1).")
            print("=" * 65)
            return True

        if action == "STOP":
            print(f"\n⚠️ توقف آمن للمسار: {reason}")
            return False

        success = execute_step(action)
        if not success:
            print(f"❌ تعذر استكمال الإجراء بنجاح: {action}")
            return False

    raise SafetyStop("تم بلوغ الحد الأقصى لدورات القرار دون الوصول لاكتمال أو توقف صريح")

if __name__ == "__main__":
    try:
        with open(TOKEN_PATH, encoding="utf-8") as token_file:
            HEADERS["X-Agent-Token"] = token_file.read().strip()
        main()
    except (SafetyStop, OSError, KeyboardInterrupt) as exc:
        print(f"\nتوقف آمن للسكربت: {exc}")
        print("توقف السكربت لا يوقف قتال اللعبة ولا يضمن سلامة الشخصية. تولَّ التحكم يدوياً فوراً.")
        sys.exit(1)
