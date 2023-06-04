from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import os
import sys
import click
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# url前缀 兼容性处理
WIN = sys.platform.startswith('win')
if WIN:  # 如果是 Windows 系统，使用三个斜线
    prefix = 'sqlite:///'
else:  # 否则使用四个斜线，代表绝对地址
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config.update(DEBUG=True)
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控
app.config['SECRET_KEY'] = 'dev'  # flash()把消息存储到 session 对象里, session会把数据签名后存储到浏览器的 Cookie 中, 此处设置签名所需的密钥
db = SQLAlchemy(app) # 初始化扩展，传入程序实例 app

class User(db.Model, UserMixin):  # 表名将会是 user（自动生成，小写处理）
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(5))  # 名字
    username = db.Column(db.String(20))  # 用户名
    password_hash = db.Column(db.String(128))  # 密码散列值

    def set_password(self, password):  # 用来设置密码的方法，接受密码作为参数
        self.password_hash = generate_password_hash(password)  # 将生成的密码保持到对应字段

    def validate_password(self, password):  # 用于验证密码的方法，接受密码作为参数
        return check_password_hash(self.password_hash, password)  # 返回布尔值

class Student(db.Model):  # 表名将会是 student
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(5))  # 学生姓名
    temper = db.Column(db.String(6))  # 学生温度
    stuNo = db.Column(db.String(13),db.ForeignKey('stuInfo.stuNo'))  # 学号
    # stuNo = db.relationship('StuInfo', backref='student', uselist=False)

class StuInfo(db.Model):
    __tablename__ = 'stuInfo'
    stuNo = db.Column(db.String(13),primary_key=True)
    stuClass = db.Column(db.String(3)) # 班级
    teacher = db.Column(db.String(4)) # 老师


@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)  # 设置密码
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)  # 设置密码
        db.session.add(user)

    db.session.commit()  # 提交数据库会话
    click.echo('Done.')

login_manager = LoginManager(app)  # 实例化扩展类
login_manager.login_view = 'login' # 未登录时把用户重定向到登录页面

@login_manager.user_loader
def load_user(user_id):  # 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id))  # 用 ID 作为 User 模型的主键查询对应的用户
    return user  # 返回用户对象

@app.cli.command()  # 注册为命令，可以传入 name 参数来自定义命令
@click.option('--drop', is_flag=True, help='Create after drop.')  # 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 输出提示信息

import click


@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()

    # 全局的两个变量移动到这个函数内
    name = 'CC'
    students = [
        {'name': '曹小晨', 'temper': '37.2℃', 'stuNo': '2021141530001'},
        {'name': '田小义', 'temper': '37.3℃', 'stuNo': '2021141530002'},
        {'name': '银小旭', 'temper': '37.4℃', 'stuNo': '2021141530003'},
        {'name': '陶小然', 'temper': '37.5℃', 'stuNo': '2021141530004'},
        {'name': '陶大然', 'temper': '37.8℃', 'stuNo': '2021141530005'},
    ]

    stuInfos = [
        {'stuNo':'2021141530001', 'stuClass':'106', 'teacher':'TWY'},
        {'stuNo':'2021141530002', 'stuClass':'106', 'teacher':'TWY'},
        {'stuNo':'2021141530003', 'stuClass':'106', 'teacher':'TWY'},
        {'stuNo':'2021141530004', 'stuClass':'106', 'teacher':'TWY'},
        {'stuNo':'2021141530005', 'stuClass':'103', 'teacher':'GX'},
    ]

    user = User(name=name)
    db.session.add(user)
    for s in students:
        student = Student(name=s['name'], temper=s['temper'], stuNo=s['stuNo'])
        db.session.add(student)

    for i in stuInfos:
        stuInfo = StuInfo(stuNo=i['stuNo'], stuClass=i['stuClass'], teacher=i['teacher'])
        db.session.add(stuInfo)

    db.session.commit()
    click.echo('Done.')

@app.context_processor # 装饰器注册模板上下文处理函数
def inject_user():
    user = User.query.first()
    return dict(user=user)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':  # 判断是否是 POST 请求
        content = request.form.get('content')  # 需要查询的内容
        if content: # 进行搜索
            students = Student.query.filter(
                Student.name.like("%" + content + "%") if content is not None else "").all()  # 查询跟content有关的数据，返回结果为列表

        else:
            if not current_user.is_authenticated:  # 如果当前用户未认证
                return redirect(url_for('index'))  # 重定向到主页
            # 获取表单数据
            name = request.form.get('name')  # 传入表单对应输入字段的 name 值
            temper = request.form.get('temper')
            stuNo = request.form.get('stuNo')
            # 验证数据
            if Student.query.filter_by(name=name).count()!=0:
                flash('Student Exist.')  # 显示错误提示
                return redirect(url_for('index'))  # 重定向回主页
            elif not name or not temper or not stuNo or len(temper) > 6 or len(name) > 5 or len(stuNo)>13:
                flash('Invalid input.')  # 显示错误提示
                return redirect(url_for('index'))  # 重定向回主页
            # 保存表单数据到数据库
            student = Student(name=name, temper=temper, stuNo=stuNo)  # 创建记录
            db.session.add(student)  # 添加到数据库会话
            db.session.commit()  # 提交数据库会话
            flash('Item created.')  # 显示成功创建的提示
            students = Student.query.all()
    else:
        students = Student.query.all()

    return render_template('index.html', students=students)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.first()
        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登入用户
            flash('Login success.')
            return redirect(url_for('index'))  # 重定向到主页

        flash('Invalid username or password.')  # 如果验证失败，显示错误消息
        return redirect(url_for('login'))  # 重定向回登录页面

    return render_template('login.html')

@app.route('/logout')
@login_required  # 用于视图保护，后面会详细介绍
def logout():
    logout_user()  # 登出用户
    flash('Goodbye.')
    return redirect(url_for('index'))  # 重定向回首页

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 5:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        current_user.name = name
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        # user = User.query.first()
        # user.name = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))

    return render_template('settings.html')

@app.route('/student/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':  # 处理编辑表单的提交请求
        name = request.form['name']
        temper = request.form['temper']
        stuNo = request.form['stuNo']

        if not name or not temper or not stuNo or len(temper) > 6 or len(name) > 5 or len(stuNo)>13:
            flash('Invalid input.')
            return redirect(url_for('edit', student_id=student_id))  # 重定向回对应的编辑页面

        student.name = name
        student.temper = temper
        student.stuNo = stuNo
        db.session.commit()  # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index'))  # 重定向回主页

    return render_template('edit.html', student=student)

@app.route('/student/delete/<int:student_id>', methods=['POST'])  # 限定只接受 POST 请求
@login_required  # 登录保护
def delete(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index'))  # 重定向回主页

@app.route('/info', methods=['GET', 'POST'])
def info():
    if request.method == 'POST':  # 判断是否是 POST 请求
        contentNo = request.form.get('contentNo')  # 需要查询的内容
        if contentNo: # 进行搜索
            stuInfos = StuInfo.query.filter(
                StuInfo.stuNo.like("%" + contentNo + "%") if contentNo is not None else "").all()  # 查询跟content有关的学号，返回结果为列表

        else:
            if not current_user.is_authenticated:  # 如果当前用户未认证
                return redirect(url_for('info'))  # 重定向到主页
            # 获取表单数据
            stuNo = request.form.get('stuNo')
            stuClass = request.form.get('stuClass')
            teacher = request.form.get('teacher')
            # 验证数据
            if StuInfo.query.filter_by(stuNo=stuNo).count()!=0:
                flash('StuInfo Exist.')  # 显示错误提示
                return redirect(url_for('info'))  # 重定向回主页
            elif not stuNo or not stuClass or not teacher or len(stuNo) > 13 or len(stuClass) > 3 or len(teacher)>4:
                flash('Invalid input.')  # 显示错误提示
                return redirect(url_for('info'))  # 重定向回主页
            # 保存表单数据到数据库
            stuInfo = StuInfo(stuNo=stuNo, stuClass=stuClass, teacher=teacher)  # 创建记录
            db.session.add(stuInfo)  # 添加到数据库会话
            db.session.commit()  # 提交数据库会话
            flash('Item created.')  # 显示成功创建的提示
            stuInfos = StuInfo.query.all()
    else:
        stuInfos = StuInfo.query.all()


    # students = Student.query.all()
    students = []
    for info in stuInfos:
        n = info.stuNo
        students.append(Student.query.filter(Student.stuNo==n).first())
    stuDict = zip(stuInfos, students)
    return render_template('info.html', stuDict=stuDict, stuInfos=stuInfos)

@app.route('/stuInfo/edit/<string:stu_No>', methods=['GET', 'POST'])
@login_required
def editInfo(stu_No):
    stuInfo = StuInfo.query.get_or_404(stu_No)

    if request.method == 'POST':  # 处理编辑表单的提交请求
        stuNo = request.form['stuNo']
        stuClass = request.form['stuClass']
        teacher = request.form['teacher']

        if not stuNo or not stuClass or not teacher or len(stuNo) > 13 or len(stuClass) > 3 or len(teacher)>4:
            flash('Invalid input.')
            return redirect(url_for('editInfo', stu_No=stu_No))  # 重定向回对应的编辑页面

        stuInfo.stuNo = stuNo
        stuInfo.stuClass = stuClass
        stuInfo.teacher = teacher
        db.session.commit()  # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('info'))  # 重定向回主页

    return render_template('editInfo.html', stuInfo=stuInfo)

@app.route('/stuInfo/delete/<string:stu_No>', methods=['POST'])  # 限定只接受 POST 请求
@login_required  # 登录保护
def deleteInfo(stu_No):
    stuInfo = StuInfo.query.get_or_404(stu_No)
    db.session.delete(stuInfo)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('info'))  # 重定向回主页