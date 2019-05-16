import datetime

import pytz
from flask import Flask
from sqlalchemy import create_engine, Column, String, Integer, MetaData, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import request
from sqlalchemy.pool import NullPool

# engine = create_engine('mysql+pymysql://root:@localhost/question?charset=utf8'
#                        , poolclass=NullPool)  # local用
engine = create_engine(
    'mysql+pymysql://root:task-wktk@/question?unix_socket=/cloudsql/mlab-apps:asia-northeast1:mlab-apps-sql'
    , poolclass=NullPool)
meta = MetaData(engine, reflect=True)
Base = declarative_base()


class User(Base):
    __tablename__ = 'slack_question'
    id = Column(String(100), primary_key=True)
    username = Column(String(100), index=True, unique=True)
    count = Column(Integer)
    attendance = Column(Integer, nullable=False)
    is_intern = Column(Integer, nullable=True)

    # attendance_time = Column(DateTime(), default=datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
    # finish_time = Column(DateTime(), default=datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
    def __repr__(self):
        return '<User username={username} count={count}>'.format(username=self.username, count=self.count)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 日本語文字化け対策
app.config["JSON_SORT_KEYS"] = False  # ソートをそのまま
usernames = [name for name, in session.query(User.username)]
session.close()


@app.route('/')
def index():
    return 'Index Page'


@app.route('/question', methods=["POST"])
def question():
    session = Session()
    posted = request.form
    posted_name = posted['text']
    posted_name = posted_name.strip("@")
    if posted_name[-1:] in " ":
        posted_name = posted_name.strip(" ")
    usernames = [name for name, in session.query(User.username)]
    session.close()
    if posted_name in usernames:
        filtered = session.query(User).filter(User.username == posted_name).first()
        filtered_count = filtered.count
        if 0 < filtered.count < 5:
            filtered.count -= 1
            session.commit()
            session.close()
            return "残りの質問回数は" + str(filtered_count) + "回です！"
        else:
            return '質問回数が不足してます！'
    else:
        return "出勤を記録してください！"


@app.route('/create', methods=['POST'])
def create():
    session = Session()
    created = request.form
    created_name = created["user_name"]
    created_id = created["user_id"]
    created_emp = created["text"]
    usernames = [name for name, in session.query(User.username)]
    session.close()
    if created_emp == "emp":
        newname = User(id=created_id, username=created_name, count=2, attendance=False, is_intern=False)
        session.add(newname)
        session.commit()
        session.close()
        return created_name + "さんを登録しました！"

    elif not created_name in usernames:
        newname = User(id=created_id, username=created_name, count=2, attendance=False, is_intern=True)
        session.add(newname)
        session.commit()
        session.close()
        return created_name + "さんを登録しました！"

    else:
        return "もうメンバーですよ！"


@app.route('/attendance', methods=['POST'])
def attendance():
    session = Session()
    post_data = request.form
    post_name = post_data["user_name"]
    usernames = [name for name, in session.query(User.username)]
    attended = session.query(User).filter(User.username == post_name).first()
    session.close()
    if attended.attendance == True:
        return "出勤済みです"
    elif post_name in usernames:
        attended = session.query(User).filter(User.username == post_name).first()
        attended.attendance = True
        if attended.is_intern == True:
            attended.count = 2
            session.commit()
            session.close()
        else:
            attended.count = 3
            session.commit()
            session.close()
        return post_name + "さんの出勤を記録しました！"
    else:
        return "メンバー登録してください！"


@app.route('/leaving_work', methods=['POST'])
def leave():
    session = Session()
    post_data = request.form
    post_name = post_data["user_name"]
    usernames = [name for name, in session.query(User.username)]
    session.close()
    if post_name in usernames:
        session = Session()
        leaving_work = session.query(User).filter(User.username == post_name).first()
        leaving_work.attendance = False
        session.commit()
        session.close()
        return post_name + "さん,今日もお疲れ様でした!"
    else:
        return "出勤した記録がないですよ！"


@app.route("/counter")
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

    session.close()
    return "success"


if __name__ == "__main__":
    app.run(debug=True)
