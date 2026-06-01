import time, io, csv, random, json
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.secret_key = 'your_secure_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) 
    role = db.Column(db.String(10), default='student')
    is_first_login = db.Column(db.Boolean, default=True)
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default="General")
    password = db.Column(db.String(50), default="1234")
    questions = db.relationship('Question', backref='exam', lazy=True)
    is_public = db.Column(db.Boolean, default=True)
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    text = db.Column(db.String(500), nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
class ExamResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    exam_title = db.Column(db.String(200), nullable=False, default="General")
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    date_taken = db.Column(db.String(100), nullable=False)
#admin
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_admin_pw = generate_password_hash('21058452')
        admin_user = User(username='admin', password=hashed_admin_pw, role='admin', is_first_login=False)
        db.session.add(admin_user)
        db.session.commit()
#all route
@app.route('/')
def index():
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
       
        user = User.query.filter_by(username=username).first()
       
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            session['role'] = user.role
           
            if user.is_first_login:
                return redirect(url_for('change_password'))
           
            if user.role == 'admin':
                return redirect(url_for('admin_panel'))
            return redirect(url_for('dashboard'))
        else:
            flash("incorect password!")
           
    return render_template('login.html')
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('login'))
       
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
       
        if new_password != confirm_password:
            flash("password not mache!")
            return redirect(url_for('change_password'))
           
        user = User.query.filter_by(username=session['user']).first()
        if user:
            user.password = generate_password_hash(new_password)
            user.is_first_login = False
            db.session.commit()
            flash("password changed!")
            return redirect(url_for('dashboard'))
           
    return render_template('change_password.html')
# =========================================
# Dashboards
# ==========================================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login'))
    
    # filter_by
    all_exams = Exam.query.filter_by(is_public=True).all()
    return render_template('dashboard.html', user=session['user'], exams=all_exams)

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin': 
        return redirect(url_for('login'))
        
 
    search_query = request.args.get('search_query', '').strip()
    search_results = []
    
    if search_query:
        
        search_results = ExamResult.query.filter(
            (ExamResult.username.like(f"%{search_query}%")) | 
            (ExamResult.date_taken.like(f"%{search_query}%"))
        ).order_by(ExamResult.id.desc()).all()
        
    all_results = ExamResult.query.order_by(ExamResult.id.desc()).all()
    
    return render_template('admin.html', 
                           results=all_results, 
                           search_results=search_results,
                           search_query=search_query,
                           questions=Question.query.all(), 
                           all_users=User.query.all(),
                           exams=Exam.query.all())
@app.route('/profile')
def profile():
    if 'user' not in session: return redirect(url_for('login'))
    current_user = session['user']
    user_results = ExamResult.query.filter_by(username=current_user).order_by(ExamResult.id.desc()).all()
    return render_template('profile.html', user=current_user, results=user_results)

@app.route('/admin/add_single_student', methods=['POST'])
def add_single_student():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    uname = request.form.get('username')
    default_password = "1234"
    hashed_pw = generate_password_hash(default_password)
   
    if not User.query.filter_by(username=uname).first():
        db.session.add(User(username=uname, password=hashed_pw, role='student', is_first_login=True))
        db.session.commit()
        flash(f"ተማሪ '{uname}' በትክክል ተመዝግቧል! Default Password: {default_password}")
    else:
        flash("ይህ የተማሪ ስም አስቀድሞ ተወስዷል!")
    return redirect(url_for('admin_panel'))
@app.route('/admin/import_students', methods=['POST'])
def import_students():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    file = request.files.get('file')
   
    if not file or not file.filename.endswith('.csv'):
        flash("እባክዎ ትክክለኛ የ CSV ፋይል ይምረጡ!")
        return redirect(url_for('admin_panel'))
   
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    try: next(csv_input)
    except StopIteration: pass
   
    count = 0
    hashed_pw = generate_password_hash("1234")
    for row in csv_input:
        if len(row) < 1: continue
        uname = row[0].strip()
        if uname and not User.query.filter_by(username=uname).first():
            db.session.add(User(username=uname, password=hashed_pw, role='student', is_first_login=True))
            count += 1
    db.session.commit()
    flash(f"{count} ተማሪዎች ከ CSV ፋይል ላይ ተመዝግበዋል!")
    return redirect(url_for('admin_panel'))
@app.route('/admin/edit_student/<int:user_id>', methods=['POST'])
def edit_student(user_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    user = User.query.get(user_id)
    new_name = request.form.get('new_username')
    if user and new_name and user.role != 'admin':
        user.username = new_name
        db.session.commit()
        flash("የተማሪው ስም ተስተካክሏል!")
    return redirect(url_for('admin_panel'))
@app.route('/admin/delete_student/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user and user.role != 'admin':
        db.session.delete(user)
        db.session.commit()
        flash("ተማሪው በትክክል ተሰርዟል!")
    return redirect(url_for('admin_panel'))

@app.route('/add_exam', methods=['POST'])
def add_exam():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    # Public/Private
    status_input = request.form.get('is_public')
    is_pub = True if status_input == 'true' else False

    new_exam = Exam(
        title=request.form.get('title'),
        category=request.form.get('category'),
        password=request.form.get('password'),
        is_public=is_pub 
    )
    db.session.add(new_exam)
    db.session.commit()
    flash("አዲስ የፈተና ርዕስ በተሳካ ሁኔታ ተፈጥሯል!")
    return redirect(url_for('admin_panel'))
@app.route('/admin/toggle_exam_status/<int:exam_id>', methods=['POST'])
def toggle_exam_status(exam_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    exam = Exam.query.get(exam_id)
    if exam:
        exam.is_public = not exam.is_public 
        db.session.commit()
        status_text = "🌍 ለሁሉም ክፍት (Public)" if exam.is_public else "🔒 የተደበቀ (Private)"
        flash(f"የፈተናው '{exam.title}' ሁኔታ ወደ {status_text} ተቀይሯል!")
        
    return redirect(url_for('admin_panel'))
@app.route('/add_question', methods=['POST'])
def add_question():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    new_q = Question(
        exam_id=request.form.get('exam_id'),
        text=request.form.get('text'),
        option_a=request.form.get('a'),
        option_b=request.form.get('b'),
        option_c=request.form.get('c'),
        option_d=request.form.get('d'),
        correct_answer=request.form.get('correct')
    )
    db.session.add(new_q)
    db.session.commit()
    return redirect(url_for('admin_panel'))
@app.route('/course/<int:exam_id>')
def course_detail(exam_id):
    if 'user' not in session: return redirect(url_for('login'))
    exam = Exam.query.get_or_404(exam_id)
    return render_template('course.html', user=session['user'], exam=exam)
@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    exam_id = request.form.get('exam_id')
    exam = Exam.query.get(exam_id)
    input_pass = request.form.get('quiz_password')
    if exam and input_pass == exam.password:
        session['current_exam_id'] = exam_id
        session['answers'] = {}
        session['start_time'] = time.time()
       
        questions = Question.query.filter_by(exam_id=exam_id).all()
        if not questions:
            return "<h1>this question has not been prepared for this exam!</h1><a href='/dashboard'>back</a>"
        q_ids = [q.id for q in questions]
        random.shuffle(q_ids)
        session['shuffled_q_ids'] = q_ids
       
        return redirect(url_for('quiz', q_id=q_ids[0]))
    return "<h1>incorrect exam password!</h1><a href='/dashboard'>back</a>"
@app.route('/quiz/<int:q_id>', methods=['GET', 'POST'])
def quiz(q_id):
    if 'user' not in session: return redirect(url_for('login'))
   
    question = Question.query.get_or_404(q_id)
    shuffled_ids = session.get('shuffled_q_ids', [])
    answers = session.get('answers', {})
   
    if request.method == 'POST':
        ans = request.form.get('answer')
        answers[str(q_id)] = ans
        session['answers'] = answers
       
        try:
            current_index = shuffled_ids.index(q_id)
            next_index = current_index + 1
            if next_index < len(shuffled_ids):
                return redirect(url_for('quiz', q_id=shuffled_ids[next_index]))
            else:
                return redirect(url_for('summary'))
        except ValueError:
            return redirect(url_for('summary'))
   
    time_left = max(0, int(600 - (time.time() - session.get('start_time', time.time()))))
    return render_template('quiz.html', question=question, shuffled_ids=shuffled_ids, time_left=time_left, answered_ids=list(answers.keys()))

@app.route('/summary')
def summary():
    exam_id = session.get('current_exam_id')
    all_qs = Question.query.filter_by(exam_id=exam_id).all()
    answered_ids = [int(k) for k in session.get('answers', {}).keys()]
    return render_template('summary.html', all_questions=all_qs, answered_ids=answered_ids)
@app.route('/finish_quiz', methods=['POST'])
def finish_quiz():
    exam_id = session.get('current_exam_id')
    exam = Exam.query.get(exam_id)
    answers = session.get('answers', {})
   
    flagged_data = request.form.get('flagged_list', '[]')
    try: flagged_ids = json.loads(flagged_data)
    except: flagged_ids = []
   
    score = 0
    questions = Question.query.filter_by(exam_id=exam_id).all()
   
    for q in questions:
        if q.id in flagged_ids: continue
        if answers.get(str(q.id)) == q.correct_answer: score += 1
  
    new_result = ExamResult(
        username=session['user'],
        exam_title=exam.title,
        score=score,
        total=len(questions),
        date_taken=time.strftime("%Y-%m-%d %H:%M")
    )
    db.session.add(new_result)
    db.session.commit()
    return render_template('result.html', score=score, total=len(questions))
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    exam_id = request.form.get('exam_id')
    file = request.files['file']
   
    if not file or not file.filename.endswith('.csv'): return "<h1>please select CSV file</h1>"
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    next(csv_input)
    for row in csv_input:
        if len(row) < 6: continue
        new_q = Question(
            exam_id=exam_id, text=row[0], option_a=row[1], option_b=row[2], option_c=row[3], option_d=row[4], correct_answer=row[5].lower()
        )
        db.session.add(new_q)
    db.session.commit()
    return redirect(url_for('admin_panel'))
@app.route('/export_results')
def export_results():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student', 'Score', 'Total', 'Date'])
    for res in ExamResult.query.all():
        writer.writerow([res.username, res.score, res.total, res.date_taken])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=results.csv"})

@app.route('/admin/delete_exam/<int:exam_id>', methods=['POST'])
def delete_exam(exam_id):
    if session.get('role') != 'admin': 
        return redirect(url_for('login'))
        
    exam = Exam.query.get(exam_id)
    if exam:
        
        Question.query.filter_by(exam_id=exam_id).delete()
        
        deleted_title = exam.title
        db.session.delete(exam)
        db.session.commit()
        flash(f"ፈተናው '{deleted_title}' ከነጥያቄዎቹ ሙሉ በሙሉ ተሰርዟል!")
        
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete_all_results', methods=['POST'])
def delete_all_results():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    ExamResult.query.delete()
    db.session.commit()
    flash("ሁሉም የተማሪዎች ውጤት ሙሉ በሙሉ ተሰርዟል!")
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete_results_by_date', methods=['POST'])
def delete_results_by_date():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    del_date = request.form.get('delete_date')
    if del_date:
    
        count = ExamResult.query.filter(ExamResult.date_taken.like(f"%{del_date}%")).delete(synchronize_session='fetch')
        db.session.commit()
        flash(f"በቀን {del_date} የተመዘገቡ {count} የተማሪ ውጤቶች በተሳካ ሁኔታ ተሰርዘዋል!")
    else:
        flash("እባክህ መጀመሪያ ትክክለኛ ቀን ምረጥ!")
        
    return redirect(url_for('admin_panel'))
if __name__ == '__main__':
    app.run(debug=True)