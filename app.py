from flask import Flask, render_template, request, redirect, session
from flask_mail import Mail, Message
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import letter
import sqlite3
import random
import datetime
import uuid
import os

app = Flask(__name__)

app.secret_key = "helpdesk"

# ---------------- MAIL CONFIG ----------------

app.config['MAIL_SERVER'] = 'smtp.gmail.com'

app.config['MAIL_PORT'] = 587

app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = 'rpm0476@gmail.com'

app.config['MAIL_PASSWORD'] = 'Pass@234'

mail = Mail(app)

# ---------------- UPLOAD FOLDER ----------------

UPLOAD_FOLDER = 'static/uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):

    os.makedirs(UPLOAD_FOLDER)

# ---------------- DATABASE ----------------

def init_db():

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    # USERS TABLE

    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        role TEXT

    )
    ''')

    # TICKETS TABLE

    cur.execute('''
    CREATE TABLE IF NOT EXISTS tickets (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_no TEXT,
        username TEXT,
        assigned_to TEXT,
        title TEXT,
        description TEXT,
        category TEXT,
        priority TEXT,
        status TEXT,
        file TEXT,
        created_at TEXT

    )
    ''')

    # REPLIES TABLE

    cur.execute('''
    CREATE TABLE IF NOT EXISTS replies (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        sender TEXT,
        message TEXT,
        created_at TEXT

    )
    ''')

    # PASSWORD RESET TOKENS

    cur.execute('''
    CREATE TABLE IF NOT EXISTS password_resets (

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        token TEXT,
        created_at TEXT

    )
    ''')

    conn.commit()

    cur.execute("PRAGMA table_info(tickets)")
    ticket_columns = [row[1] for row in cur.fetchall()]

    if 'assigned_to' not in ticket_columns:
        cur.execute("ALTER TABLE tickets ADD COLUMN assigned_to TEXT DEFAULT 'Not Assigned'")
    if 'category' not in ticket_columns:
        cur.execute("ALTER TABLE tickets ADD COLUMN category TEXT DEFAULT ''")
    if 'priority' not in ticket_columns:
        cur.execute("ALTER TABLE tickets ADD COLUMN priority TEXT DEFAULT 'Low'")
    if 'status' not in ticket_columns:
        cur.execute("ALTER TABLE tickets ADD COLUMN status TEXT DEFAULT 'Open'")
    if 'file' not in ticket_columns:
        cur.execute("ALTER TABLE tickets ADD COLUMN file TEXT DEFAULT ''")
    if 'created_at' not in ticket_columns:
        cur.execute("ALTER TABLE tickets ADD COLUMN created_at TEXT DEFAULT ''")

    conn.commit()
    conn.close()

init_db()

# ---------------- SEND EMAIL ----------------

def send_email(to, subject, body):

    try:

        msg = Message(

            subject,

            sender=app.config['MAIL_USERNAME'],

            recipients=[to]

        )

        msg.body = body

        mail.send(msg)

        return True

    except Exception as e:

        print(e)

        return False


def send_email_result(to, subject, body):

    try:

        msg = Message(

            subject,

            sender=app.config['MAIL_USERNAME'],

            recipients=[to]

        )

        msg.body = body

        mail.send(msg)

        return True, None

    except Exception as e:

        print(e)

        return False, str(e)

# ---------------- HOME ----------------

@app.route('/')
def home():

    return render_template('login.html')

# ---------------- REGISTER ----------------

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if email == "admin@gmail.com":

            role = "admin"

        else:

            role = "user"

        conn = sqlite3.connect('database.db')

        conn.execute(
            '''
            INSERT INTO users(
            name,
            email,
            password,
            role
            )
            VALUES(?,?,?,?)
            ''',
            (
                name,
                email,
                password,
                role
            )
        )

        conn.commit()

        send_email(
            email,
            'Welcome to Help Desk',
            f'Hi {name},\n\nYour account has been created successfully. You can login with this email at {request.host_url}.\n\nThanks,\nHelp Desk Team'
        )

        conn.close()

        return redirect('/')

    return render_template('register.html')

# ---------------- FORGOT PASSWORD ----------------

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form['email']

        conn = sqlite3.connect('database.db')

        cur = conn.cursor()

        cur.execute(
            '''
            SELECT * FROM users
            WHERE email=?
            ''',
            (email,)
        )

        user = cur.fetchone()

        if user:

            token = uuid.uuid4().hex

            created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cur.execute(
                '''
                INSERT INTO password_resets(
                email,
                token,
                created_at
                )
                VALUES(?,?,?)
                ''',
                (
                    email,
                    token,
                    created_at
                )
            )

            conn.commit()

            reset_link = request.host_url.rstrip('/') + f'/reset_password/{token}'

            email_sent, email_error = send_email_result(
                email,
                'Help Desk Password Reset',
                f'Hi {user[1]},\n\nA password reset request was received for your account.\n\nPlease open the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, you can safely ignore this email.\n\nThanks,\nHelp Desk Team'
            )

        else:
            reset_link = None
            email_sent = False
            email_error = 'Email address not registered.'

        conn.close()

        return render_template(
            'forgot_password.html',
            message='If that email is registered, a reset link has been sent.',
            reset_link=reset_link,
            email_sent=email_sent,
            email_error=email_error
        )

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    cur.execute(
        '''
        SELECT email,
               created_at
        FROM password_resets
        WHERE token=?
        ''',
        (token,)
    )

    row = cur.fetchone()

    if not row:

        conn.close()

        return render_template('reset_password.html', error='Invalid or expired password reset link.')

    created_at = datetime.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')

    if datetime.datetime.now() - created_at > datetime.timedelta(hours=24):

        cur.execute(
            '''
            DELETE FROM password_resets
            WHERE token=?
            ''',
            (token,)
        )

        conn.commit()

        conn.close()

        return render_template('reset_password.html', error='This password reset link has expired.')

    if request.method == 'POST':

        new_password = request.form['password']

        cur.execute(
            '''
            UPDATE users
            SET password=?
            WHERE email=?
            ''',
            (
                new_password,
                row[0]
            )
        )

        cur.execute(
            '''
            DELETE FROM password_resets
            WHERE token=?
            ''',
            (token,)
        )

        conn.commit()

        conn.close()

        return render_template('reset_password.html', success='Your password has been reset. You can now login.')

    conn.close()

    return render_template('reset_password.html')


# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    cur.execute(
        '''
        SELECT * FROM users
        WHERE email=? AND password=?
        ''',
        (
            email,
            password
        )
    )

    user = cur.fetchone()

    conn.close()

    if user:

        session['user'] = user[1]
        session['role'] = user[4]

        return redirect('/dashboard')

    else:

        return "Invalid Login"

# ---------------- DASHBOARD ----------------

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:

        return redirect('/')

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    if session['role'] == 'admin':

        total_query = '''
        SELECT COUNT(*) FROM tickets
        '''

        open_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status='Open'
        '''

        progress_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status='In Progress'
        '''

        closed_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status='Closed'
        '''

        recent_query = '''
        SELECT * FROM tickets
        ORDER BY id DESC
        LIMIT 5
        '''

        query_params = ()

    else:

        total_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        '''

        open_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        AND status='Open'
        '''

        progress_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        AND status='In Progress'
        '''

        closed_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        AND status='Closed'
        '''

        recent_query = '''
        SELECT * FROM tickets
        WHERE username=?
        ORDER BY id DESC
        LIMIT 2
        '''

        query_params = (session['user'],)

    cur.execute(total_query, query_params)
    total = cur.fetchone()[0]

    cur.execute(open_query, query_params)
    open_count = cur.fetchone()[0]

    cur.execute(progress_query, query_params)
    progress_count = cur.fetchone()[0]

    cur.execute(closed_query, query_params)
    closed_count = cur.fetchone()[0]

    if session['role'] == 'admin':
        cur.execute(
            '''
            SELECT COUNT(*) FROM tickets
            WHERE priority='High'
            '''
        )
    else:
        cur.execute(
            '''
            SELECT COUNT(*) FROM tickets
            WHERE username=?
            AND priority='High'
            ''',
            query_params
        )
    high_priority = cur.fetchone()[0]

    cur.execute(recent_query, query_params)
    recent_tickets = cur.fetchall()

    conn.close()

    return render_template(

        'dashboard.html',

        username=session['user'],
        role=session['role'],
        total=total,
        open_count=open_count,
        progress_count=progress_count,
        closed_count=closed_count,
        high_priority=high_priority,
        recent_tickets=recent_tickets

    )

# ---------------- ANALYTICS ----------------

@app.route('/analytics')
def analytics():

    if 'user' not in session:

        return redirect('/')

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    if session['role'] == 'admin':
        open_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status='Open'
        '''

        progress_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status='In Progress'
        '''

        closed_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE status='Closed'
        '''

        query_params = ()
    else:
        open_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        AND status='Open'
        '''

        progress_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        AND status='In Progress'
        '''

        closed_query = '''
        SELECT COUNT(*) FROM tickets
        WHERE username=?
        AND status='Closed'
        '''

        query_params = (session['user'],)

    cur.execute(open_query, query_params)
    open_count = cur.fetchone()[0]

    cur.execute(progress_query, query_params)
    progress_count = cur.fetchone()[0]

    cur.execute(closed_query, query_params)
    closed_count = cur.fetchone()[0]

    conn.close()

    return render_template(

        'analytics.html',

        open_count=open_count,
        progress_count=progress_count,
        closed_count=closed_count,
        role=session['role']

    )

# ---------------- TICKETS ----------------

@app.route('/tickets')
def tickets():

    if 'user' not in session:

        return redirect('/')

    search = request.args.get('search')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()

    if session['role'] == 'admin':

        if search:

            cur.execute(
                '''
                SELECT id,
                       ticket_no,
                       username,
                       assigned_to,
                       title,
                       description,
                       category,
                       priority,
                       status,
                       file,
                       created_at
                FROM tickets
                WHERE title LIKE ?
                ORDER BY id DESC
                ''',
                (
                    '%' + search + '%',
                )
            )

        else:

            cur.execute(
                '''
                SELECT id,
                       ticket_no,
                       username,
                       assigned_to,
                       title,
                       description,
                       category,
                       priority,
                       status,
                       file,
                       created_at
                FROM tickets
                ORDER BY id DESC
                '''
            )

    else:

        if search:

            cur.execute(
                '''
                SELECT id,
                       ticket_no,
                       username,
                       assigned_to,
                       title,
                       description,
                       category,
                       priority,
                       status,
                       file,
                       created_at
                FROM tickets
                WHERE username=?
                AND title LIKE ?
                ORDER BY id DESC
                ''',
                (
                    session['user'],
                    '%' + search + '%'
                )
            )

        else:

            cur.execute(
                '''
                SELECT id,
                       ticket_no,
                       username,
                       assigned_to,
                       title,
                       description,
                       category,
                       priority,
                       status,
                       file,
                       created_at
                FROM tickets
                WHERE username=?
                ORDER BY id DESC
                ''',
                (
                    session['user'],
                )
            )

    tickets = cur.fetchall()

    conn.close()

    return render_template(
        'tickets.html',
        tickets=tickets,
        role=session['role']
    )

# ---------------- CREATE TICKET ----------------

@app.route('/create_ticket', methods=['GET', 'POST'])
def create_ticket():

    if 'user' not in session:

        return redirect('/')

    if request.method == 'POST':

        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        priority = request.form['priority']

        file = request.files.get('file')

        filename = ""

        if file and file.filename:

            filename = file.filename

            file.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

        ticket_no = "TKT-" + str(
            random.randint(100000, 999999)
        )

        created_at = datetime.datetime.now().strftime(
            "%d-%m-%Y %H:%M"
        )

        conn = sqlite3.connect('database.db')

        conn.execute(
            '''
            INSERT INTO tickets(
            ticket_no,
            username,
            assigned_to,
            title,
            description,
            category,
            priority,
            status,
            file,
            created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ''',
            (
                ticket_no,
                session['user'],
                "Not Assigned",
                title,
                description,
                category,
                priority,
                "Open",
                filename,
                created_at
            )
        )

        conn.commit()

        cur = conn.cursor()

        cur.execute(
            '''
            SELECT email FROM users
            WHERE name=?
            ''',
            (
                session['user'],
            )
        )

        user_email = cur.fetchone()[0]

        send_email(
            user_email,
            'Ticket Created',
            f'Hi {session["user"]},\n\nYour ticket {ticket_no} has been created successfully.\n\nTitle: {title}\nCategory: {category}\nPriority: {priority}\n\nThank you for submitting your request.'
        )

        send_email(
            'admin@gmail.com',
            'New Ticket Created',
            f'New ticket created by {session["user"]}:\n\nTicket No: {ticket_no}\nTitle: {title}\nCategory: {category}\nPriority: {priority}\nStatus: Open\n\nPlease take action as needed.'
        )

        conn.close()

        return redirect('/tickets')

    return render_template(
        'create_ticket.html',
        role=session['role']
    )

# ---------------- ASSIGN TICKET ----------------

@app.route('/assign_ticket/<int:id>', methods=['GET', 'POST'])
def assign_ticket(id):

    if session['role'] != 'admin':

        return "Access Denied"

    conn = sqlite3.connect('database.db')

    if request.method == 'POST':

        assigned_to = request.form['assigned_to']

        conn.execute(
            '''
            UPDATE tickets
            SET assigned_to=?
            WHERE id=?
            ''',
            (
                assigned_to,
                id
            )
        )

        conn.commit()

        send_email(

            "admin@gmail.com",

            "Ticket Assigned",

            f"Ticket ID {id} assigned to {assigned_to}"

        )

        conn.close()

        return redirect('/tickets')

    return render_template('assign_ticket.html')

# ---------------- TICKET REPLY ----------------

@app.route('/ticket_reply/<int:id>', methods=['GET', 'POST'])
def ticket_reply(id):

    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT * FROM tickets
        WHERE id=?
        ''',
        (id,)
    )

    ticket = cur.fetchone()

    if not ticket:
        conn.close()
        return "Ticket not found"

    if session.get('role') != 'admin' and ticket['username'] != session['user']:
        conn.close()
        return "Access Denied"

    if request.method == 'POST':
        message = request.form['message']
        created_at = datetime.datetime.now().strftime(
            "%d-%m-%Y %H:%M"
        )

        conn.execute(
            '''
            INSERT INTO replies(
            ticket_id,
            sender,
            message,
            created_at
            )
            VALUES(?,?,?,?)
            ''',
            (
                id,
                session['user'],
                message,
                created_at
            )
        )

        conn.commit()

    cur.execute(
        '''
        SELECT * FROM replies
        WHERE ticket_id=?
        ORDER BY id ASC
        ''',
        (id,)
    )

    replies = cur.fetchall()

    conn.close()

    return render_template(
        'ticket_reply.html',
        ticket=ticket,
        replies=replies
    )

# ---------------- PROGRESS ----------------

@app.route('/progress_ticket/<int:id>')
def progress_ticket(id):

    if session['role'] != 'admin':

        return "Access Denied"

    conn = sqlite3.connect('database.db')

    conn.execute(
        '''
        UPDATE tickets
        SET status='In Progress'
        WHERE id=?
        ''',
        (id,)
    )

    conn.commit()

    conn.close()

    return redirect('/tickets')

# ---------------- CLOSE ----------------

@app.route('/close_ticket/<int:id>')
def close_ticket(id):

    if session['role'] != 'admin':

        return "Access Denied"

    conn = sqlite3.connect('database.db')

    conn.execute(
        '''
        UPDATE tickets
        SET status='Closed'
        WHERE id=?
        ''',
        (id,)
    )

    conn.commit()

    send_email(

        "admin@gmail.com",

        "Ticket Closed",

        f"Ticket ID {id} closed successfully."

    )

    conn.close()

    return redirect('/tickets')

# ---------------- DELETE ----------------

@app.route('/delete_ticket/<int:id>')
def delete_ticket(id):

    if session['role'] != 'admin':

        return "Access Denied"

    conn = sqlite3.connect('database.db')

    conn.execute(
        '''
        DELETE FROM tickets
        WHERE id=?
        ''',
        (id,)
    )

    conn.commit()

    conn.close()

    return redirect('/tickets')

# ---------------- PDF REPORT ----------------

@app.route('/download_report')
def download_report():

    if session['role'] != 'admin':

        return "Access Denied"

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    cur.execute(
        '''
        SELECT ticket_no,
               username,
               title,
               priority,
               status,
               created_at
        FROM tickets
        '''
    )

    tickets = cur.fetchall()

    conn.close()

    pdf_file = "static/ticket_report.pdf"

    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter
    )

    elements = []

    data = [[

        "Ticket No",
        "User",
        "Title",
        "Priority",
        "Status",
        "Date"

    ]]

    for ticket in tickets:

        data.append(ticket)

    table = Table(data)

    elements.append(table)

    doc.build(elements)

    return redirect('/static/ticket_report.pdf')

# ---------------- PROFILE ----------------

@app.route('/profile', methods=['GET', 'POST'])
def profile():

    if 'user' not in session:

        return redirect('/')

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    cur.execute(
        '''
        SELECT * FROM users
        WHERE name=?
        ''',
        (
            session['user'],
        )
    )

    user = cur.fetchone()

    if request.method == 'POST':

        new_name = request.form['name']

        new_password = request.form['password']

        conn.execute(
            '''
            UPDATE users
            SET name=?,
                password=?
            WHERE name=?
            ''',
            (
                new_name,
                new_password,
                session['user']
            )
        )

        conn.commit()

        session['user'] = new_name

        conn.close()

        return redirect('/profile')

    conn.close()

    return render_template(
        'profile.html',
        username=user[1],
        email=user[2],
        role=user[4]
    )

# ---------------- ADMIN ----------------

@app.route('/admin')
def admin():

    if session['role'] != 'admin':

        return "Access Denied"

    conn = sqlite3.connect('database.db')

    cur = conn.cursor()

    cur.execute(
        '''
        SELECT COUNT(*) FROM users
        '''
    )

    users = cur.fetchone()[0]

    cur.execute(
        '''
        SELECT COUNT(*) FROM tickets
        '''
    )

    tickets = cur.fetchone()[0]

    cur.execute(
        '''
        SELECT COUNT(*) FROM tickets
        WHERE status='Closed'
        '''
    )

    closed = cur.fetchone()[0]

    conn.close()

    return render_template(
        'admin.html',
        users=users,
        tickets=tickets,
        closed=closed
    )

# ---------------- ADMIN USER MANAGEMENT ----------------

@app.route('/admin/users')
def admin_users():

    if session.get('role') != 'admin':
        return "Access Denied"

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT id,
               name,
               email,
               role
        FROM users
        ORDER BY id ASC
        '''
    )

    users = cur.fetchall()
    conn.close()

    return render_template(
        'admin_users.html',
        users=users
    )


@app.route('/admin/reset_user_password/<int:user_id>', methods=['GET', 'POST'])
def admin_reset_user_password(user_id):

    if session.get('role') != 'admin':
        return "Access Denied"

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT id,
               name,
               email,
               role
        FROM users
        WHERE id=?
        ''',
        (user_id,)
    )

    user = cur.fetchone()

    if not user:
        conn.close()
        return "User not found"

    if request.method == 'POST':
        new_password = request.form['password']
        cur.execute(
            '''
            UPDATE users
            SET password=?
            WHERE id=?
            ''',
            (
                new_password,
                user_id
            )
        )
        conn.commit()
        conn.close()

        send_email(
            user[2],
            'Your Help Desk Password Has Been Reset',
            f'Hi {user[1]},\n\nYour account password has been updated by the admin. You can now login with your new password.\n\nIf you did not request this change, please contact support.\n\nThanks,\nHelp Desk Team'
        )

        return render_template(
            'admin_reset_user_password.html',
            user=user,
            success='Password updated successfully.'
        )

    conn.close()
    return render_template(
        'admin_reset_user_password.html',
        user=user
    )

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

# ---------------- 404 ----------------

@app.errorhandler(404)
def not_found(error):

    return render_template('404.html'), 404

# ---------------- RUN ----------------

if __name__ == '__main__':

    app.run(debug=True)

