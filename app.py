from flask import Flask, render_template, request, redirect, session, url_for
import json, os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Инициализация
if not os.path.exists('data'):
    os.makedirs('data')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

for file in ['users.json', 'messages.json']:
    path = f'data/{file}'
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({} if file == 'users.json' else {"general": []}, f)

def load_users():
    with open('data/users.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open('data/users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)

def load_messages():
    with open('data/messages.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_messages(messages):
    with open('data/messages.json', 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    if 'username' in session:
        return redirect('/channel/general')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect('/channel/general')
        return render_template('login.html', error='Неверный логин или пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        if username in users:
            return render_template('register.html', error='Пользователь уже существует')
        if password != confirm:
            return render_template('register.html', error='Пароли не совпадают')
        users[username] = {
            'password': password,
            'role': 'user',
            'mute_until': '',
            'channels': ['general', 'memes', 'support', 'chat', 'news'],
            'hide_profile': False,
            'avatar': 'default.png'
        }
        save_users(users)
        return redirect('/login')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/channel/<channel>')
def channel(channel):
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    session['channel'] = channel
    users = load_users()
    messages = load_messages()
    if channel not in messages:
        messages[channel] = []
        save_messages(messages)
    muted = False
    if users[username].get("mute_until"):
        mute_time = datetime.strptime(users[username]["mute_until"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < mute_time:
            muted = True
        else:
            users[username]["mute_until"] = ""
            save_users(users)
    return render_template('index.html', username=username, channel=channel, users=users, messages=messages[channel], muted=muted)

@app.route('/send', methods=['POST'])
def send():
    if 'username' not in session:
        return redirect('/login')
    username = session['username']
    users = load_users()
    messages = load_messages()
    channel = request.form['channel']
    text = request.form['message'].strip()
    if not text:
        return redirect(f'/channel/{channel}')
    if users[username].get("mute_until"):
        mute_time = datetime.strptime(users[username]["mute_until"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < mute_time:
            return redirect(f'/channel/{channel}')
    if channel == "news" and users[username]["role"] != "admin":
        return redirect(f'/channel/{channel}')
    msg = {
        "user": username,
        "text": text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if channel not in messages:
        messages[channel] = []
    messages[channel].append(msg)
    save_messages(messages)
    return redirect(f'/channel/{channel}')

@app.route('/delete_message', methods=['POST'])
def delete_message():
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    username = session['username']
    if users[username]['role'] != 'admin':
        return "Доступ запрещён", 403
    channel = request.form.get('channel')
    time_to_delete = request.form.get('time')
    if not channel or not time_to_delete:
        return "Неверный запрос", 400
    messages = load_messages()
    if channel in messages:
        messages[channel] = [m for m in messages[channel] if m.get('time') != time_to_delete]
        save_messages(messages)
    return redirect(f"/channel/{channel}")

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    username = session['username']
    if request.method == 'POST':
        new_name = request.form.get("new_name", "").strip()
        hide = request.form.get("hide_profile") == "on"
        users[username]["hide_profile"] = hide
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(username + '.' + ext)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                users[username]['avatar'] = filename
        if new_name and new_name != username and new_name not in users:
            users[new_name] = users.pop(username)
            session["username"] = new_name
        save_users(users)
        return redirect('/settings')
    return render_template("settings.html", username=username, users=users)

@app.route('/profile/<target_user>')
def view_profile(target_user):
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    if target_user not in users or users[target_user].get("hide_profile", False):
        return render_template('profile_hidden.html', target=target_user)
    return render_template('view_profile.html', username=session['username'], target=target_user, users=users)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect('/login')

    users = load_users()
    username = session['username']

    if request.method == 'POST':
        # смена ника
        new_name = request.form.get("new_name", "").strip()
        if new_name and new_name != username and new_name not in users:
            users[new_name] = users.pop(username)
            session["username"] = new_name
            username = new_name  # обновим переменную

        # смена конфиденциальности
        hide = request.form.get("hide_profile") == "on"
        users[username]["hide_profile"] = hide

        # смена аватара
        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            ext = avatar_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ['png', 'jpg', 'jpeg', 'gif']:
                avatar_filename = f"{username}.{ext}"
                avatar_path = os.path.join("static", "avatars", avatar_filename)
                avatar_file.save(avatar_path)
                users[username]["avatar"] = avatar_filename

        save_users(users)
        return redirect('/profile')

    return render_template('profile.html', username=username, users=users)


@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'username' not in session:
        return redirect('/login')
    users = load_users()
    username = session['username']
    if users[username]['role'] != 'admin':
        return "Доступ запрещён", 403
    if request.method == 'POST':
        target = request.form.get('target')
        minutes = int(request.form.get('minutes', 0))
        if target in users:
            mute_until = datetime.now() + timedelta(minutes=minutes)
            users[target]['mute_until'] = mute_until.strftime("%Y-%m-%d %H:%M:%S")
            save_users(users)
        return redirect('/admin')
    return render_template('admin.html', users=users, username=username)

if __name__ == '__main__':
    app.run(debug=True)
