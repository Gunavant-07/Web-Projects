from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import secrets
import string
import random
from datetime import datetime, timedelta
import logging
import MySQLdb.cursors
from werkzeug.utils import secure_filename
import os
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'task_manager'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Flask-Mail Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'smartyboy4873@gmail.com'
app.config['MAIL_PASSWORD'] = 'tszo goxw zbtg llvf'  # Verify this App Password
app.config['MAIL_DEFAULT_SENDER'] = ('TASK MANAGER', 'smartyboy4873@gmail.com')
app.config['MAIL_DEBUG'] = True
app.config['MAIL_SUPPRESS_SEND'] = False

# Upload Config
app.config['UPLOAD_FOLDER'] = 'static/uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)
socketio = SocketIO(app)

# Initialize the serializer for secure tokens
serializer = URLSafeTimedSerializer(app.secret_key)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



    
class User(UserMixin):
    def __init__(self, id, username, email, password_hash, profile_pic=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.profile_pic = profile_pic  # Add profile_pic attribute

# @app.route('/test_static')
# def test_static():
#     return send_from_directory(app.config['UPLOAD_FOLDER'], 'styles.css')

@login_manager.user_loader
def load_user(user_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        if user:
            return User(user['id'], user['username'], user['email'], user['password_hash'], user['profile_pic'])
        return None
    except Exception as e:
        logger.error(f"Error loading user: {e}")
        return None

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    try:
        msg = Message(
            subject='Your Registration OTP',
            recipients=[email],
            body=f"""Your One-Time Password (OTP) for registration is: {otp}
This OTP is valid for 10 minutes. Please enter it to complete your registration."""
        )
        mail.send(msg)
        logger.info(f"OTP email sent to {email}")
        return True, "OTP sent successfully"
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False, str(e)

def generate_reset_token(email):
    return serializer.dumps(email, salt='password-reset-salt')

def validate_reset_token(token, max_age=3600):  # max_age = 1 hour in seconds
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None

def send_reset_email(email, token):
    try:
        reset_url = url_for('reset_password', token=token, _external=True)
        msg = Message(
            subject='Password Reset Link',
            recipients=[email],
            body=f"""Please use the following link to reset your password. This link is valid for 1 hour:
{reset_url}
If you did not request a password reset, please ignore this email."""
        )
        mail.send(msg)
        logger.info(f"Reset email sent to {email}")
        return True, "Basic email sent", reset_url
    except Exception as e:
        logger.error(f"Failed to send reset email to {email}: {str(e)}")
        return False, str(e), None

@app.route('/')
def home():
    # If user is already authenticated, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    # Check if user has a session (e.g., from a previous visit or partial registration)
    email = session.get('email')
    if email:
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            if user:
                # User exists but not logged in, redirect to login
                return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")

    # No session or user found, assume new user and redirect to register
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if OTP verification is in progress
        if 'otp' in request.form:
            entered_otp = request.form['otp'].strip()
            stored_otp = session.get('otp')
            otp_expiry = session.get('otp_expiry')
            username = session.get('username')
            email = session.get('email')
            password = session.get('password')

            if not all([entered_otp, stored_otp, otp_expiry, username, email, password]):
                flash('Session expired or invalid data. Please start over.', 'danger')
                return redirect(url_for('register'))

            if datetime.now() > datetime.fromisoformat(otp_expiry):
                flash('OTP has expired! Please request a new one.', 'danger')
                session.pop('otp', None)
                session.pop('otp_expiry', None)
                session.pop('username', None)
                session.pop('email', None)
                session.pop('password', None)
                return redirect(url_for('register'))

            if entered_otp == stored_otp:
                try:
                    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                    cur = mysql.connection.cursor()
                    cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", 
                               (username, email, hashed_password))
                    mysql.connection.commit()
                    cur.close()
                    flash('Registration successful! Please log in.', 'success')
                    session.pop('otp', None)
                    session.pop('otp_expiry', None)
                    session.pop('username', None)
                    session.pop('email', None)
                    session.pop('password', None)
                    return redirect(url_for('login'))
                except Exception as e:
                    flash(f'Registration failed: {str(e)}', 'danger')
            else:
                flash('Incorrect OTP! Please try again.', 'danger')
            return render_template('register.html', show_otp=True, email=email)

        # Initial registration form submission
        try:
            username = request.form['username'].strip()
            email = request.form['email'].strip()
            password = request.form['password']

            if not all([username, email, password]):
                flash('All fields are required!', 'danger')
                return render_template('register.html')

            # Check if email already exists
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                flash('Email already registered!', 'danger')
                return render_template('register.html')

            cur.close()

            # Generate and send OTP
            otp = generate_otp()
            success, message = send_otp_email(email, otp)
            if success:
                session['otp'] = otp
                session['otp_expiry'] = (datetime.now() + timedelta(minutes=10)).isoformat()
                session['username'] = username
                session['email'] = email
                session['password'] = password
                return render_template('register.html', show_otp=True, email=email)
            else:
                flash(f'Failed to send OTP email: {message}. Please try again.', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email'].strip()
            password = request.form['password']

            if not all([email, password]):
                flash('All fields are required!', 'danger')
                return render_template('login.html')

            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()

            if user and bcrypt.check_password_hash(user['password_hash'], password):
                user_obj = User(user['id'], user['username'], user['email'], user['password_hash'], user['profile_pic'])
                login_user(user_obj)
                session['user_id'] = user['id']  # Ensure user_id is in session
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password', 'danger')
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
    return render_template('login.html')

@app.route('/forgotpass', methods=['GET', 'POST'])
def forgotpass():
    success_message = None
    reset_link = None
    if request.method == 'POST':
        try:
            email = request.form['email'].strip()
            if not email:
                flash('Email is required!', 'danger')
                return render_template('forgotpass.html')

            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()
            
            if user:
                reset_token = generate_reset_token(email)
                success, message, reset_url = send_reset_email(email, reset_token)
                if success:
                    success_message = "A password reset link has been sent to your email! Click below or check your inbox (and spam/junk folder):"
                    reset_link = reset_url
                else:
                    flash(f'Failed to send reset email: {message}. Please try again or contact support.', 'danger')
            else:
                flash('No account found with that email!', 'danger')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('forgotpass.html', success_message=success_message, reset_link=reset_link)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = validate_reset_token(token)
    if not email:
        flash('Invalid or expired reset link!', 'danger')
        return redirect(url_for('forgotpass'))

    if request.method == 'POST':
        try:
            new_password = request.form['password']
            if not new_password:
                flash('Password is required!', 'danger')
                return render_template('reset_password.html')
                
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET password_hash = %s WHERE email = %s", 
                       (hashed_password, email))
            mysql.connection.commit()
            cur.close()
            
            flash('Password reset successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error resetting password: {str(e)}', 'danger')
    
    return render_template('reset_password.html')

@app.route('/dashboard')
@login_required
def dashboard():
    current_date = datetime.now().strftime('%A, %d/%m/%Y')
    return render_template('dashboard.html', current_user=current_user, current_date=current_date)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    data = request.get_json()
    title = data.get('title')
    category = data.get('category')
    due_date = data.get('due_date')

    logger.info(f"Received task data: title={title}, category={category}, due_date={due_date}")

    if not title or not category:
        logger.error("Title or category missing in request")
        return jsonify({'error': 'Title and category are required'}), 400

    try:
        cur = mysql.connection.cursor()
        
        query_max_position = """
            SELECT COALESCE(MAX(order_position), -1) + 1 AS next_position 
            FROM tasks 
            WHERE user_id = %s AND category = %s
        """
        cur.execute(query_max_position, (current_user.id, category))
        result = cur.fetchone()
        next_position = result['next_position']
        
        query_insert = """
            INSERT INTO tasks (user_id, title, category, completed, important, due_date, order_position) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query_insert, (current_user.id, title, category, False, False, due_date if due_date else None, next_position))
        mysql.connection.commit()
        
        logger.info(f"Task added successfully: title={title}, category={category}, user_id={current_user.id}, order_position={next_position}")
        cur.close()
        return jsonify({'message': 'Task added successfully'})
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_tasks/<category>', methods=['GET'])
@login_required
def get_tasks(category):
    try:
        logger.info(f"Fetching tasks for user_id: {current_user.id}, category: {category}")
        cur = mysql.connection.cursor()
        
        if category == 'important':
            query = """
                SELECT id, title, category, completed, important, due_date, order_position 
                FROM tasks 
                WHERE user_id = %s AND important = TRUE
                ORDER BY order_position
            """
            cur.execute(query, (current_user.id,))
        else:
            query = """
                SELECT id, title, category, completed, important, due_date, order_position 
                FROM tasks 
                WHERE user_id = %s AND LOWER(category) = LOWER(%s)
                ORDER BY order_position
            """
            cur.execute(query, (current_user.id, category))
        
        tasks = cur.fetchall()
        cur.close()
        logger.info(f"Found {len(tasks)} tasks for category {category}: {tasks}")
        return jsonify(tasks)
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/toggle_task/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT completed FROM tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        task = cur.fetchone()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        new_status = not task['completed']
        cur.execute("UPDATE tasks SET completed = %s WHERE id = %s", (new_status, task_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Task status updated successfully'})
    except Exception as e:
        logger.error(f"Error toggling task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/toggle_important/<int:task_id>', methods=['POST'])
@login_required
def toggle_important(task_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT important FROM tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        task = cur.fetchone()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        new_status = not task['important']
        cur.execute("UPDATE tasks SET important = %s WHERE id = %s", (new_status, task_id))
        mysql.connection.commit()
        cur.close()
        logger.info(f"Toggled important status for task {task_id} to {new_status}")
        return jsonify({'message': 'Task importance updated successfully', 'important': new_status})
    except Exception as e:
        logger.error(f"Error toggling important: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, current_user.id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Task deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_task_order', methods=['POST'])
@login_required
def update_task_order():
    data = request.get_json()
    task_order = data.get('task_order', [])
    try:
        cur = mysql.connection.cursor()
        for index, task_id in enumerate(task_order):
            cur.execute("UPDATE tasks SET order_position = %s WHERE id = %s AND user_id = %s", (index, task_id, current_user.id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Task order updated successfully'})
    except Exception as e:
        logger.error(f"Error updating task order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/add_custom_list', methods=['POST'])
@login_required
def add_custom_list():
    data = request.get_json()
    list_name = data.get('list_name')
    if not list_name:
        return jsonify({'error': 'List name is required'}), 400
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO custom_lists (user_id, list_name) VALUES (%s, %s)", (current_user.id, list_name))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Custom list added successfully'})
    except Exception as e:
        logger.error(f"Error adding custom list: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_custom_lists', methods=['GET'])
@login_required
def get_custom_lists():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT list_name FROM custom_lists WHERE user_id = %s", (current_user.id,))
        lists = cur.fetchall()
        cur.close()
        return jsonify(lists)
    except Exception as e:
        logger.error(f"Error fetching custom lists: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_custom_list', methods=['POST'])
@login_required
def delete_custom_list():
    data = request.get_json()
    list_name = data.get('list_name')
    if not list_name:
        logger.error("List name missing in request")
        return jsonify({'error': 'List name is required'}), 400

    try:
        cur = mysql.connection.cursor()
        
        # Check if the custom list exists for the current user
        cur.execute("SELECT id FROM custom_lists WHERE user_id = %s AND list_name = %s", (current_user.id, list_name))
        custom_list = cur.fetchone()
        if not custom_list:
            logger.warning(f"Custom list '{list_name}' not found for user_id: {current_user.id}")
            return jsonify({'error': 'List not found'}), 404

        # Delete all tasks associated with the custom list
        cur.execute("DELETE FROM tasks WHERE user_id = %s AND category = %s", (current_user.id, list_name))
        logger.info(f"Deleted {cur.rowcount} tasks from '{list_name}' for user_id: {current_user.id}")

        # Delete the custom list
        cur.execute("DELETE FROM custom_lists WHERE user_id = %s AND list_name = %s", 
                   (current_user.id, list_name))
        mysql.connection.commit()
        cur.close()

        logger.info(f"Deleted custom list: {list_name} for user_id: {current_user.id}")
        return jsonify({'message': 'Custom list and all its tasks deleted'}), 200

    except Exception as e:
        logger.error(f"Error deleting custom list: {e}")
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/update_profile_pic', methods=['POST'])
@login_required
def update_profile_pic():
    if 'profile_pic' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['profile_pic']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Update user profile picture
        cur = mysql.connection.cursor()
        profile_pic_url = url_for('static', filename=f'uploads/{filename}')
        cur.execute("UPDATE users SET profile_pic = %s WHERE id = %s", (profile_pic_url, current_user.id))
        mysql.connection.commit()
        cur.close()

        # Update the current_user object in the session
        current_user.profile_pic = profile_pic_url
        session['user_profile_pic'] = profile_pic_url  # Optional: Store in session for immediate use

        return jsonify({'message': 'Profile picture updated', 'profile_pic': profile_pic_url}), 200
    return jsonify({'error': 'Invalid file'}), 400

if __name__ == '__main__':
    app.run(debug=True)