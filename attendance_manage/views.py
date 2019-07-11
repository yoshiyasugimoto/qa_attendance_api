from flask import Blueprint
from datetime import datetime, timedelta, time

from flask import session as cook
import pytz
from pytz import timezone
from flask import render_template, flash
from sqlalchemy import create_engine, Column, String, Integer, MetaData, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import request
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

    id_list = []
    work_time_username_list = []
    attendance_time_string_list = []
    working_time_list = []
    overworking_time_list = []
    total_working_time_list = []
    finish_time_string_list = []

    for row in all_record:
        id_list.append(row.id)
        work_time_username_list.append(row.username)
        try:
            attendance_time_string_list.append(calcu_jst_time(row.attendance_time).strftime('%Y-%m-%d_%H:%M%z'))
            finish_time_string_list.append(calcu_jst_time(row.finish_time).strftime('%Y-%m-%d_%H:%M%z'))
            total_time = row.finish_time - row.attendance_time
            if total_time >= timedelta(hours=REST_TIME + MAX_WORKING_TIME):
                working_time_list.append(time(hour=MAX_WORKING_TIME))
                overworking_time_list.append(total_time - timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                total_working_time_list.append(total_time - timedelta(hours=REST_TIME))
            elif timedelta(hours=WORKING_TIME) <= total_time < timedelta(
                    hours=REST_TIME + WORKING_TIME):
                working_time_list.append(timedelta(hours=WORKING_TIME))
                total_working_time_list.append(timedelta(hours=WORKING_TIME))
                overworking_time_list.append("残業なし")
            else:
                working_time_list.append(total_time)
                total_working_time_list.append(total_time)
                overworking_time_list.append("残業なし")
        except:
            finish_time_string_list.append("打刻されていません")
            working_time_list.append("打刻されていません")
            overworking_time_list.append("打刻されていません")
            total_working_time_list.append("打刻されていません")

    return render_template("show_entry.html", data=zip(id_list, work_time_username_list,
                                                       attendance_time_string_list,
                                                       finish_time_string_list,
                                                       working_time_list,
                                                       overworking_time_list,
                                                       total_working_time_list))


'''退勤、残業総労働時間の生成'''


def work_time_data(attendance_time, finish_time):
    working_time = []
    overworking_time = []
    total_working_time = []
    finish_time_string = []
    for att, fin in zip(attendance_time, finish_time):
        try:
            finish_timezone_jst = calcu_jst_time(fin)
            finish_time_string.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M%z'))
            total_time = fin - att
            if total_time >= timedelta(hours=REST_TIME + MAX_WORKING_TIME):
                working_time.append(time(hour=MAX_WORKING_TIME))
                overworking_time.append(total_time - timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                total_working_time.append(total_time - timedelta(hours=REST_TIME))
            elif timedelta(hours=WORKING_TIME) <= total_time < timedelta(
                    hours=REST_TIME + WORKING_TIME):
                working_time.append(timedelta(hours=WORKING_TIME))
                total_working_time.append(timedelta(hours=WORKING_TIME))
                overworking_time.append("残業なし")
            else:
                working_time.append(total_time)
                total_working_time.append(total_time)
                overworking_time.append("残業なし")
        except:
            finish_time_string.append("打刻されていません")
            working_time.append("打刻されていません")
            overworking_time.append("打刻されていません")
            total_working_time.append("打刻されていません")
    return finish_time_string, overworking_time, total_working_time, working_time


'''出退勤時間を整形する'''


def calcu_jst_time(_time):
    return pytz.timezone("UTC").localize(_time).astimezone(pytz.timezone("Asia/Tokyo")).replace(tzinfo=None)


'''出勤時間の整形'''


def caluc_attendance_time(attendance_time):
    attendance_string_list = []

    for att in attendance_time:
        try:
            attendance_timezone_jst = calcu_jst_time(att)

            attendance_string_list.append(attendance_timezone_jst.strftime("%Y-%m-%d_%H:%M%z"))
        except:
            attendance_string_list.append("打刻されていません")
    return attendance_string_list


'''検索機能'''


@attendance_manage.route("/filter", methods=['GET', 'POST'])
def filter():
    if request.method == "POST":
        sum_total_working_time = 0
        session = Session()
        username = request.form["username"]
        start_time = request.form["search_start"]
        end_time = request.form["search_end"]
        filtered_username_list, filtered_attendance_list, filtered_finish_list, filtered_id_list = filtered_username(
            username, session)

        try:
            search_end_datetime, search_start_datetime = calcu_search_time(start_time, end_time)

            '''名前$時間検索'''
            if filtered_username_list:
                if not filtered_username_list:
                    flash("検索条件に当てはまるデータがありません")
                    return render_template("confirm.html")

                filtered_id_list, filtered_username_list, search_attendance_string_list, search_finish_string_list, \
                working_time_list, overworking_time_list, total_working_time_list = filtered_username_time(
                    search_start_datetime, search_end_datetime, username, session)

                '''時間のみ検索'''
            elif username == '':

                filtered_id_list, filtered_username_list, overworking_time_list, search_attendance_string_list, \
                search_finish_string_list, total_working_time_list, working_time_list = filtered_time(
                    search_end_datetime, search_start_datetime, session)

            return render_template("result.html",
                                   data=zip(filtered_id_list, filtered_username_list, search_attendance_string_list,
                                            search_finish_string_list, working_time_list, overworking_time_list,
                                            total_working_time_list), sum_total_working_time=sum_total_working_time)
            '''名前のみ検索'''
        except:
            if username:
                return render_template("result.html",
                                       data=zip(filtered_id_list, filtered_username_list, search_attendance_string_list,
                                                search_finish_string_list, working_time_list, overworking_time_list,
                                                total_working_time_list))

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


def filtered_username(username, session):
    filtered_username_record = session.query(WorkTime).filter(WorkTime.username == username).order_by(
        desc(WorkTime.id)).all()
    filtered_username_list = []
    filtered_attendance_list = []
    filtered_finish_list = []
    filtered_id_list = []
    for row in filtered_username_record:
        filtered_username_list.append(row.username)
        filtered_attendance_list.append(row.attendance_time)
        filtered_finish_list.append(row.finish_time)
        filtered_id_list.append(row.id)

    return filtered_username_list, filtered_attendance_list, filtered_finish_list, filtered_id_list


'''名前&z時間検索'''


def filtered_username_time(search_start_datetime, search_end_datetime, username, session):
    filtered_username_time_record = session.query(WorkTime).order_by(desc(WorkTime.id)).filter(
        WorkTime.attendance_time.between(search_start_datetime, search_end_datetime)).filter(
        WorkTime.username == username).all()

    filtered_id_list = []
    filtered_username_list = []
    filtered_attendance_list = []
    filtered_finish_list = []
    for row in filtered_username_time_record:
        filtered_id_list.append(row.id)
        filtered_username_list.append(row.username)
        filtered_attendance_list.append(row.attendance_time)
        filtered_finish_list.append(row.finish_time)

    search_attendance_string_list = caluc_attendance_time(filtered_attendance_list)
    search_finish_string_list, overworking_time_list, total_working_time_list, working_time_list = work_time_data(
        filtered_attendance_list, filtered_finish_list)

    sum_total_working_time = timedelta(0, 0)
    for i in total_working_time_list:
        try:
            sum_total_working_time += i
        except:
            pass
    session.close()
    return filtered_id_list, filtered_username_list, search_attendance_string_list, search_finish_string_list, \
           working_time_list, overworking_time_list, total_working_time_list


'''時間検索'''


def filtered_time(search_end_datetime, search_start_datetime, session):
    filtered_time_record = session.query(WorkTime).order_by(desc(WorkTime.id)).filter(
        WorkTime.attendance_time.between(
            search_start_datetime, search_end_datetime)).all()
    filtered_username_list = []
    filtered_attendance_list = []
    filtered_finish_list = []
    filtered_id_list = []
    for row in filtered_time_record:
        filtered_username_list.append(row.username)
        filtered_attendance_list.append(row.attendance_time)
        filtered_finish_list.append(row.finish_time)
        filtered_id_list.append(row.id)
    search_attendance_string_list = caluc_attendance_time(filtered_attendance_list)
    search_finish_string_list, overworking_time_list, total_working_time_list, working_time_list = work_time_data(
        filtered_attendance_list, filtered_finish_list)
    session.close()
    return filtered_id_list, filtered_username_list, overworking_time_list, search_attendance_string_list, \
           search_finish_string_list, total_working_time_list, working_time_list


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


'''編集画面'''


@attendance_manage.route("/edit/<int:id>", methods=['GET'])
def edit(id):
    session = Session()
    edit_attendance_list, edit_finish_list, edit_id_list, edit_username_list = edit_setup(id, session)

    edit_attendance_string_list = caluc_attendance_time(edit_attendance_list)

    edit_finish_string_list = []
    for fin in edit_finish_list:
        try:
            finish_timezone_jst = calcu_jst_time(fin)
            edit_finish_string_list.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M%z'))
        except:
            edit_finish_string_list.append("打刻されていません")

    return render_template("edit.html", ids=edit_id_list[0],
                           edit_username=edit_username_list,
                           attendance_time_string=edit_attendance_string_list,
                           finish_time_string=edit_finish_string_list, )


def edit_setup(id, session):
    edit_record = session.query(WorkTime).filter(WorkTime.id == id).all()
    edit_id_list = []
    edit_username_list = []
    edit_attendance_list = []
    edit_finish_list = []
    for row in edit_record:
        edit_id_list.append(row.id)
        edit_username_list.append(row.username)
        edit_attendance_list.append(row.attendance_time)
        edit_finish_list.append(row.finish_time)

    return edit_attendance_list, edit_finish_list, edit_id_list, edit_username_list


'''編集操作'''


@attendance_manage.route("/edit/<int:id>/update", methods=["POST"])
def edit_update(id):
    session = Session()
    edit_attendance = request.form["attendance_time"]
    edit_finish = request.form["finish_time"]
    attendance_timezone_utc, edit_attendance_datetime_string, edit_finish_datetime_string, finish_timezone_utc, \
    overworking_time, total_working_time, working_time = caluc_work_data(edit_attendance, edit_finish)
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
        attendance_timezone_utc, edit_attendance_datetime, edit_attendance_datetime_string = caluc_edit_time(
            edit_attendance)
        finish_timezone_utc, edit_finish_datetime, edit_finish_datetime_string = caluc_edit_time(edit_finish)
        time_difference = edit_finish_datetime - edit_attendance_datetime

        if time_difference >= timedelta(hours=REST_TIME + WORKING_TIME):
            working_time = timedelta(hours=MAX_WORKING_TIME)
            overworking_time = time_difference - timedelta(hours=MAX_WORKING_TIME + REST_TIME)
            total_working_time = time_difference - timedelta(hours=REST_TIME)

        elif timedelta(hours=WORKING_TIME) <= time_difference < timedelta(
                hours=REST_TIME + WORKING_TIME):
            working_time = timedelta(hours=WORKING_TIME)
            total_working_time = timedelta(hours=WORKING_TIME)
            overworking_time = "残業なし"
        else:
            working_time = time_difference
            total_working_time = time_difference
            overworking_time = "残業なし"
    except:
        attendance_timezone_utc = None
        finish_timezone_utc = None
        edit_attendance_datetime_string = "出勤されていません"
        edit_finish_datetime_string = "打刻されていません"
        working_time = "打刻されていません"
        overworking_time = "打刻されていません"
        total_working_time = "打刻されていません"

    return attendance_timezone_utc, edit_attendance_datetime_string, edit_finish_datetime_string, finish_timezone_utc, \
           overworking_time, total_working_time, working_time


'''編集する出退勤時間の計算'''


def caluc_edit_time(edit_time):
    try:
        edit_datetime = datetime.strptime(edit_time, '%Y-%m-%d_%H:%M')
    except:
        edit_datetime = datetime.strptime(edit_time, '%Y-%m-%d_%H:%M:%S')
    timezone_utc = pytz.timezone("Asia/Tokyo").localize(edit_datetime).astimezone(
        timezone('UTC'))
    edit_time_string = edit_datetime.strftime("%Y-%m-%d_%H:%M")

    return timezone_utc, edit_datetime, edit_time_string
