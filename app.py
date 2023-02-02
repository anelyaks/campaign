from flask import Flask, render_template, url_for, request, redirect, jsonify
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from jproperties import Properties
from werkzeug.utils import secure_filename
import os
import requests
import time
import dateparser

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cmanager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = set(['txt', 'csv'])
ls = []


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def conf():
    configs = Properties()
    with open('app-config.properties', 'rb') as config_file:
        configs.load(config_file)
    items_view = configs.items()
    dictX = {}
    for item in items_view:
        dictX[item[0]] = item[1].data
    return dictX


class Numbers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    status = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'),
                            nullable=False)


class IncorrectNumbers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'),
                            nullable=False)


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    appName = db.Column(db.String(100), nullable=False)
    license = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now())
    status = db.Column(db.Integer, default=0)
    attempts = db.Column(db.Integer, default=0)
    numbers = db.relationship('Numbers', backref='campaign')
    incorrectNumbers = db.relationship('IncorrectNumbers', backref='campaign')
    startTime = db.Column(db.String(100), default='null')

    def __repr__(self):
        return '<Campaign %r>' % self.id


@app.route("/")
@app.route("/campaign")
def index():
    campaign = Campaign.query.order_by(Campaign.date).all()
    return render_template("index.html", Campaigns=campaign, len=len(campaign))


@app.route("/<int:id>", methods=['POST', 'GET'])
def detail(id):
    campaign = Campaign.query.get(id)
    numbers = Numbers.query.filter_by(campaign_id=id).all()
    incorrectNumbers = IncorrectNumbers.query.filter_by(campaign_id=id).all()
    print(campaign.startTime)
    if request.method == 'POST':
        startTime = request.form['startTime']
        campaign.startTime = startTime
        print(startTime)
        db.session.commit()
    # if campaign.startTime
    if campaign.startTime != 'null':
        print(dateparser.parse(campaign.startTime))
        minutes_diff = (datetime.now() - dateparser.parse(campaign.startTime)).total_seconds()
        if minutes_diff > 1:
            campaign.startTime = 'null'
            db.session.commit()
    return render_template("detail.html", campaign=campaign, numbers=numbers, notCorrect=incorrectNumbers)


@app.route("/create", methods=['POST', 'GET'])
def create():
    print(request.endpoint)
    if request.method == 'POST':
        name = request.form['name']
        appName = request.form['appName']
        print(appName)
        license = request.form['license']
        campaign = Campaign(name=name, appName=appName, license=license)
        try:
            db.session.add(campaign)
            db.session.flush()
            db.session.refresh(campaign)
            id = campaign.id
            db.session.commit()
            return redirect(url_for('upload_file', id=id))
        except:
            return "При создании кампании произошла ошибка"

    else:
        dictX = conf()
        print(dictX)
        return render_template("create.html", names=dictX)


@app.route("/<int:id>/upload_file", methods=['POST', 'GET'])
def upload_file(id):
    campaign = Campaign.query.get(id)
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)

        if file and allowed_file(file.filename):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            f = open(UPLOAD_FOLDER + "/" + filename, "r")
            Lines = f.readlines()
            nm = []
            for line in Lines:
                nm.append(line)
            nm, notCorrect = check_number(nm, id)
            for number in nm:
                number = number.replace("\n", "")
                print(number)
                numbers = Numbers(number=number, campaign_id=id)
                db.session.add(numbers)
                db.session.commit()
            for inc in notCorrect:
                incorrectNumbers = IncorrectNumbers(number=inc, campaign_id=id)
                db.session.add(incorrectNumbers)
                db.session.commit()
            return redirect(url_for('detail', id=id))

        else:
            print('Invalid Upload only txt,csv')

    else:
        return render_template("upload_file.html", campaign=campaign)


@app.route("/<int:id>/edit", methods=['POST', 'GET'])
def edit(id):
    campaign = Campaign.query.get(id)
    numbers = Numbers.query.filter_by(campaign_id=id).all()
    if request.method == "POST":
        campaign.name = request.form['name']
        campaign.appName = request.form['appName']
        campaign.license = request.form['license']
        number = request.form['number']
        if len(number) != 0:
            numbers = Numbers(number=number, campaign_id=id)
            db.session.add(numbers)
        try:
            db.session.commit()
            return redirect(url_for('edit', id=id))

        except:
            return "При редактировании статьи произошла ошибка"

    else:
        dictX = conf()
        print(dictX)
        return render_template("edit.html", campaign=campaign, numbers=numbers, names=dictX)


@app.route("/<int:id>/delete")
def delete_campaign(id):
    campaign = Campaign.query.get_or_404(id)
    numbers = Numbers.query.filter_by(campaign_id=id).all()
    incorrectNumbers = IncorrectNumbers.query.filter_by(campaign_id=id).all()

    try:
        db.session.delete(campaign)
        for number in numbers:
            db.session.delete(number)
        for incorrectNumber in incorrectNumbers:
            db.session.delete(incorrectNumber)
        db.session.commit()
        return redirect('/')


    except:
        return "При удалении кампании произошла ошибка"

class User(db.model, UserMixin):
    id= db.Column
@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/<int:id>/<int:number>/delete_number")
def delete_number(id, number):
    print(number)
    numbers = Numbers.query.filter_by(campaign_id=id).all()
    try:
        for numbera in numbers:
            print(numbera.number)
            if numbera.number == number:
                db.session.delete(numbera)
            else:
                pass
        db.session.commit()
        return redirect(url_for('detail', id=id))


    except:
        return "При удалении кампании произошла ошибка"


def check_number(numbers, id):
    list_set = set(numbers)
    unique_list = (list(list_set))
    new_list = []
    notCorrect = []
    print(list_set)
    for number in unique_list:
        number = number.replace("\n", "")
        # convert the set to the list
        if 10 <= len(number) <= 12:
            numnum = number[-10:]
            if numnum[:3] in ["700", "708", "705", "771", "776", "777", "701", "702", "775", "778", "707", "747",
                              "706"]:
                finalNum = "8" + numnum
                new_list.append(finalNum)
            else:
                notCorrect.append(numnum)

        else:
            notCorrect.append(number)

    print(new_list)
    print("некорректные номера")
    print(len(notCorrect))
    return new_list, notCorrect


@app.route("/<int:id>/recall")
def recall(id):
    print("in recall")
    numbers = Numbers.query.filter_by(campaign_id=id).all()
    for number in numbers:
        number.status = 0
        db.session.commit()

    return redirect(url_for('ff', id=id))


@app.route("/<int:id>/startcampaign")
def ff(id):
    numbers = Numbers.query.filter_by(campaign_id=id).all()
    campaign = Campaign.query.get_or_404(id)
    campaign.attempts = campaign.attempts + 1
    db.session.commit()
    allNumbers = []
    allNumberscopy = []
    for number in numbers:
        print(number.status == 0)
        print(number.status == -1)
        if number.status == 0 or number.status == -1:
            allNumbers.append(str(number.number))
            print(number.number)
            number.attempts = number.attempts + 1
    print(allNumbers)
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    last = allNumbers[-1]
    allNumberscopy = allNumbers.copy()
    anotherCopy = allNumbers.copy()
    print(campaign.license)
    sametimecalls = campaign.license
    print(type(sametimecalls))
    print(sametimecalls)
    zvonokketkennomer = ''

    def proverka():
        for i in range(len(allNumberscopy)):
            if allNumberscopy[i] != '1':
                return False
        return True

    # возвращает количество одновременных звонков
    def proverka2():
        r2 = requests.get('http://10.0.1.23:8088/ari/channels?api_key=username:eca123')
        return len(r2.json())

    # если кто-то поднял трубу, то записываем его как поднял
    def proverka3():
        for i in range(20):
            r2 = requests.get('http://10.0.1.23:8088/ari/channels?api_key=username:eca123')
            if r2.json() != []:
                mainArray = r2.json()
                for j in range(len(mainArray)):
                    eachNumber = mainArray[j]
                    if eachNumber.get('state') == 'Up':
                        numOf = eachNumber.get('caller').get('number')
                        if numOf in allNumbers:
                            y = allNumbers.index(numOf)
                            allNumbers[y] = "1"
                        else:
                            continue
                    else:
                        continue
            else:
                continue

    # пока не на все номера пошёл звонок, выполняем:
    while proverka() == False:
        proverka3()
        # если больше одного звонка то идём дальше
        if proverka2() >= sametimecalls:
            proverka3()
            continue
        # если равно или меньше одного звонка, то
        else:
            proverka3()
            # находим номер на который не был отправлен звонок
            for i in range(len(allNumberscopy)):
                if allNumberscopy[i] != '1':
                    indexcopy = allNumberscopy.index(allNumberscopy[i])
                    zvonokketkennomer = allNumberscopy[indexcopy]
                    break
                    # отправляем запрос на звонок

            dictX = conf()
            print(dictX)

            # if campaign.appName in dictX:
            #     exten = dictX.values()

            ext = dictX[campaign.appName]
            print(campaign.appName, dictX[campaign.appName])

            json_data = {
                "api_key": "username:eca123",
                "endpoint": "SIP/%s@3441568" % (zvonokketkennomer),
                "extension": ext,
                "callerId": zvonokketkennomer,
                "context": "from-internal",
                "timeout": 30
            }
            r = requests.post('http://10.0.1.23:8088/ari/channels', json=json_data, headers=headers,
                              auth=("username", "eca123"))
            time.sleep(1)

            x = ''
            for i in range(len(allNumberscopy)):
                if allNumberscopy[i] != '1':
                    x = allNumberscopy[i]
                    break
            if x == last:
                time.sleep(5)
                proverka3()
                time.sleep(5)
                proverka3()
                time.sleep(5)
                proverka3()
                time.sleep(5)
                proverka3()
                time.sleep(5)
                proverka3()
                time.sleep(5)
                proverka3()

            # меняем данные в листе, то что звонок был отправлен
            allNumberscopy[indexcopy] = "1"

    print(allNumberscopy)

    for number in numbers:
        if number.status != 1:
            ind = anotherCopy.index(str(number.number))
            if allNumbers[ind] == '1':
                number.status = 1
                db.session.commit()
            else:
                number.status = -1
                db.session.commit()
        else:
            pass

    print(allNumbers)
    print(allNumberscopy)
    campaign = Campaign.query.get(id)
    return redirect(url_for('detail', id=id))


if __name__ == "__main__":
    app.run(debug=True)
