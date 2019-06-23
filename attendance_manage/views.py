from flask import Blueprint, abort
from jinja2 import TemplateNotFound
import datetime
import os
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

engine = create_engine(PRODUCTION_ENGINE, poolclass=NullPool)

# engine = create_engine(LOCAL_ENGINE, poolclass=NullPool)
meta = MetaData(engine, reflect=True)
Base = declarative_base()
attendance_manage = Blueprint('attendance_manage', __name__,
                              template_folder='templates')

REST_TIME = 1
WORKING_TIME = 6
MAX_WORKING_TIME = 8


class WorkTime(Base):
    __tablename__ = 'work_time'
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
work_time_username = [name for name, in session.query(WorkTime.username)]
session.close()


@attendance_manage.route('/show_entry', methods=["GET"])
def show_entries():
    try:
        session = Session()
        id = [i for i, in session.query(WorkTime.id).order_by(desc(WorkTime.id)).all()]
        attendance_time = [time for time, in session.query(WorkTime.attendance_time).order_by(desc(WorkTime.id))]
        finish_time = [time for time, in session.query(WorkTime.finish_time).order_by(desc(WorkTime.id))]

        attendance_timezone_jst = []
        for att in attendance_time:
            time_difference = pytz.timezone("UTC").localize(att) - pytz.timezone("Asia/Tokyo").localize(att)
            attendance_timezone_jst.append((att + time_difference).replace(tzinfo=None))

        attendance_time_string = [i.strftime('%Y-%m-%d_%H:%M:%S%z') for i in attendance_timezone_jst]
        working_time = []
        overworking_time = []
        total_working_time = []
        finish_time_string = []
        for num, i in zip(finish_time, attendance_time):

            try:
                time_difference = (pytz.timezone("UTC").localize(num) - pytz.timezone("Asia/Tokyo").localize(num))
                finish_timezone_jst = (num + time_difference).replace(tzinfo=None)
                finish_time_string.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M:%S%z'))
                total_time = num - i
                if total_time >= datetime.timedelta(hours=REST_TIME + WORKING_TIME):
                    if total_time - datetime.timedelta(hours=REST_TIME) >= datetime.timedelta(hours=MAX_WORKING_TIME):
                        working_time.append(datetime.time(hour=MAX_WORKING_TIME, minute=0, second=0))
                        overworking_time.append(total_time - datetime.timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                        total_working_time.append(total_time - datetime.timedelta(hours=REST_TIME))

                elif datetime.timedelta(hours=WORKING_TIME) <= total_time < datetime.timedelta(
                        hours=REST_TIME + WORKING_TIME):
                    working_time.append(datetime.time(hour=WORKING_TIME, minute=0, second=0))
                    total_working_time.append(datetime.time(hour=WORKING_TIME, minute=0, second=0))
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

        return render_template("show_entry.html", data=zip(id, work_time_username,
                                                           attendance_time_string,
                                                           finish_time_string,
                                                           working_time,
                                                           overworking_time,
                                                           total_working_time))
    except TemplateNotFound:
        abort(404)


@attendance_manage.route("/filter", methods=['GET', 'POST'])
def filter():
    if request.method == "POST":

        session = Session()
        post_name = request.form["username"]
        search_start_date = request.form["search_start"]
        search_end_date = request.form["search_end"]
        attendance_times = [time for time, in
                            session.query(WorkTime.attendance_time).order_by(desc(WorkTime.id)).all()]
        try:
            search_start_date_datetimes = datetime.datetime.strptime(search_start_date, "%Y-%m-%d_%H:%M:%S")
            time_difference_start = (
                (pytz.timezone("Asia/Tokyo").localize(search_start_date_datetimes) - pytz.timezone("UTC").localize(
                    search_start_date_datetimes)))
            search_start_date_datetime = search_start_date_datetimes + time_difference_start

            search_end_date_datetimes = datetime.datetime.strptime(search_end_date, "%Y-%m-%d_%H:%M:%S")
            time_difference_end = (
                (pytz.timezone("Asia/Tokyo").localize(search_end_date_datetimes) - pytz.timezone("UTC").localize(
                    search_end_date_datetimes)))
            search_end_date_datetime = search_end_date_datetimes + time_difference_end
            for attendance_times_time in attendance_times:
                if not search_start_date_datetime <= attendance_times_time <= search_end_date_datetime:
                    continue
                elif search_start_date_datetime <= attendance_times_time <= search_end_date_datetime and post_name in work_time_username:

                    attendance_time_filtered_name = [time for time, in session.query(WorkTime.attendance_time).filter(
                        WorkTime.username == post_name).order_by(
                        desc(WorkTime.id)).all()]
                    seach_username = [time for time, in session.query(WorkTime.username).filter(
                        WorkTime.username == post_name).order_by(
                        desc(WorkTime.id)).all()]

                    attendance_timezone_jst = []
                    for att in attendance_time_filtered_name:
                        time_difference = (
                                pytz.timezone("UTC").localize(att) - pytz.timezone("Asia/Tokyo").localize(att))
                        attendance_timezone_jst.append((att + time_difference).replace(tzinfo=None))

                    search_attendance_time_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in attendance_timezone_jst]
                    finish_time_filtered_time = [time for time, in session.query(WorkTime.finish_time).filter(
                        WorkTime.username == post_name).order_by(
                        desc(WorkTime.id)).all()]
                    search_id = [i for i, in session.query(WorkTime.id).filter(
                        WorkTime.username == post_name).order_by(
                        desc(WorkTime.id)).all()]
                    working_time = []
                    overworking_time = []
                    total_working_time = []
                    search_finish_time_string = []
                    for num, i in zip(finish_time_filtered_time, attendance_time_filtered_name):

                        try:
                            time_difference = (
                                    pytz.timezone("UTC").localize(num) - pytz.timezone("Asia/Tokyo").localize(
                                num))
                            finish_timezone_jst = (num + time_difference).replace(tzinfo=None)
                            search_finish_time_string.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M:%S%z'))
                            total_time = num - i
                            if total_time >= datetime.timedelta(hours=REST_TIME + WORKING_TIME):
                                if total_time - datetime.timedelta(hours=REST_TIME) >= datetime.timedelta(
                                        hours=MAX_WORKING_TIME):
                                    working_time.append(datetime.timedelta(hours=MAX_WORKING_TIME))
                                    overworking_time.append(
                                        total_time - datetime.timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                                    total_working_time.append(total_time - datetime.timedelta(hours=REST_TIME))
                            elif datetime.timedelta(hours=WORKING_TIME) <= total_time < datetime.timedelta(
                                    hours=REST_TIME + WORKING_TIME):
                                working_time.append(datetime.timedelta(hours=WORKING_TIME))
                                total_working_time.append(datetime.timedelta(hours=WORKING_TIME))
                                overworking_time.append("残業なし")
                            else:
                                working_time.append(total_time)
                                total_working_time.append(total_time)
                                overworking_time.append("残業なし")
                        except:
                            search_finish_time_string.append("打刻されていません")
                            working_time.append("打刻されていません")
                            overworking_time.append("打刻されていません")
                            total_working_time.append("打刻されていません")

                    sum_total_working_time = datetime.timedelta(0, 0)
                    for i in total_working_time:
                        sum_total_working_time += i
                    session.close()

                    return render_template("result.html",
                                           data=zip(search_id, seach_username,
                                                    search_attendance_time_string, search_finish_time_string,
                                                    working_time,
                                                    overworking_time,
                                                    total_working_time,
                                                    ), sum_total_working_time=sum_total_working_time)

                elif post_name == '':
                    search_username = [name for name, in
                                          session.query(WorkTime.username).order_by(desc(WorkTime.id)).filter(
                                              WorkTime.attendance_time.between(search_start_date_datetime,
                                                                               search_end_date_datetime)).all()]
                    attendance_time_filtered_date = [time for time, in session.query(WorkTime.attendance_time).order_by(
                        desc(WorkTime.id)).filter(
                        WorkTime.attendance_time.between(search_start_date_datetime, search_end_date_datetime)).all()]

                    attendance_timezone_jst = []
                    for att in attendance_time_filtered_date:
                        time_difference = (
                                pytz.timezone("UTC").localize(att) - pytz.timezone("Asia/Tokyo").localize(att))
                        attendance_timezone_jst.append((att + time_difference).replace(tzinfo=None))

                    search_attendance_time_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in attendance_timezone_jst]

                    finish_time_filtered_date = [time for time, in session.query(WorkTime.finish_time).filter(
                        WorkTime.attendance_time.between(search_start_date_datetime,
                                                         search_end_date_datetime)).order_by(
                        desc(WorkTime.id)).all()]
                    search_id = [i for i, in session.query(WorkTime.id).order_by(desc(WorkTime.id)).filter(
                        WorkTime.attendance_time.between(search_start_date_datetime, search_end_date_datetime)).all()]
                    search_finish_time_string = []
                    working_time = []
                    overworking_time = []
                    total_working_time = []

                    for num, i in zip(finish_time_filtered_date, attendance_time_filtered_date):
                        try:
                            time_difference = (
                                    pytz.timezone("UTC").localize(num) - pytz.timezone("Asia/Tokyo").localize(num))
                            finish_timezone_jst = (num + time_difference).replace(tzinfo=None)
                            search_finish_time_string.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M:%S%z'))
                            total_time = num - i
                            if total_time >= datetime.timedelta(hours=REST_TIME + WORKING_TIME):
                                if total_time - datetime.timedelta(hours=REST_TIME) >= datetime.timedelta(
                                        hours=MAX_WORKING_TIME):
                                    working_time.append(datetime.timedelta(hours=MAX_WORKING_TIME))
                                    overworking_time.append(
                                        total_time - datetime.timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                                    total_working_time.append(total_time - datetime.timedelta(hours=REST_TIME))

                            elif datetime.timedelta(hours=WORKING_TIME) <= total_time < datetime.timedelta(
                                    hours=WORKING_TIME + REST_TIME):
                                working_time.append(datetime.timedelta(hours=WORKING_TIME))
                                total_working_time.append(datetime.timedelta(hours=WORKING_TIME))
                                overworking_time.append("残業なし")
                            else:
                                working_time.append(total_time)
                                total_working_time.append(total_time)
                                overworking_time.append("残業なし")

                        except AttributeError:
                            print(ValueError)
                            search_finish_time_string.append("打刻されていません")
                            working_time.append("打刻されていません")
                            overworking_time.append("打刻されていません")
                            total_working_time.append("打刻されていません")
                    session.close()

                    return render_template("result.html", data=zip(search_id, search_username,
                                                                   search_attendance_time_string, search_finish_time_string,
                                                                   working_time,
                                                                   overworking_time,
                                                                   total_working_time,))
            else:
                flash("検索条件に当てはまるデータがありません")
                return render_template("confirm.html")
        except:
            if post_name in work_time_username and search_start_date == '':
                search_attendance_time = [time for time, in session.query(WorkTime.attendance_time).filter(
                    WorkTime.username == post_name).order_by(
                    desc(WorkTime.id)).all()]
                search_username = [name for name, in session.query(WorkTime.username).filter(
                    WorkTime.username == post_name).order_by(
                    desc(WorkTime.id)).all()]

                attendance_timezone_jst = []
                for att in search_attendance_time:
                    time_difference = (pytz.timezone("UTC").localize(att) - pytz.timezone("Asia/Tokyo").localize(att))
                    attendance_timezone_jst.append((att + time_difference).replace(tzinfo=None))

                search_attendance_time_string = [i.strftime('%Y-%m-%d_%H:%M:%S') for i in attendance_timezone_jst]
                search_finish_time = [time for time, in session.query(WorkTime.finish_time).filter(
                    WorkTime.username == post_name).order_by(
                    desc(WorkTime.id)).all()]
                search_id = [i for i, in session.query(WorkTime.id).filter(
                    WorkTime.username == post_name).order_by(
                    desc(WorkTime.id)).all()]
                search_finish_time_string = []
                working_time = []
                overworking_time = []
                total_working_time = []

                for num, i in zip(search_finish_time, search_attendance_time):
                    try:
                        time_difference = (pytz.timezone("UTC").localize(num) - pytz.timezone("Asia/Tokyo").localize(
                            num))
                        finish_timezone_jst = (num + time_difference).replace(tzinfo=None)
                        search_finish_time_string.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M:%S%z'))
                        total_time = num - i
                        if total_time >= datetime.timedelta(hours=WORKING_TIME + REST_TIME):
                            if total_time - datetime.timedelta(hours=REST_TIME) >= datetime.timedelta(
                                    hours=MAX_WORKING_TIME):
                                working_time.append(datetime.timedelta(hours=MAX_WORKING_TIME))
                                overworking_time.append(
                                    total_time - datetime.timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                                total_working_time.append(total_time - datetime.timedelta(hours=REST_TIME))

                        elif datetime.timedelta(hours=WORKING_TIME) <= total_time < datetime.timedelta(
                                hours=WORKING_TIME + REST_TIME):
                            working_time.append(datetime.timedelta(hours=WORKING_TIME))
                            total_working_time.append(datetime.timedelta(hours=WORKING_TIME))
                            overworking_time.append("残業なし")
                        else:
                            working_time.append(total_time)
                            total_working_time.append(total_time)
                            overworking_time.append("残業なし")

                    except AttributeError:
                        print(ValueError)
                        search_finish_time_string.append("打刻されていません")
                        working_time.append("打刻されていません")
                        overworking_time.append("打刻されていません")
                        total_working_time.append("打刻されていません")

                session.close()

                return render_template(os.path.join(attendance_manage.name, "result.html"),
                                       data=zip(search_id, search_username,
                                                search_attendance_time_string, search_finish_time_string,
                                                working_time,
                                                overworking_time,
                                                total_working_time,
                                                ))
            else:
                flash("検索条件に当てはまるデータがありません")
                return render_template("confirm.html")

    return render_template("confirm.html")


@attendance_manage.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["loginname"] == "mlab" and request.form["password"] == "password":
            cook['logged_in'] = True
            return show_entries()
        else:
            flash("ログイン名、パスワードを正しく入力してください")
    return render_template("login.html")


@attendance_manage.route("/edit/<int:id>", methods=['GET'])
def edit(id):
    session = Session()
    edit_id = [i for i, in session.query(WorkTime.id).filter(WorkTime.id == id).all()]
    edit_username = [name for name, in
                     session.query(WorkTime.username).order_by(desc(WorkTime.id)).filter(WorkTime.id == id).all()]
    edit_attendance_time = [time for time, in
                            session.query(WorkTime.edit_attendance_time).order_by(desc(WorkTime.id)).filter(
                                WorkTime.id == id)]
    edit_finish_time = [time for time, in
                        session.query(WorkTime.edit_finish_time).order_by(desc(WorkTime.id)).filter(WorkTime.id == id)]

    attendance_timezone_jst = []
    for att in edit_attendance_time:
        time_difference = (pytz.timezone("UTC").localize(att) - pytz.timezone("Asia/Tokyo").localize(att))
        attendance_timezone_jst.append((att + time_difference).replace(tzinfo=None))

    edit_attendance_time_string = [i.strftime('%Y-%m-%d_%H:%M') for i in attendance_timezone_jst]
    edit_finish_time_string = []
    for fin in edit_finish_time:
        try:
            time_difference = (pytz.timezone("UTC").localize(fin) - pytz.timezone("Asia/Tokyo").localize(
                fin))
            finish_timezone_jst = (fin + time_difference).replace(tzinfo=None)
            edit_finish_time_string.append(finish_timezone_jst.strftime('%Y-%m-%d_%H:%M%z'))
        except AttributeError:
            print(ValueError)
            edit_finish_time_string.append("打刻されていません")
    return render_template("edit.html", ids=edit_id[0],
                           edit_username=edit_username,
                           attendance_time_string=edit_attendance_time_string,
                           finish_time_string=edit_finish_time_string, )


@attendance_manage.route("/edit/<int:id>/update", methods=["POST"])
def edit_update(id):
    session = Session()
    edit_data = session.query(WorkTime).filter(WorkTime.id == id).first()
    edit_id = [i for i, in session.query(WorkTime.id).filter(WorkTime.id == id).all()]
    updated = request.form
    edit_attendance_time = updated["time_att_time"]
    edit_finish_time = updated["time_fin_time"]
    edit_attendance_datetime = datetime.datetime.strptime(edit_attendance_time, '%Y-%m-%d_%H:%M')
    edit_attendance_datetime_string = edit_attendance_datetime.strftime("%Y-%m-%d_%H:%M:%S")
    attendance_timezone_jst = pytz.timezone("Asia/Tokyo").localize(edit_attendance_datetime)
    attendance_timezone_utc = attendance_timezone_jst.astimezone(timezone('UTC'))
    edit_data.username = updated["username"]
    edit_data.attendance_time = attendance_timezone_utc
    session.commit()
    working_time = []
    overworking_time = []
    total_working_time = []

    try:
        edit_finish_datetime = datetime.datetime.strptime(edit_finish_time, '%Y-%m-%d_%H:%M')
        finish_timezone_jst = pytz.timezone("Asia/Tokyo").localize(edit_finish_datetime)
        finish_timezone_utc = finish_timezone_jst.astimezone(timezone('UTC'))
        edit_finish_datetime_string = edit_finish_datetime.strftime('%Y-%m-%d_%H:%M:%S')
        time_difference = edit_finish_datetime - edit_attendance_datetime
        if time_difference >= datetime.timedelta(hours=REST_TIME + WORKING_TIME):
            if time_difference - datetime.timedelta(hours=REST_TIME) >= datetime.timedelta(hours=MAX_WORKING_TIME):
                working_time.append(datetime.timedelta(hours=MAX_WORKING_TIME))
                overworking_time.append(time_difference - datetime.timedelta(hours=MAX_WORKING_TIME + REST_TIME))
                total_working_time.append(time_difference - datetime.timedelta(hours=REST_TIME))
        elif datetime.timedelta(hours=WORKING_TIME) <= time_difference < datetime.timedelta(
                hours=REST_TIME + WORKING_TIME):
            working_time.append(datetime.timedelta(hours=WORKING_TIME))
            total_working_time.append(datetime.timedelta(hours=WORKING_TIME))
            overworking_time.append("残業なし")
        else:
            working_time.append(time_difference)
            total_working_time.append(time_difference)
            overworking_time.append("残業なし")
    except:
        finish_timezone_utc = None
        edit_finish_datetime_string = "打刻されていません"
        working_time.append("打刻されていません")
        overworking_time.append("打刻されていません")
        total_working_time.append("打刻されていません")
    edit_data.finish_time = finish_timezone_utc
    edit_name = [updated["username"]]
    session.commit()
    session.close()

    return render_template("result.html", data=zip(edit_id, edit_name,
                                                   [edit_attendance_datetime_string],
                                                   [edit_finish_datetime_string],
                                                   working_time,
                                                   overworking_time,
                                                   total_working_time,
                                                   ))
