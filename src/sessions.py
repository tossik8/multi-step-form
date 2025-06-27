from typing_extensions import Self

import redis

from session import Session

class SessionsCache:

    _instance = None
    _conn: redis.Redis


    def __new__(cls) -> Self:
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._conn = redis.Redis(host="localhost", port=6379, password="mysecretpw", decode_responses=True)
        return cls._instance
    

    def add_session(self, key: str, session: Session):
        self._conn.set(key, session.serialize(), ex=5 * 60)


    def get_session(self, key: str) -> Session | None:
        session = self._conn.get(key)
        if session is None:
            return None
        return Session.deserialize(str(session))
    
    def delete_session(self, key: str):
        self._conn.delete(key)