import json
from dataclasses import dataclass, field


@dataclass
class Session:
    name: str
    email: str
    tel: str
    plan_id: int = 1
    _plan: dict = field(default_factory=dict)
    yearly: bool = False
    add_on_ids: list[int] = field(default_factory=list)
    _add_ons: list[dict] = field(default_factory=list)
    deleted: bool = False

    
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
    

    def serialize(self):
        return json.dumps(vars(self))


    @classmethod
    def deserialize(cls, session: str):
        return cls(**json.loads(session))

