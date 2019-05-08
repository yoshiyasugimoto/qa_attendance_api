from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, String, Integer, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import jsonify, request

import time
import schedule

engine = create_engine('mysql+pymysql://root:@localhost/question?charset=utf8'
                       )
meta = MetaData(engine, reflect=True)
Base = declarative_base()

usernames = ["yoshiyasugimoto", "Satoko Ouchi", "Takashima Katsu", "Yuki Matsukuma", "Yusuke Hamaike", "杉本 義弥",
             "Kai Sato", "muraho", "saori murakami"]


class User(Base):
    __tablename__ = 'slack_question'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), index=True, unique=True)
    count = Column(Integer)

    def __repr__(self):
        return '<User username={username} count={count}>'.format(username=self.username, count=self.count)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 日本語文字化け対策
app.config["JSON_SORT_KEYS"] = False  # ソートをそのまま


@app.route('/')
def index():
    return 'Index Page'


def morning():
    session.rollback()
    session.commit()


# schedule.every(1).minutes.do(morning)  # 毎分初期化


schedule.every().day.at('07:00').do(morning)  # 毎朝7時初期化


@app.route('/question', methods=["POST"])
def question():
    posted = request.get_json()
    # incomeCounter = posted[]
    # import pdb;
    # pdb.set_trace()
    if posted['username'] in usernames:
        session.begin_nested()
        filtered = session.query(User).filter(User.id == 1).first()
        filtered.count -= 1  # update
        session.commit()

        # counter = session.query(User.count).filter(User.username == "yoshiyasugimoto").first()
        # playload = {
        #     counter
        # }
        # return jsonify(counter)
        return jsonify(session.query(User.count).filter(User.username == posted["username"]).first())
    else:
        return "no name"


if __name__ == "__main__":
    app.run(debug=True)
