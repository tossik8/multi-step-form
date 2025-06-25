import time


class Session:

    def __init__(self, name = "", email = "", tel = ""):
        self.name = name
        self.email = email
        self.tel = tel
        self.plan_id = 1
        self._plan = {}
        self.yearly = False
        self.add_on_ids = []
        self._add_ons = []
        self.update_last_activity_time()

    
    def update_last_activity_time(self):
        self.last_activity_time = time.time()

    
    def find_plan(self, plans):
        for plan in plans:
            if plan["id"] == self.plan_id:
                self._plan = plan
                break

        
    def find_add_ons(self, add_ons):
        self._add_ons.clear()
        for add_on in add_ons:
            if add_on["id"] in self.add_on_ids:
                self._add_ons.append(add_on)


    def _get_price(self, price: dict[str, int]):
        return price["yearly"] if self.yearly else price["monthly"]

    
    def calculate_total(self):
        total = self._get_price(self._plan["price"])
        for add_on in self._add_ons:
            total += self._get_price(add_on["price"])
        return total


    @classmethod
    def is_valid(cls, session: dict, step: int = 0):
        if "id" not in session or session["id"] not in sessions:
            return False
        session_data = sessions[session["id"]]
        if step >= 3:
            if session_data._plan == {}:
                return False
        return True



sessions = dict[str, Session]()

def clear_inactive_sessions():
    interval = 5 * 60
    while True:
        time.sleep(interval)
        for key in list(sessions.keys()):
            if time.time() - sessions[key].last_activity_time > interval:
                del sessions[key]



            


    