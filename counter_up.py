from main import User
from sqlalchemy import create_engine, Column, String, Integer, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('mysql+pymysql://root:@localhost/question?charset=utf8')

Base = declarative_base()
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def add_question():
    session = Session()
    users = session.query(User).filter(User.is_intern == True, User.attendance).all()

    for i in users:
        if i.count < 4:
            i.count += 2
            session.commit()
        else:
            i.count = 5
            session.commit()


add_question()
