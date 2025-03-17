import os
import threading
from contextlib import contextmanager
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.engine import create_engine
from config import Config

class Database():
    _instance = None
    _engine = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
                cls._engine = create_engine(url=Config.SQLALCHEMY_DATABASE_URI)
    
        return cls._instance
    
    @contextmanager
    def session(cls):
        SessionLocal = scoped_session(sessionmaker(autoflush=False, bind=cls._engine, autocommit=False))
        session = SessionLocal()

        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()