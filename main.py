from flask import Flask
from sqlalchemy import create_engine, Column, String, Integer, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import request

engine = create_engine('mysql+pymysql://root:@localhost/question?charset=utf8'
                       )
meta = MetaData(engine, reflect=True)
Base = declarative_base()


class User(Base):
    __tablename__ = 'slack_question'
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

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 日本語文字化け対策
app.config["JSON_SORT_KEYS"] = False  # ソートをそのまま
usernames = [name for name, in session.query(User.username)]


@app.route('/')
def index():
    return 'Index Page'


@app.route('/question', methods=["POST"])
def question():
    posted = request.form
    posted_name = posted['user_name']
    usernames = [name for name, in session.query(User.username)]
    if posted_name in usernames:
        filtered = session.query(User).filter(User.username == posted_name).first()
        if 0 < filtered.count < 5:
            filtered.count -= 1
            session.commit()
            return "残りの質問回数は" + str(filtered.count) + "回です！"
        else:
            return '質問回数が不足してます！'
    else:
        return "出勤を記録してください！"


@app.route('/create', methods=['POST'])
def create():
    created = request.form
    created_name = created["user_name"]
    created_id = created["user_id"]
    usernames = [name for name, in session.query(User.username)]
    if not created_name in usernames:

        newname = User(id=created_id, username=created_name, count=2, attendance=False, is_intern=True)
        session.add(newname)
        session.commit()
        return created_name + "さんを登録しました！"
    else:
        return "もうメンバーですよ！"


@app.route('/attendance', methods=['POST'])
def attendance():
    post_data = request.form
    post_name = post_data["user_name"]
    usernames = [name for name, in session.query(User.username)]
    if post_name in usernames:
        attended = session.query(User).filter(User.username == post_name).first()
        attended.attendance = True
        if attended.is_intern == True:
            attended.count += 2
            session.commit()
        else:
            attended.count += 3
            session.commit()
        return post_name + "さんの出勤を記録しました！"
    else:
        return "メンバー登録してください！"


@app.route('/leaving_work', methods=['POST'])
def leave():
    post_data = request.form
    post_name = post_data["user_name"]
    usernames = [name for name, in session.query(User.username)]
    if post_name in usernames:
        leaving_work = session.query(User).filter(User.username == post_name).first()
        leaving_work.attendance = False

        session.commit()
        return post_name + "さん,今日もお疲れ様でした!"
    else:
        return "出勤した記録がないですよ！"


if __name__ == "__main__":
    app.run(debug=True)
