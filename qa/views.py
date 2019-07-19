import datetime
import sys

from sqlalchemy import create_engine, Column, String, Integer, MetaData, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import request, Blueprint
from sqlalchemy.pool import NullPool
from attendance_manage.views import WorkTime
from constant_name import PRODUCTION_ENGINE, LOCAL_ENGINE

if 'test' in sys.argv:
    '''ローカルエンジン'''
    engine = create_engine(LOCAL_ENGINE, poolclass=NullPool)
else:
    '''本番環境エンジン'''
    engine = create_engine(PRODUCTION_ENGINE, poolclass=NullPool)

meta = MetaData(engine, reflect=True)
Base = declarative_base()
qa = Blueprint('qa', __name__)

MAX_TICKET = 5
MINI_TICKET = 0
QUESTION_COST = 1
FIRST_TICKET = 2
FIRST_INTERN_TICKET = 2
FIRST_EMPLOYEE_TICKET = 3


class User(Base):
    __tablename__ = 'qa_ticket'
    id = Column(String(100), primary_key=True)
    username = Column(String(100), index=True, unique=True)
    count = Column(Integer)
    attendance = Column(Integer, nullable=False)
    is_intern = Column(Integer, nullable=True)

    def __repr__(self):
        return '<User username={username} count={count}>'.format(username=self.username, count=self.count)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


@qa.route('/question', methods=["POST"])
def question():
    session = Session()
    qa_ticket_username = [name for name, in session.query(User.username)]
    post = request.form
    post_name = post['text']
    post_name = post_name.strip("@")
    if post_name[-1:] in " ":
        post_name = post_name.strip(" ")
    if post_name in qa_ticket_username:
        filtered_name = session.query(User).filter(User.username == post_name).first()
        filtered_name_count = filtered_name.count
        if MINI_TICKET < filtered_name.count < MAX_TICKET:
            filtered_name.count -= QUESTION_COST
            session.commit()
            session.close()
            return "残りの質問回数は" + str(filtered_name_count) + "回です！"
        else:
            session.close()
            return '質問回数が不足してます！'
    else:
        session.close()
        return "出勤を記録してください！"


@qa.route('/create', methods=['POST'])
def create():
    session = Session()
    qa_ticket_username = [name for name, in session.query(User.username)]
    created = request.form
    created_name = created["user_name"]
    created_id = created["user_id"]
    created_employee = created["text"]
    if created_employee == "emp":
        new_name = User(id=created_id, username=created_name, count=FIRST_TICKET, attendance=False, is_intern=False)
        session.add(new_name)
        session.commit()
        session.close()
        return created_name + "さんを登録しました！"
    elif not created_name in qa_ticket_username:
        new_name = User(id=created_id, username=created_name, count=FIRST_TICKET, attendance=False, is_intern=True)
        session.add(new_name)
        session.commit()
        session.close()
        return created_name + "さんを登録しました！"

    else:
        session.close()
        return "もうメンバーですよ！"


@qa.route('/attendance', methods=['POST'])
def attendance():
    session = Session()
    qa_ticket_username = [name for name, in session.query(User.username)]
    post = request.form
    post_name = post["user_name"]
    attendance_id = post["user_id"]
    filtered_name = session.query(User).filter(User.username == post_name).first()
    if filtered_name.attendance == True:
        return "出勤済みです"
    elif post_name in qa_ticket_username:
        filtered_name = session.query(User).filter(User.username == post_name).first()
        filtered_name.attendance = True
        filtered_name_time = WorkTime(user_id=attendance_id, username=post_name,
                                      attendance_time=datetime.datetime.now())
        session.add(filtered_name_time)
        session.commit()

        if filtered_name.is_intern == True:
            filtered_name.count = FIRST_INTERN_TICKET
            session.commit()

        else:
            filtered_name.count = FIRST_EMPLOYEE_TICKET
            session.commit()
        session.close()
        return post_name + "さんの出勤を記録しました！"
    else:
        session.close()
        return "メンバー登録してください！"


@qa.route('/leaving_work', methods=['POST'])
def leave():
    session = Session()
    qa_ticket_username = [name for name, in session.query(User.username)]
    post = request.form
    post_name = post["user_name"]

    if post_name in qa_ticket_username:
        leaving_work = session.query(User).filter(User.username == post_name).first()

        leaving_work.attendance = False
        leaving_time_order = session.query(WorkTime).filter(WorkTime.username == post_name).order_by(
            desc(WorkTime.id)).first()

        leaving_time_order.finish_time = datetime.datetime.now()
        session.commit()
        session.close()
        return post_name + "さん,今日もお疲れ様でした!"
    else:
        session.close()
        return "出勤した記録がないですよ！"


HOURLY_TICKET_ADDITION = 2


@qa.route("/counter")
def add_question():
    session = Session()
    add_question_user_list = session.query(User).filter(User.is_intern == True, User.attendance).all()

    for row in add_question_user_list:
        if row.count < 4:
            row.count += HOURLY_TICKET_ADDITION
            session.commit()
        else:
            row.count = MAX_TICKET
            session.commit()

    session.close()
    return "Success"
