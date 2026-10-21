"""Fail-closed guards for the documented API shape; unsupported shapes stop."""
import time

class SafetyStop(RuntimeError):
    pass

class SafetyController:
    def __init__(self, get, post):
        self.get, self.post = get, post
        self.was_underground = False
        self.allow_surface_exit = False
        self.last_position = None

    @staticmethod
    def require(result, operation):
        if not isinstance(result, dict) or result.get('success') is not True:
            raise SafetyStop(f'{operation}: لم يؤكد الخادم نجاح الطلب: {result}')
        return result

    def position(self):
        state = self.get('/state')
        if state.get('loggedIn') is not True:
            raise SafetyStop('الحساب غير متصل أو حالة الاتصال غير معروفة')
        pos = state.get('player', {}).get('position', {})
        values = tuple(pos.get(k) for k in ('x', 'y', 'plane'))
        if not all(type(v) is int for v in values) or values[0] <= 0 or values[1] <= 0:
            raise SafetyStop('تعذر قراءة موقع صالح')
        x, y, plane = values
        if self.was_underground and y < 5000 and not self.allow_surface_exit:
            raise SafetyStop('خروج غير متوقع إلى السطح؛ احتمال موت أو انتقال. لن نتابع المسار')
        if self.last_position and not self.allow_surface_exit:
            old_x, old_y, _ = self.last_position
            # Floor changes may be large, but only explicit interaction should cause them.
            if y >= 5000 and old_y >= 5000 and max(abs(x-old_x), abs(y-old_y)) > 256:
                raise SafetyStop('انتقال كبير غير متوقع؛ افحص الموقع يدوياً')
        self.was_underground = self.was_underground or y >= 5000
        self.last_position = values
        return values

    def check(self):
        pos = self.position()
        data = self.get('/skills')
        skills = data.get('skills')
        if not isinstance(skills, list):
            raise SafetyStop('صيغة /skills غير مدعومة؛ لن نفترض أن الدم سليم')
        hp = next((s for s in skills if str(s.get('name', '')).casefold() == 'hitpoints'), None)
        current = hp.get('boostedLevel') if hp else None
        if type(current) is not int or current <= 0:
            raise SafetyStop('قراءة الدم الحالي غير صالحة؛ مطلوب boostedLevel')
        inventory = self.get('/inventory')
        items = inventory.get('items')
        if not isinstance(items, list):
            raise SafetyStop('تعذر قراءة الشنطة')
        # Exact known foods only: no raw fish, burnt food or substring guesses.
        foods = {'shrimps', 'shrimp', 'trout', 'salmon', 'cooked meat', 'bread', 'tuna', 'lobster', 'swordfish', 'monkfish', 'shark'}
        food = next((i for i in items if str(i.get('name', '')).casefold() in foods and type(i.get('id')) is int), None)
        if food is None:
            raise SafetyStop('لا يوجد طعام مدعوم في الشنطة؛ توقف وتحكم يدوياً')
        if current <= 7:
            self.require(self.post('/inventory/interact', {'id': food['id'], 'action': 'Eat'}), 'الأكل')
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                self.position()
                updated = self.get('/skills').get('skills', [])
                new_hp = next((s.get('boostedLevel') for s in updated if str(s.get('name', '')).casefold() == 'hitpoints'), None)
                if type(new_hp) is int and new_hp > current:
                    return pos
                time.sleep(0.2)
            raise SafetyStop('لم تُرصد زيادة الدم بعد الأكل')
        return pos
