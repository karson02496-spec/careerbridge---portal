import os, uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import UniqueConstraint
from io import BytesIO

app=Flask(__name__)
app.config['SECRET_KEY']=os.environ.get('SECRET_KEY','dev-only-change-me')
db_url=os.environ.get('DATABASE_URL','sqlite:///portal.db')
if db_url.startswith('postgres://'): db_url=db_url.replace('postgres://','postgresql://',1)
app.config['SQLALCHEMY_DATABASE_URI']=db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['MAX_CONTENT_LENGTH']=5*1024*1024
app.config['SESSION_COOKIE_HTTPONLY']=True
app.config['SESSION_COOKIE_SAMESITE']='Lax'
app.config['SESSION_COOKIE_SECURE']=os.environ.get('RENDER')=='true'
db=SQLAlchemy(app)

class User(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 name=db.Column(db.String(120),nullable=False)
 email=db.Column(db.String(180),unique=True,nullable=False)
 password=db.Column(db.String(255),nullable=False)
 role=db.Column(db.String(20),nullable=False)
 company=db.Column(db.String(150),default='')
 approved=db.Column(db.Boolean,default=False)
 created=db.Column(db.DateTime,default=datetime.utcnow)

class Job(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 hr_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
 title=db.Column(db.String(150),nullable=False)
 department=db.Column(db.String(120),nullable=False)
 location=db.Column(db.String(140),nullable=False)
 salary=db.Column(db.String(90),nullable=False)
 type=db.Column(db.String(60),nullable=False)
 description=db.Column(db.Text,nullable=False)
 active=db.Column(db.Boolean,default=True)
 created=db.Column(db.DateTime,default=datetime.utcnow)
 hr=db.relationship('User')

class Application(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 job_id=db.Column(db.Integer,db.ForeignKey('job.id'),nullable=False)
 applicant_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
 status=db.Column(db.String(30),default='Pending')
 resume_name=db.Column(db.String(180),nullable=False)
 resume_data=db.Column(db.LargeBinary,nullable=False)
 interview_date=db.Column(db.String(30),default='')
 interview_time=db.Column(db.String(30),default='')
 interview_place=db.Column(db.String(220),default='')
 created=db.Column(db.DateTime,default=datetime.utcnow)
 job=db.relationship('Job')
 applicant=db.relationship('User')
 __table_args__=(UniqueConstraint('job_id','applicant_id',name='unique_job_application'),)

with app.app_context():
 db.create_all()
 admin_email=os.environ.get('ADMIN_EMAIL','admin@careerbridge.local').strip().lower()
 admin_pass=os.environ.get('ADMIN_PASSWORD')
 if admin_pass and not User.query.filter_by(email=admin_email).first():
  db.session.add(User(name='Administrator',email=admin_email,password=generate_password_hash(admin_pass),role='admin',approved=True)); db.session.commit()

@app.context_processor
def context():
 return {'me':db.session.get(User,session['uid']) if session.get('uid') else None,'year':datetime.now().year}

def login_required(role=None):
 def decorate(fn):
  @wraps(fn)
  def inner(*args,**kwargs):
   u=db.session.get(User,session.get('uid')) if session.get('uid') else None
   if not u: flash('Please log in first.','error'); return redirect(url_for('login'))
   if role and u.role!=role: abort(403)
   if u.role=='hr' and not u.approved: session.clear(); flash('Your HR account is awaiting admin approval.','error'); return redirect(url_for('login'))
   return fn(*args,**kwargs)
  return inner
 return decorate

def current(): return db.session.get(User,session['uid'])

@app.route('/')
def index():
 jobs=Job.query.filter_by(active=True).order_by(Job.created.desc()).limit(6).all()
 return render_template('index.html',jobs=jobs,job_count=Job.query.filter_by(active=True).count())

@app.route('/register',methods=['GET','POST'])
def register():
 if request.method=='POST':
  name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); password=request.form.get('password',''); role=request.form.get('role','applicant'); company=request.form.get('company','').strip()
  if role not in ('applicant','hr') or not name or not email or '@' not in email or len(password)<8 or (role=='hr' and not company): flash('Complete all fields. Password must be at least 8 characters.','error')
  elif User.query.filter_by(email=email).first(): flash('Email is already registered.','error')
  else:
   db.session.add(User(name=name,email=email,password=generate_password_hash(password),role=role,company=company if role=='hr' else '',approved=role=='applicant')); db.session.commit()
   flash('HR registration submitted for admin approval.' if role=='hr' else 'Account created! You can log in now.','success'); return redirect(url_for('login'))
 return render_template('register.html')

@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
  if not u or not check_password_hash(u.password,request.form.get('password','')): flash('Incorrect email or password.','error')
  elif u.role=='hr' and not u.approved: flash('Your HR account is waiting for admin approval.','error')
  else: session.clear(); session['uid']=u.id; return redirect(url_for('dashboard'))
 return render_template('login.html')

@app.route('/logout',methods=['POST'])
def logout(): session.clear(); flash('You have logged out.','success'); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required()
def dashboard():
 u=current()
 if u.role=='applicant': return render_template('applicant.html',apps=Application.query.filter_by(applicant_id=u.id).order_by(Application.created.desc()).all())
 if u.role=='hr': return render_template('hr.html',jobs=Job.query.filter_by(hr_id=u.id).order_by(Job.created.desc()).all(),apps=Application.query.join(Job).filter(Job.hr_id==u.id).order_by(Application.created.desc()).all())
 return render_template('admin.html',pending=User.query.filter_by(role='hr',approved=False).all(),users=User.query.order_by(User.created.desc()).all(),jobs=Job.query.order_by(Job.created.desc()).all(),apps=Application.query.order_by(Application.created.desc()).all())

@app.route('/jobs')
def jobs():
 q=request.args.get('q','').strip(); query=Job.query.filter_by(active=True)
 if q: query=query.filter(db.or_(Job.title.ilike('%'+q+'%'),Job.department.ilike('%'+q+'%'),Job.location.ilike('%'+q+'%')))
 return render_template('jobs.html',jobs=query.order_by(Job.created.desc()).all(),q=q)

@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
 job=db.get_or_404(Job,job_id)
 if not job.active and (not session.get('uid') or current().role not in ('admin',) and current().id!=job.hr_id): abort(404)
 applied=bool(session.get('uid') and Application.query.filter_by(job_id=job.id,applicant_id=session['uid']).first())
 return render_template('job.html',job=job,applied=applied)

@app.route('/jobs/<int:job_id>/apply',methods=['POST'])
@login_required('applicant')
def apply(job_id):
 job=db.get_or_404(Job,job_id)
 if not job.active: abort(404)
 if Application.query.filter_by(job_id=job.id,applicant_id=current().id).first(): flash('You already applied to this job.','error'); return redirect(url_for('job_detail',job_id=job.id))
 file=request.files.get('resume')
 if not file or not file.filename or '.' not in file.filename or file.filename.rsplit('.',1)[1].lower() not in ('pdf','doc','docx'): flash('Upload a PDF, DOC, or DOCX resume.','error'); return redirect(url_for('job_detail',job_id=job.id))
 data=file.read()
 if not data or len(data)>5*1024*1024: flash('Resume must be between 1 byte and 5 MB.','error'); return redirect(url_for('job_detail',job_id=job.id))
 name=secure_filename(file.filename)
 db.session.add(Application(job_id=job.id,applicant_id=current().id,resume_name=name,resume_data=data)); db.session.commit(); flash('Application submitted successfully!','success'); return redirect(url_for('dashboard'))

@app.route('/hr/jobs/new',methods=['GET','POST'])
@login_required('hr')
def new_job():
 if request.method=='POST':
  fields={k:request.form.get(k,'').strip() for k in ('title','department','location','salary','type','description')}
  if not all(fields.values()): flash('Please fill in all fields.','error')
  else: db.session.add(Job(hr_id=current().id,**fields)); db.session.commit(); flash('Job published!','success'); return redirect(url_for('dashboard'))
 return render_template('new_job.html')

@app.route('/hr/jobs/<int:job_id>/toggle',methods=['POST'])
@login_required('hr')
def toggle_job(job_id):
 job=db.get_or_404(Job,job_id)
 if job.hr_id!=current().id: abort(403)
 job.active=not job.active; db.session.commit(); flash('Job status updated.','success'); return redirect(url_for('dashboard'))

@app.route('/applications/<int:app_id>/resume')
@login_required()
def resume(app_id):
 a=db.get_or_404(Application,app_id); u=current()
 if u.role!='admin' and u.id!=a.applicant_id and u.id!=a.job.hr_id: abort(403)
 return send_file(BytesIO(a.resume_data),download_name=a.resume_name,as_attachment=True,mimetype='application/octet-stream')

@app.route('/hr/applications/<int:app_id>/update',methods=['POST'])
@login_required('hr')
def update_application(app_id):
 a=db.get_or_404(Application,app_id)
 if a.job.hr_id!=current().id: abort(403)
 status=request.form.get('status','')
 if status not in ('Accepted','Rejected','Interview Scheduled'): abort(400)
 if status=='Interview Scheduled':
  date=request.form.get('interview_date','').strip(); time=request.form.get('interview_time','').strip(); place=request.form.get('interview_place','').strip()
  if not date or not time or not place: flash('Provide interview date, time, and place.','error'); return redirect(url_for('dashboard'))
  a.interview_date=date; a.interview_time=time; a.interview_place=place
 a.status=status; db.session.commit(); flash('Application updated.','success'); return redirect(url_for('dashboard'))

@app.route('/admin/hr/<int:user_id>/<action>',methods=['POST'])
@login_required('admin')
def approve_hr(user_id,action):
 u=db.get_or_404(User,user_id)
 if u.role!='hr' or action not in ('approve','reject'): abort(400)
 if action=='approve': u.approved=True
 else: db.session.delete(u)
 db.session.commit(); flash('HR request '+('approved.' if action=='approve' else 'rejected.'),'success'); return redirect(url_for('dashboard'))

@app.route('/admin/jobs/<int:job_id>/toggle',methods=['POST'])
@login_required('admin')
def admin_toggle(job_id):
 j=db.get_or_404(Job,job_id); j.active=not j.active; db.session.commit(); flash('Job status updated.','success'); return redirect(url_for('dashboard'))

@app.route('/health')
def health(): return {'status':'ok'}

if __name__=='__main__': app.run(debug=os.environ.get('FLASK_DEBUG')=='1',port=int(os.environ.get('PORT',5000)))
