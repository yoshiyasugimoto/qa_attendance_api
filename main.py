import datetime
import os

from flask import session as cook
import pytz
from flask import Flask, render_template, flash
from sqlalchemy import create_engine, Column, String, Integer, MetaData, DateTime, desc, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import request
from sqlalchemy.pool import NullPool

engine = create_engine('mysql+pymysql://root:@localhost/question?charset=utf8'
                       , poolclass=NullPool)  # local用
# engine = create_engine(
#     'mysql+pymysql://root:task-wktk@/question?unix_socket=/cloudsql/mlab-apps:asia-northeast1:mlab-apps-sql'
#     , poolclass=NullPool)
meta = MetaData(engine, reflect=True)
Base = declarative_base()

app = Flask(__name__)
app.secret_key = "hoge"


class User(Base):
    __tablename__ = 'slack_question'
    id = Column(String(100), primary_key=True)
    username = Column(String(100), index=True, unique=True)
    count = Column(Integer)
    attendance = Column(Integer, nullable=False)
    is_intern = Column(Integer, nullable=True)

    def __repr__(self):
        return '<User username={username} count={count}>'.format(username=self.username, count=self.count)


class Work_time(Base):
    __tablename__ = 'Work_time'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), index=True)
    username = Column(String(100), index=True)
    attendance_time = Column(DateTime(), default=datetime.datetime.now(pytz.timezone('Asia/Tokyo')))
    finish_time = Column(DateTime(), onupdate=datetime.datetime.now(pytz.timezone('Asia/Tokyo')))

    def __repr__(self):
        return '<User username={username} >'.format(username=self.username)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 日本語文字化け対策
app.config["JSON_SORT_KEYS"] = False  # ソートをそのまま
usernames = [name for name, in session.query(User.username)]
usernames_time = [name for name, in session.query(Work_time.username)]
session.close()


@app.route('/show_entry', methods=["GET"])
def show_entries():
    if not cook.get('logged_in'):
        return render_template('login.html')
    else:
        id = session.query(Work_time.id).order_by(desc(Work_time.id)).all()
        id_data = [i for i, in id]
        all_name = session.query(Work_time.username).order_by(desc(Work_time.id)).all()
        all__name_string = [name for name, in all_name]
        times_att = [timer for timer, in session.query(Work_time.attendance_time).order_by(desc(Work_time.id))]
        times_fin = [timer for timer, in session.query(Work_time.finish_time).order_by(desc(Work_time.id))]
        times_att_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in times_att]

        times_fin_string = []
        for num in times_fin:
            try:
                times_fin_string.append(num.strftime('%Y-%m-%d_%H:%M:%S'))
            except AttributeError:
                print(ValueError)
                times_fin_string.append("打刻されていません")
        return render_template("show_entry.html", id=id_data, all__name_string=all__name_string,
                               times_att_string=times_att_string,
                               times_fin_string=times_fin_string, )


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
    attendance_id = post_data["user_id"]

    attended = session.query(User).filter(User.username == post_name).first()
    if attended.attendance == True:
        return "出勤済みです"
    elif post_name in usernames:
        attended = session.query(User).filter(User.username == post_name).first()
        attended.attendance = True
        attended_time = Work_time(user_id=attendance_id, username=post_name, attendance_time=datetime.datetime.now())
        session.add(attended_time)
        session.commit()

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
        session.close()
        return "メンバー登録してください！"


@app.route('/leaving_work', methods=['POST'])
def leave():
    session = Session()
    post_data = request.form
    post_name = post_data["user_name"]
    usernames = [name for name, in session.query(User.username)]

    if post_name in usernames:
        session = Session()
        leaving_work = session.query(User).filter(User.username == post_name).first()

        leaving_work.attendance = False
        leaving_time_order = session.query(Work_time).filter(Work_time.username == post_name).order_by(
            desc(Work_time.id)).first()

        leaving_time_order.finish_time = datetime.datetime.now()

        session.commit()
        session.close()
        return post_name + "さん,今日もお疲れ様でした!"
    else:
        session.close()
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
    return "Success"


@app.route("/filter", methods=['GET', 'POST'])
def filter():
    if not cook.get('logged_in'):
        return render_template('login.html')
    else:
        if request.method == "POST":
            session = Session()
            postname = request.form["username"]
            start_date = request.form["検索開始日"]
            end_date = request.form["検索終了日"]
            usernames = [name for name, in session.query(Work_time.username)]
            data_att = session.query(Work_time.attendance_time).order_by(desc(Work_time.id)).all()
            times_att = [timer for timer, in data_att]

            try:
                start_date_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d_%H:%M:%S")
                end_date_datetime = datetime.datetime.strptime(end_date, "%Y-%m-%d_%H:%M:%S")

                for dates_date in times_att:
                    if start_date_datetime <= dates_date <= end_date_datetime and postname in usernames:

                        result_att = session.query(Work_time.attendance_time).filter(
                            Work_time.username == postname).order_by(
                            desc(Work_time.id)).all()
                        times_att = [timer for timer, in result_att]
                        result_name = session.query(Work_time.username).filter(
                            Work_time.username == postname).order_by(
                            desc(Work_time.id)).all()
                        result_name_name = [timer for timer, in result_name]
                        times_att_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in times_att]
                        result_fin = session.query(Work_time.finish_time).filter(
                            Work_time.username == postname).order_by(
                            desc(Work_time.id)).all()
                        times_fin = [timer for timer, in result_fin]
                        times_fin_string = []
                        times_sum_date = []
                        overtimes_sum_date = []
                        alltimes_sum_date = []

                        for num, i in zip(times_fin, times_att):

                            try:
                                times_fin_string.append(num.strftime('%Y-%m-%d_%H:%M:%S'))
                                d = num - i
                                if num - i >= datetime.timedelta(hours=7):
                                    if d - datetime.timedelta(hours=1) >= datetime.timedelta(hours=8):
                                        times_sum_date.append(datetime.time(hour=8, minute=0, second=0))
                                        overtimes_sum_date.append(d - datetime.timedelta(hours=9))
                                        alltimes_sum_date.append(d - datetime.timedelta(hours=1))

                                elif datetime.timedelta(hours=6) <= d < datetime.timedelta(hours=7):
                                    times_sum_date.append(datetime.time(hour=6, minute=0, second=0))
                                    alltimes_sum_date.append(datetime.time(hour=6, minute=0, second=0))
                                    overtimes_sum_date.append("残業なし")
                                else:
                                    times_sum_date.append(d)
                                    alltimes_sum_date.append(d)
                                    overtimes_sum_date.append("残業なし")

                            except:
                                import pdb;
                                pdb.set_trace()
                                times_fin_string.append("打刻されていません")
                                times_sum_date.append("打刻されていません")
                                overtimes_sum_date.append("打刻されていません")
                                alltimes_sum_date.append("打刻されていません")

                        session.close()

                        return render_template("result.html", usernames=result_name_name,
                                               times_att_string=times_att_string,
                                               times_fin_string=times_fin_string, times_sum_date=times_sum_date,
                                               overtimes_sum_date=overtimes_sum_date,
                                               alltimes_sum_date=alltimes_sum_date)
                    elif postname == '':
                        # import pdb;pdb.set_trace()
                        date_name = session.query(Work_time.username).order_by(desc(Work_time.id)).filter(
                            Work_time.attendance_time.between(start_date_datetime, end_date_datetime)).all()
                        date_name_name = [name for name, in date_name]
                        date_att = session.query(Work_time.attendance_time).order_by(desc(Work_time.id)).filter(
                            Work_time.attendance_time.between(start_date_datetime, end_date_datetime)).all()
                        date_att_att = [timer for timer, in date_att]
                        times_att_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in date_att_att]

                        time_and_fin = session.query(Work_time.finish_time).filter(
                            Work_time.attendance_time.between(start_date_datetime, end_date_datetime)).order_by(
                            desc(Work_time.id)).all()
                        times_fin = [timer for timer, in time_and_fin]
                        times_fin_string = []
                        times_sum_date = []
                        overtimes_sum_date = []
                        alltimes_sum_date = []

                        for num, i in zip(times_fin, date_att_att):
                            try:
                                times_fin_string.append(num.strftime('%Y-%m-%d_%H:%M:%S'))
                                d = num - i
                                if num - i >= datetime.timedelta(hours=7):
                                    if d - datetime.timedelta(hours=1) >= datetime.timedelta(hours=8):
                                        times_sum_date.append(datetime.time(hour=8, minute=0, second=0))
                                        overtimes_sum_date.append(d - datetime.timedelta(hours=9))
                                        alltimes_sum_date.append(d - datetime.timedelta(hours=1))

                                elif datetime.timedelta(hours=6) <= num - i < datetime.timedelta(hours=7):
                                    times_sum_date.append(datetime.time(hour=6, minute=0, second=0))
                                    alltimes_sum_date.append(datetime.time(hour=6, minute=0, second=0))
                                    overtimes_sum_date.append("残業なし")
                                else:
                                    times_sum_date.append((num - i))
                                    alltimes_sum_date.append((num - i))
                                    overtimes_sum_date.append("残業なし")

                            except AttributeError:
                                print(ValueError)
                                times_fin_string.append("打刻されていません")
                                times_sum_date.append("打刻されていません")
                                overtimes_sum_date.append("打刻されていません")
                                alltimes_sum_date.append("打刻されていません")
                        session.close()
                        return render_template("result.html", usernames=date_name_name,
                                               times_att_string=times_att_string,
                                               times_fin_string=times_fin_string, times_sum_date=times_sum_date,
                                               overtimes_sum_date=overtimes_sum_date,
                                               alltimes_sum_date=alltimes_sum_date)


                else:
                    flash("検索条件に当てはまるデータがありません")
                    return render_template("confirm.html")
            except:

                if postname in usernames:
                    result_att = session.query(Work_time.attendance_time).filter(
                        Work_time.username == postname).order_by(
                        desc(Work_time.id)).all()
                    times_att = [timer for timer, in result_att]
                    times_att_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in times_att]
                    result_fin = session.query(Work_time.finish_time).filter(
                        Work_time.username == postname).order_by(
                        desc(Work_time.id)).all()
                    times_fin = [timer for timer, in result_fin]
                    times_fin_string = []
                    times_sum_date = []
                    overtimes_sum_date = []
                    alltimes_sum_date = []

                    for num, i in zip(times_fin, times_att):
                        try:
                            times_fin_string.append(num.strftime('%Y-%m-%d_%H:%M:%S'))
                            d = num - i
                            if num - i >= datetime.timedelta(hours=7):
                                if d - datetime.timedelta(hours=1) >= datetime.timedelta(hours=8):
                                    times_sum_date.append(datetime.time(hour=8, minute=0, second=0))
                                    overtimes_sum_date.append(d - datetime.timedelta(hours=9))
                                    alltimes_sum_date.append(d - datetime.timedelta(hours=1))

                            elif datetime.timedelta(hours=6) <= num - i < datetime.timedelta(hours=7):
                                times_sum_date.append(datetime.time(hour=6, minute=0, second=0))
                                alltimes_sum_date.append(datetime.time(hour=6, minute=0, second=0))
                                overtimes_sum_date.append("残業なし")
                            else:
                                times_sum_date.append((num - i))
                                alltimes_sum_date.append((num - i))
                                overtimes_sum_date.append("残業なし")

                        except AttributeError:
                            print(ValueError)
                            times_fin_string.append("打刻されていません")
                            times_sum_date.append("打刻されていません")
                            overtimes_sum_date.append("打刻されていません")
                            alltimes_sum_date.append("打刻されていません")

                    session.close()
                    return render_template("result.html", usernames=usernames, times_att_string=times_att_string,
                                           times_fin_string=times_fin_string, times_sum_date=times_sum_date,
                                           overtimes_sum_date=overtimes_sum_date,
                                           alltimes_sum_date=alltimes_sum_date)
        else:
            flash("検索条件に当てはまるデータがありません")
        return render_template("confirm.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["loginname"] == "mlab" and request.form["password"] == "password":
            cook['logged_in'] = True
            return show_entries()
        else:
            flash("ログイン名、パスワードを正しく入力してください")
    return render_template("login.html")


@app.route("/edit/<int:id>", methods=['GET'])
def edit(id):
    ids = session.query(Work_time.id).filter(Work_time.id == id).all()
    ids_date = [ids_dates for ids_dates, in ids]
    all_name = session.query(Work_time.username).order_by(desc(Work_time.id)).filter(Work_time.id == id).all()
    all__name_string = [name for name, in all_name]
    times_att = [timer for timer, in
                 session.query(Work_time.attendance_time).order_by(desc(Work_time.id)).filter(Work_time.id == id)]
    times_fin = [timer for timer, in
                 session.query(Work_time.finish_time).order_by(desc(Work_time.id)).filter(Work_time.id == id)]
    times_att_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in times_att]
    times_fin_string = []
    for num in times_fin:
        try:
            times_fin_string.append(num.strftime('%Y-%m-%d_%H:%M:%S'))
        except AttributeError:
            print(ValueError)
            times_fin_string.append("打刻されていません")
    return render_template("edit.html", ids=ids_date[0], all__name_string=all__name_string,
                           times_att_string=times_att_string,
                           times_fin_string=times_fin_string, )


@app.route("/edit/<int:id>/update", methods=["POST"])
def edit_update(id):
    session = Session()
    user_id = session.query(Work_time).order_by(desc(Work_time.id)).filter(id == id).first()
    updated = request.form
    att_date_time = updated["time_att_time"]
    fin_date_time = updated["time_fin_time"]
    att_date_time_sql = datetime.datetime.strptime(att_date_time, '%Y-%m-%d_%H:%M:%S')
    user_id.username = updated["username"]
    user_id.attendance_time = att_date_time_sql
    times_sum_date = []
    overtimes_sum_date = []
    alltimes_sum_date = []
    try:
        fin_date_time_sql = datetime.datetime.strptime(fin_date_time, '%Y-%m-%d_%H:%M:%S')
        fin_date_time_sql_string = fin_date_time_sql.strftime('%Y-%m-%d_%H:%M:%S')
        d = fin_date_time_sql - att_date_time_sql
        if d >= datetime.timedelta(hours=7):
            if d - datetime.timedelta(hours=1) >= datetime.timedelta(hours=8):
                times_sum_date.append(datetime.time(hour=8, minute=0, second=0))
                overtimes_sum_date.append(d - datetime.timedelta(hours=9))
                alltimes_sum_date.append(d - datetime.timedelta(hours=1))
        elif datetime.timedelta(hours=6) <= d < datetime.timedelta(hours=7):
            times_sum_date.append(datetime.time(hour=6, minute=0, second=0))
            alltimes_sum_date.append(datetime.time(hour=6, minute=0, second=0))
            overtimes_sum_date = "残業なし"
        else:
            times_sum_date.append(d)
            alltimes_sum_date.append(d)
            overtimes_sum_date.append("残業なし")
    except:
        fin_date_time_sql = None
        fin_date_time_sql_string = "打刻されていません"
        times_sum_date.append("打刻されていません")
        overtimes_sum_date.append("打刻されていません")
        alltimes_sum_date.append("打刻されていません")
    user_id.finish_time = fin_date_time_sql
    att_date_time_sql_string = att_date_time_sql.strftime('%Y-%m-%d_%H:%M:%S')
    session.commit()
    session.close()

    return render_template("result.html", usernames=[updated["username"]], times_att_string=[att_date_time_sql_string],
                           times_fin_string=[fin_date_time_sql_string], times_sum_date=times_sum_date,
                           overtimes_sum_date=overtimes_sum_date,
                           alltimes_sum_date=alltimes_sum_date)


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True)
