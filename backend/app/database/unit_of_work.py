from app.database.session import SessionLocal


class UnitOfWork:
    def __enter__(self):
        self.session = SessionLocal()
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
