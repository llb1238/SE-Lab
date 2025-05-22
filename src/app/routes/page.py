from flask import render_template, session, redirect, url_for
from app import app
from app.utils.auth import login_required, role_required

@app.route('/')
def index():
    if 'username' not in session:
        return render_template('login.html')
    return render_template('main.html')

@app.route('/main')
@login_required
def show_main():
    role = session.get('role', '')
    return render_template('main.html', role=role)

# 页面路由
@app.route('/courses')
@login_required
@role_required(['admin'])  # 只允许管理员访问课程管理
def show_courses():
    return render_template('courses.html')

@app.route('/students')
@login_required
@role_required(['admin'])  # 只允许管理员访问学生管理
def show_students():
    return render_template('students.html')

@app.route('/teachers')
@login_required
@role_required(['admin'])  # 只允许管理员访问教师管理
def show_teachers():
    return render_template('teachers.html')

@app.route('/progress')
@login_required
@role_required(['teacher'])  # 只允许教师访问成绩管理
def show_progress():
    return render_template('progress.html', role=session.get('role', ''))

@app.route('/interaction')
@login_required
@role_required(['teacher'])  # 只允许教师访问作业管理
def show_interaction():
    return render_template('interaction.html', role=session.get('role', ''))

# 学生专有页面路由
@app.route('/student/courses')
@login_required
@role_required(['student'])  # 只允许学生角色访问
def show_student_courses():
    """显示学生课程页面，包括已选课程和可选课程"""
    return render_template('student/courses.html')

@app.route('/student/progress')
@login_required
@role_required(['student'])
def show_student_progress():
    return render_template('student/progress.html')

@app.route('/student/assignments')
@login_required
@role_required(['student'])
def show_student_assignments():
    return render_template('student/assignments.html')

# 学生个人资料页面路由
@app.route('/student/profile')
@login_required
@role_required(['student'])
def show_student_profile():
    return render_template('student/profile.html')

# 教师个人资料页面路由
@app.route('/teacher/profile')
@login_required
@role_required(['teacher'])
def show_teacher_profile():
    return render_template('teacher/profile.html')

# 管理员个人资料页面路由
@app.route('/admin/profile')
@login_required
@role_required(['admin'])
def show_admin_profile():
    return render_template('admin/profile.html')
