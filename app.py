import os
from flask import Flask, render_template, request, redirect, flash, url_for
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import re

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "supersecretkey"

# Email config from environment
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS") == "True",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
)

mail = Mail(app)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'txt'}

# Upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Validate email format
def is_valid_email(email):
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email) is not None

# Check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message_body = request.form.get('message', '').strip()
        sender = request.form.get('sender', '').strip()
        recipients_raw = request.form.get('recipients', '')
        recipient_emails = [email.strip() for email in recipients_raw.split(',') if email.strip()]

        # Validate inputs
        if not subject or not message_body or not sender or not recipient_emails:
            flash("Please fill in all required fields and add at least one recipient.", 'error')
            return redirect(url_for('index'))

        # Validate sender email format
        if not is_valid_email(sender):
            flash("Invalid sender email entered.", 'error')
            return redirect(url_for('index'))

        # Validate recipient emails
        for email in recipient_emails:
            if not is_valid_email(email):
                flash(f"Invalid recipient email: {email}", 'error')
                return redirect(url_for('index'))

        # Get file uploads
        files = request.files.getlist('attachments')

        attachments = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                attachments.append((filename, filepath))
            elif file.filename != '':
                flash(f"File type not allowed: {file.filename}", "error")
                return redirect(url_for('index'))

        # Compose and send email
        try:
            msg = Message(subject=subject, sender=sender, recipients=recipient_emails, body=message_body)

            for filename, filepath in attachments:
                with open(filepath, 'rb') as f:
                    msg.attach(filename, "application/octet-stream", f.read())

            mail.send(msg)

            # Remove uploaded files after sending
            for _, filepath in attachments:
                os.remove(filepath)

            flash("Email sent successfully!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            flash(f"Failed to send email: {str(e)}", "error")
            return redirect(url_for('index'))

    return render_template('index.html')
