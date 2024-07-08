from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import timedelta, datetime
import os
import openai
import plotly
import plotly.graph_objs as go
import json
import qrcode
from io import BytesIO
from flask import send_file
import pytz
from selenium import webdriver
from PIL import Image
import base64

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

openai.api_key = "your-openai-key"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    phone = db.Column(db.String(20), unique=True)

    def __repr__(self):
        return f'<User {self.name}>'

class ExerciseData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    count = db.Column(db.Integer)
    exercise_type = db.Column(db.String(64))  
    left_forearm_innerbody = db.Column(db.Integer)
    left_forearm_outterbody = db.Column(db.Integer)
    right_forearm_innerbody = db.Column(db.Integer)
    right_forearm_outterbody = db.Column(db.Integer)
    left_knee_innerbody = db.Column(db.Integer)
    right_knee_innerbody = db.Column(db.Integer)
    diagnosis = db.Column(db.Text)
    exercise_time = db.Column(db.Integer)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    log_data = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('exercise_data', lazy=True))
    set = db.Column(db.Integer)
    weight = db.Column(db.Integer)

    def __repr__(self):
        return f'<ExerciseData User: {self.user_id}, Count: {self.count}>'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        session.permanent = True
        name = request.form['name']
        phone = request.form['phone']
        user = User.query.filter_by(name=name, phone=phone).first()
        
        if user is None:
            flash('회원 정보가 존재하지 않습니다. 회원가입을 해주세요.')
            return redirect(url_for('home'))

        session['name'] = user.name
        session['phone'] = user.phone
        session['user_id'] = user.id
        flash('불러오기 성공!')
        return redirect(url_for('select'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('name', None)
    session.pop('phone', None)
    session.pop('user_id', None)
    flash('로그아웃 되었습니다.')
    return redirect(url_for('home'))

@app.route('/select')
def select():
    if 'name' in session and 'phone' in session:
        name = session['name']
        return render_template('select.html', name=name)
    else:
        flash('로그인이 필요합니다.')
        return redirect(url_for('home'))
    
@app.route('/exercise', methods=['POST'])
def exercise():
    exercise = request.form['exercise']
    exercise_videos = {
        '덤벨 인클라인 프레스': 'db_inclinepress.mp4',
        '덤벨 숄더 프레스': 'shoulderpress.mp4',
        '오버 헤드 프레스': 'bb_standing_shoulderpress.mp4',
        '스탠딩 덤벨 숄더 프레스': 'std_db_shoulderpress.mp4',
        '인클라인 바벨 프레스': 'bb_inclinepress.mp4',
        '시티드 바벨 프레스': 'bb_seated_shoulderpress.mp4',
    }
    video_file = exercise_videos.get(exercise, 'shoulderpress.mp4')  

    return render_template('shoulderpress.html', exercise=exercise, video_file=video_file)

@app.route('/squat', methods=['POST'])
def exercise_lower():
    exercise = request.form['exercise']
    exercise_videos = {
        '백 스쿼트': 'squat.mp4',
        '고블릿 스쿼트': 'db_goblet_squat.mp4',
        '스미스 스쿼트': 'smith_squat.mp4',
        '프론트 스쿼트': 'bb_front_squat.mp4',
        '덤벨 스쿼트': 'db_squat.mp4',
        '스모 스쿼트': 'bb_sumo_squat.mp4',
    }
    video_file = exercise_videos.get(exercise, 'squat.mp4') 

    return render_template('squat.html', exercise=exercise, video_file=video_file)

@app.route('/rank')
def rank():
    # 모든 사용자의 운동 데이터를 가져오기
    users = User.query.all()
    user_data = []

    for user in users:
        exercise_data = ExerciseData.query.filter_by(user_id=user.id).all()
        total_count = sum(data.count or 0 for data in exercise_data)
        total_time = sum(data.exercise_time or 0 for data in exercise_data)
        total_sets = sum(data.set or 0 for data in exercise_data)
        total_weight = sum(data.weight or 0 for data in exercise_data)
        total_left_forearm_innerbody = sum(data.left_forearm_innerbody or 0 for data in exercise_data)
        total_left_forearm_outterbody = sum(data.left_forearm_outterbody or 0 for data in exercise_data)
        total_right_forearm_innerbody = sum(data.right_forearm_innerbody or 0 for data in exercise_data)
        total_right_forearm_outterbody = sum(data.right_forearm_outterbody or 0 for data in exercise_data)

        # 평가 점수 계산
        score = calculate_fitness_score({
            'left_forearm_innerbody': total_left_forearm_innerbody,
            'left_forearm_outterbody': total_left_forearm_outterbody,
            'right_forearm_innerbody': total_right_forearm_innerbody,
            'right_forearm_outterbody': total_right_forearm_outterbody,
            'count': total_count,
            'exercise_time': total_time,
            'weight': total_weight
        })

        user_data.append({
            'name': user.name,
            'total_count': total_count,
            'total_time': total_time,
            'total_sets': total_sets,
            'total_weight': total_weight,
            'score': score
        })

    # 점수 기준으로 내림차순 정렬
    user_data.sort(key=lambda x: x['score'], reverse=True)

    return render_template('rank.html', user_data=user_data, enumerate=enumerate)

def calculate_fitness_score(data):
    """
    주어진 운동 데이터를 기반으로 평가 점수를 계산합니다.
    
    Args:
        data (dict): 사용자 운동 데이터
            - left_forearm_innerbody (int): 왼쪽 전완근 내부 거리
            - left_forearm_outterbody (int): 왼쪽 전완근 외부 거리
            - right_forearm_innerbody (int): 오른쪽 전완근 내부 거리
            - right_forearm_outterbody (int): 오른쪽 전완근 외부 거리
            - count (int): 운동 횟수
            - exercise_time (int): 운동 시간 (밀리초)
            - weight (int): 사용한 무게 (kg)
    
    Returns:
        float: 평가 점수
    """
    # 가중치 설정
    weight_forearm_innerbody = 0.2
    weight_forearm_outterbody = 0.2
    weight_count = 0.25
    weight_time_per_count = 0.15
    weight_weight = 0.2
    
    # 거리 점수 계산 (낮을수록 점수 높음)
    forearm_innerbody_score = 100 - (data['left_forearm_innerbody'] + data['right_forearm_innerbody']) * weight_forearm_innerbody
    forearm_outterbody_score = 100 - (data['left_forearm_outterbody'] + data['right_forearm_outterbody']) * weight_forearm_outterbody
    
    # 운동 횟수 점수 계산 (많을수록 점수 높음)
    count_score = data['count'] * weight_count
    
    # 운동 시간 당 횟수 점수 계산 (짧을수록 점수 높음)
    if data['count'] > 0:
        time_per_count_score = 100 - (data['exercise_time'] / data['count'] / 60000) * weight_time_per_count
    else:
        time_per_count_score = 0
    
    # 사용한 무게 점수 계산 (많을수록 점수 높음)
    weight_score = data['weight'] * weight_weight
    
    total_score = forearm_innerbody_score + forearm_outterbody_score + count_score + time_per_count_score + weight_score
    
    return total_score

# Flask route for rendering analysis page in app.py
@app.route('/anal')
def anal():
    if 'user_id' not in session:
        flash('로그인이 필요합니다.')
        return redirect(url_for('home'))

    user_id = session['user_id']
    name = session.get('name')
    latest_exercise_data = ExerciseData.query.filter_by(user_id=user_id).order_by(ExerciseData.date.desc()).first()

    if not latest_exercise_data or not latest_exercise_data.log_data:
        flash('시각화할 데이터가 없습니다.')
        return redirect(url_for('home'))

    log_data = json.loads(latest_exercise_data.log_data)
    times = [entry['time'] for entry in log_data]
    left_distances = [entry['leftDistance'] for entry in log_data]
    right_distances = [entry['rightDistance'] for entry in log_data]
    imbalances = [entry['imbalance'] for entry in log_data]

    trace_left = go.Scatter(x=times, y=left_distances, mode='lines', name='Left Distance')
    trace_right = go.Scatter(x=times, y=right_distances, mode='lines', name='Right Distance')
    trace_imbalance = go.Scatter(x=times, y=imbalances, mode='lines', name='Imbalance')

    data = [trace_left, trace_right, trace_imbalance]

    kst = pytz.timezone('Asia/Seoul')
    kst_date = latest_exercise_data.date.replace(tzinfo=pytz.utc).astimezone(kst)

    layout = go.Layout(
        title=f'사용자 ID: {user_id}, Set: {latest_exercise_data.set}, 시간: {kst_date.strftime("%Y년 %m월 %d일 %H:%M")}',
        xaxis=dict(title='Time (ms)')
    )

    fig = go.Figure(data=data, layout=layout)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    user_video_folder = os.path.join(basedir, 'static', 'videos', str(user_id))
    if os.path.exists(user_video_folder):
        video_files = [f for f in os.listdir(user_video_folder) if os.path.isfile(os.path.join(user_video_folder, f))]
        video_files.sort(key=lambda x: os.path.getmtime(os.path.join(user_video_folder, x)), reverse=True)
        video_files = video_files[:6]
    else:
        video_files = []
    short_diagnosis = session.get('short_diagnosis', '')
    exercise_images = {
        '덤벨 인클라인 프레스': 'images/dumbbell_press.png',
        '덤벨 숄더 프레스': 'images/shoulder_press.png',
        '오버 헤드 프레스': 'images/OHP.png',
        '스탠딩 덤벨 숄더 프레스': 'images/standingdumbellshoulderpress.png',
        '인클라인 바벨 프레스': 'images/inclinebenchpress.png',
        '시티드 바벨 프레스': 'images/sittedbarbellpress.png',
        '백 스쿼트': 'images/back_squat.png',
        '고블릿 스쿼트': 'images/gobletsquat.png',
        '스미스 스쿼트': 'images/smithsquat.png',
        '프론트 스쿼트': 'images/frontsquat.png',
        '덤벨 스쿼트': 'images/dumbellsquat.png',
        '스모 스쿼트': 'images/sumosquat.png',
    }
    exercise_image = exercise_images.get(latest_exercise_data.exercise_type, 'images/default.png')

    return render_template('anal.html',
                           name=name,
                           graphJSON=graphJSON,
                           latest_exercise_data=latest_exercise_data,
                           exercise_time=latest_exercise_data.exercise_time,
                           diagnosis=latest_exercise_data.diagnosis,
                           short_diagnosis=short_diagnosis,
                           video_files=video_files,
                           kst_date=kst_date,
                           weight=latest_exercise_data.weight,
                           exercise_image=exercise_image)  



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        if User.query.filter_by(name=name).first():
            flash('이미 등록된 이름입니다.')
            return redirect(url_for('signup'))
        if User.query.filter_by(phone=phone).first():
            flash('이미 등록된 전화번호입니다.')
            return redirect(url_for('signup'))

        user = User(name=name, phone=phone)
        db.session.add(user)
        db.session.commit()
        flash('회원가입 성공! 이제 로그인해주세요.')
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/squat')
def squat():
    exercise = request.args.get('exercise', '운동')
    return render_template('squat.html', exercise=exercise)

@app.route('/shoulderpress')
def shoulderpress():
    exercise = request.args.get('exercise', '운동')
    return render_template('shoulderpress.html', exercise=exercise)

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 400

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    if 'set' not in request.form:
        return jsonify({'error': 'No set number provided'}), 400

    video = request.files['video']
    user_id = session['user_id']
    set_number = request.form['set']
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    
    user_folder = os.path.join(basedir, 'static', 'videos', str(user_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    video_filename = f"{timestamp}_set{set_number}.mp4"
    video_path = os.path.join(user_folder, video_filename)
    video.save(video_path)

    return jsonify({'message': 'Video uploaded successfully'}), 200

def get_gpt_response(log_data, exercise_type):
    try:
        squat_exercises = [
            '백 스쿼트', '고블릿 스쿼트', '스미스 스쿼트',
            '프론트 스쿼트', '덤벨 스쿼트', '스모 스쿼트'
        ]
        
        press_exercises = [
            '덤벨 인클라인 프레스', '덤벨 숄더 프레스', '오버 헤드 프레스',
            '스탠딩 덤벨 숄더 프레스', '인클라인 바벨 프레스', '시티드 바벨 프레스'
        ]
        
        if exercise_type in squat_exercises:  # 스쿼트에 대한 진단 요청
            # 긴 버전 생성
            long_response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "너는 아주 친절하고 박학다식한 한국인 트레이너이자 운동처방사야."},
                    {"role": "user", "content": f"주어진 불균형 데이터는 스쿼트 진행시 좌우측 무릎 거리이고 한쪽이 다른 한 쪽에 대해서 불균형하게 벌어질 경우 불균형이라고 판단해. 주어진 데이터를 바탕으로 긴 진단 결과를 제공해줘.\n\n{log_data}"}
                ]
            )
            long_diagnosis = long_response.choices[0]['message']['content']

            # 짧은 버전 생성
            short_response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "너는 아주 친절하고 박학다식한 한국인 트레이너이자 운동처방사야."},
                    {"role": "user", "content": f"주어진 불균형 데이터는 스쿼트 진행시 좌우측 무릎 거리이고 한쪽이 다른 한 쪽에 대해서 불균형하게 벌어질 경우 불균형이라고 판단해. 주어진 데이터를 바탕으로 짧고 간결하게 불균형 진단을 설명해줘. 마지막 멘트는 '자세한 진단 결과를 보려면 QR 코드를 통해 분석 결과지를 다운받으세요!' 라고 해줘.\n\n{log_data}"}
                ]
            )
            short_diagnosis = short_response.choices[0]['message']['content']
        elif exercise_type in press_exercises:  # 숄더 프레스에 대한 진단 요청
            # 긴 버전 생성
            long_response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "너는 아주 친절하고 박학다식한 한국인 트레이너이자 운동처방사야."},
                    {"role": "user", "content": f"주어진 불균형 데이터는 숄더프레스 진행시 좌우측 전완근 거리이고 한쪽이 다른 한 쪽에 대해서 불균형하게 벌어질 경우 불균형이라고 판단해. 총 불균형 중 우측 혹은 좌측 중 더 불균형이 자주 일어나는 부분에 대해 알려줘. 그리고 그러한 불균형이 왜 일어나는지 운동 역학적, 기능 해부학적(어떤 근육인지 해부학적용어를 활용해 설명)으로 설명해줘. 그 다음에 앞으로 이렇게 계속 불균형이 발생할 경우 어떤 결과를 초래하게 될 것이라고 이야기 해줘. 마지막으로는 이러한 불균형을 개선하기 위해서는 어떠한 스트레칭이 필요한지 구체적으로 운동 종목을 알려주거나 어떤 운동을 해서 개선할 수 있는지 아주 자세하게 설명해줘. 말투는 친절하고 상냥하게 해줘. 그리고 시작은 회원님 운동 진단해드리겠습니다~ 이렇게 트레이너처럼 말해주면 좋을 것 같아. 주의: 진단은 일회성으로 끝날것이므로 혹시 더 궁금한 점이 있으시면 언제든지 물어봐 주세요 와 같은 말은 안들어가야함. 그리고 좀 간결하게 작성해줘. 내용은 다 담기되 양은 적게.\n\n{log_data}"}
                ]
            )
            long_diagnosis = long_response.choices[0]['message']['content']

            # 짧은 버전 생성
            short_response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "너는 아주 친절하고 박학다식한 한국인 트레이너이자 운동처방사야."},
                    {"role": "user", "content": f"주어진 불균형 데이터는 숄더프레스 진행시 좌우측 전완근 거리이고 한쪽이 다른 한 쪽에 대해서 불균형하게 벌어질 경우 불균형이라고 판단해. 주어진 데이터를 바탕으로 짧고 간결하게 불균형 진단을 설명해줘. 마지막 멘트는 '자세한 진단 결과를 보려면 QR 코드를 통해 분석 결과지를 다운받으세요!' 라고 해줘.\n\n{log_data}"}
                ]
            )
            short_diagnosis = short_response.choices[0]['message']['content']
        else:
            return "운동 유형이 올바르지 않습니다.", "운동 유형이 올바르지 않습니다."

        formatted_long_diagnosis = long_diagnosis.replace("\n", "<br>")
        formatted_short_diagnosis = short_diagnosis.replace("\n", "<br>")
        
        print(f"GPT-4o long response: {formatted_long_diagnosis}")
        print(f"GPT-4o short response: {formatted_short_diagnosis}")

        return formatted_long_diagnosis, formatted_short_diagnosis
    except Exception as e:
        error_message = f"진단 중 오류 발생: {str(e)}"
        print(error_message)
        return error_message.replace("\n", "<br>").replace("**", "<b>").replace("**", "</b>").replace("###", "<h3>").replace("</h3><br>", "</h3>"), error_message.replace("\n", "<br>").replace("**", "<b>").replace("**", "</b>").replace("###", "<h3>").replace("</h3><br>", "</h3>")


@app.route('/save_exercise_data', methods=['POST'])
def save_exercise_data():
    if 'user_id' not in session:
        return jsonify({'error': 'User not logged in'}), 400
    
    data = request.json
    user_id = session['user_id']
    print("Received data:", data)
    
    count = data.get('count')
    set_num = data.get('set')  
    weight = data.get('weight')  
    exercise_type = data.get('exercise_type')
    exercise_time = data.get('exercise_time')
    log_data = json.dumps(data.get('logData', []))  # 로그 데이터를 JSON 문자열로 변환
    
    squat_exercises = [
        '백 스쿼트', '고블릿 스쿼트', '스미스 스쿼트',
        '프론트 스쿼트', '덤벨 스쿼트', '스모 스쿼트'
    ]
    
    if exercise_type in squat_exercises:
        left_knee_innerbody = data.get('left_knee_innerbody')
        right_knee_innerbody = data.get('right_knee_innerbody')
        left_forearm_innerbody = None
        left_forearm_outterbody = None
        right_forearm_innerbody = None
        right_forearm_outterbody = None
        log_data_str = f"Count: {count}, Left Knee Inner Body: {left_knee_innerbody}, Right Knee Inner Body: {right_knee_innerbody}"
    else:
        left_forearm_innerbody = data.get('left_forearm_innerbody')
        left_forearm_outterbody = data.get('left_forearm_outterbody')
        right_forearm_innerbody = data.get('right_forearm_innerbody')
        right_forearm_outterbody = data.get('right_forearm_outterbody')
        left_knee_innerbody = None
        right_knee_innerbody = None
        log_data_str = f"Count: {count}, Left Forearm Inner Body: {left_forearm_innerbody}, Left Forearm Outer Body: {left_forearm_outterbody}, Right Forearm Inner Body: {right_forearm_innerbody}, Right Forearm Outer Body: {right_forearm_outterbody}"
        
    long_diagnosis, short_diagnosis = get_gpt_response(log_data_str, exercise_type)  # 운동 유형 전달
    
    print("Parsed data:", count, left_forearm_innerbody, left_forearm_outterbody, right_forearm_innerbody, right_forearm_outterbody, left_knee_innerbody, right_knee_innerbody)
    print("GPT Long Diagnosis:", long_diagnosis)
    print("GPT Short Diagnosis:", short_diagnosis)

    exercise_data = ExerciseData(
        user_id=user_id,
        count=count,
        set=set_num,  
        weight=weight, 
        exercise_type=exercise_type, 
        left_forearm_innerbody=left_forearm_innerbody,
        left_forearm_outterbody=left_forearm_outterbody,
        right_forearm_innerbody=right_forearm_innerbody,
        right_forearm_outterbody=right_forearm_outterbody,
        left_knee_innerbody=left_knee_innerbody,
        right_knee_innerbody=right_knee_innerbody,
        diagnosis=long_diagnosis,  
        exercise_time=exercise_time,
        log_data=log_data,  # 추가된 로그 데이터 저장
        date=datetime.utcnow()
    )

    db.session.add(exercise_data)
    db.session.commit()
    session['short_diagnosis'] = short_diagnosis  # 세션에 짧은 진단 저장
    print("Data committed to database")
    return jsonify({'message': 'Exercise data and diagnosis saved successfully', 'exercise_data_id': exercise_data.id, 'short_diagnosis': short_diagnosis}), 200



    db.session.add(exercise_data)
    db.session.commit()
    session['short_diagnosis'] = short_diagnosis  # 세션에 짧은 진단 저장
    print("Data committed to database")
    return jsonify({'message': 'Exercise data and diagnosis saved successfully', 'exercise_data_id': exercise_data.id, 'short_diagnosis': short_diagnosis}), 200

def get_website_screenshot(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    driver_path = os.path.join(basedir, 'drivers', 'chromedriver')
    options.binary_location = driver_path
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    screenshot = driver.get_screenshot_as_png()
    driver.quit()
    return screenshot

@app.route('/generate_qr')
def generate_qr():
    url = request.url_root  
    screenshot = get_website_screenshot(url)

    screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(screenshot_base64)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
