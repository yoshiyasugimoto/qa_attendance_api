from flask import Blueprint
from datetime import datetime, timedelta, time

from flask import session as cook
import pytz
from pytz import timezone
from flask import render_template, flash, request
from sqlalchemy import create_engine, Column, String, Integer, MetaData, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from constant_name import PRODUCTION_ENGINE, LOCAL_ENGINE

'''本番環境エンジン'''
# engine = create_engine(PRODUCTION_ENGINE, poolclass=NullPool)

'''ローカルエンジン'''
engine = create_engine(LOCAL_ENGINE, poolclass=NullPool)

meta = MetaData(engine, reflect=True)
Base = declarative_base()


class WorkTime(Base):
    __tablename__ = 'work_time'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), index=True)
    username = Column(String(100), index=True)
    attendance_time = Column(DateTime(), default=datetime.now(pytz.timezone('Asia/Tokyo')))
    finish_time = Column(DateTime(), onupdate=datetime.now(pytz.timezone('Asia/Tokyo')))

    def __repr__(self):
        return '<User username={username} >'.format(username=self.username)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
attendance_manage = Blueprint('attendance_manage', __name__,
                              template_folder='templates')

REST_TIME = 1
WORKING_TIME = 6
MAX_WORKING_TIME = 8

'''全データの出力'''


@attendance_manage.route('/show_entry', methods=["GET"])
def show_entries():
    session = Session()
    all_record = session.query(WorkTime).order_by(desc(WorkTime.id)).all()
    context = data_send_html(all_record)
    return render_template("show_entry.html", context=context)


def data_send_html(all_record):
    context = []
    for row in all_record:
        finish_time_string, overworking_time, total_working_time, working_time = work_time_data(row.attendance_time,
                                                                                                row.finish_time)
        sample_dict = {
            "id": row.id,
            "username": row.username,
            "attendance_time": caluc_attendance_time(row.attendance_time),
            "finish_time": finish_time_string,
            "working_time": working_time,
            "overworking_time": overworking_time,
            "total_working_time": total_working_time}
        context.append(sample_dict)
    return context


'''退勤、残業総労働時間の生成'''


def work_time_data(attendance_time, finish_time):
    try:
        finish_timezone_jst = calcu_jst_time(finish_time)
        finish_time_string = finish_timezone_jst.strftime('%Y-%m-%d_%H:%M%z')
        total_time = finish_time - attendance_time
        if total_time >= timedelta(hours=REST_TIME + MAX_WORKING_TIME):
            working_time = time(hour=MAX_WORKING_TIME)
            overworking_time = total_time - timedelta(hours=MAX_WORKING_TIME + REST_TIME)
            total_working_time = total_time - timedelta(hours=REST_TIME)
        elif timedelta(hours=WORKING_TIME) <= total_time < timedelta(
                hours=REST_TIME + WORKING_TIME):
            working_time = timedelta(hours=WORKING_TIME)
            total_working_time = timedelta(hours=WORKING_TIME)
            overworking_time = "残業なし"
        else:
            working_time = total_time
            total_working_time = total_time
            overworking_time = "残業なし"
    except:
        finish_time_string = "打刻されていません"
        working_time = "打刻されていません"
        overworking_time = "打刻されていません"
        total_working_time = "打刻されていません"

    return finish_time_string, overworking_time, total_working_time, working_time


'''出退勤時間を整形する'''


def calcu_jst_time(_time):
    return pytz.timezone("UTC").localize(_time).astimezone(pytz.timezone("Asia/Tokyo")).replace(tzinfo=None)


'''出勤時間の整形'''


def caluc_attendance_time(attendance_time):
    try:
        attendance_timezone_jst = calcu_jst_time(attendance_time)
        attendance_time_string = attendance_timezone_jst.strftime("%Y-%m-%d_%H:%M%z")

        return attendance_time_string
    except:
        attendance_time_string = "打刻されていません"

        return attendance_time_string


'''検索機能'''


@attendance_manage.route("/filter", methods=['GET', 'POST'])
def filter():
    if request.method == "POST":
        sum_total_working_time = 0
        session = Session()
        username = request.form["username"]
        start_time = request.form["search_start"]
        end_time = request.form["search_end"]

        filtered_username_record = session.query(WorkTime).filter(WorkTime.username == username).order_by(
            desc(WorkTime.id)).all()
        filtered_username_context = data_send_html(filtered_username_record)

        try:
            search_end_datetime, search_start_datetime = calcu_search_time(start_time, end_time)

            '''名前$時間検索'''
            if filtered_username_context:
                if not filtered_username_context:
                    flash("検索条件に当てはまるデータがありません")
                    return render_template("confirm.html")

                filtered_username_time_record = session.query(WorkTime).order_by(desc(WorkTime.id)).filter(
                    WorkTime.attendance_time.between(search_start_datetime, search_end_datetime)).filter(
                    WorkTime.username == username).all()

                filtered_username_time_context = data_send_html(filtered_username_time_record)

                return render_template("result.html", context=filtered_username_time_context,
                                       sum_total_working_time=sum_total_working_time)

                '''時間のみ検索'''
            elif username == '':
                filtered_time_record = session.query(WorkTime).order_by(desc(WorkTime.id)).filter(
                    WorkTime.attendance_time.between(search_start_datetime, search_end_datetime)).all()

                filtered_time_context = data_send_html(filtered_time_record)

                return render_template("result.html", context=filtered_time_context)

            '''名前のみ検索'''
        except:
            if username:
                return render_template("result.html", context=filtered_username_context)
            else:
                flash("検索条件に当てはまるデータがありません")
                return render_template("confirm.html")

    else:
        return render_template("confirm.html")


'''検索する名前の整形'''


def search_username(username, session):
    return [name for name, in session.query(WorkTime.username).filter(
        WorkTime.username == username).order_by(
        desc(WorkTime.id)).all()]


'''検索する時間の整形'''


def calcu_search_time(start_time, end_time):
    search_start_datetimes = datetime.strptime(start_time, "%Y-%m-%d_%H:%M:%S")
    search_start_datetime = pytz.timezone("Asia/Tokyo").localize(search_start_datetimes).astimezone(
        pytz.timezone("UTC")).replace(tzinfo=None)
    search_end_datetimes = datetime.strptime(end_time, "%Y-%m-%d_%H:%M:%S")
    search_end_datetime = pytz.timezone("Asia/Tokyo").localize(search_end_datetimes).astimezone(
        pytz.timezone("UTC")).replace(tzinfo=None)
    return search_end_datetime, search_start_datetime


'''ログイン画面'''


@attendance_manage.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["loginname"] == "mlab" and request.form["password"] == "password":
            cook['logged_in'] = True
            return show_entries()
        else:
            flash("ログイン名、パスワードを正しく入力してください")
    return render_template("login.html")


'''編集画面遷移'''


@attendance_manage.route("/edit/<int:id>", methods=['GET'])
def edit(id):
    session = Session()
    edit_record = session.query(WorkTime).filter(WorkTime.id == id).all()
    edit_context = data_send_html(edit_record)

    return render_template("edit.html", context=edit_context)


'''編集操作'''


@attendance_manage.route("/edit/<int:id>/update", methods=["POST"])
def edit_update(id):
    session = Session()
    edit_attendance = request.form["attendance_time"]
    edit_finish = request.form["finish_time"]
    attendance_timezone_utc, finish_timezone_utc = caluc_work_data(edit_attendance, edit_finish)
    edit_data = session.query(WorkTime).filter(WorkTime.id == id).first()
    edit_data.username = request.form["edit_name"]
    edit_data.attendance_time = attendance_timezone_utc
    edit_data.finish_time = finish_timezone_utc
    session.commit()
    session.close()

    return show_entries()


'''就業時間、残業時間、合計労働時間の計算'''


def caluc_work_data(edit_attendance, edit_finish):
    try:
        attendance_timezone_utc = caluc_edit_time(edit_attendance)
        finish_timezone_utc = caluc_edit_time(edit_finish)
    except:
        attendance_timezone_utc = None
        finish_timezone_utc = None

    return attendance_timezone_utc, finish_timezone_utc


'''編集する出退勤時間の計算'''


def caluc_edit_time(edit_time):
    try:
        edit_datetime = datetime.strptime(edit_time, '%Y-%m-%d_%H:%M')
    except:
        edit_datetime = datetime.strptime(edit_time, '%Y-%m-%d_%H:%M:%S')
    timezone_utc = pytz.timezone("Asia/Tokyo").localize(edit_datetime).astimezone(timezone('UTC'))

    return timezone_utc
