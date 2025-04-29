from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from itsdangerous import URLSafeTimedSerializer
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

s = URLSafeTimedSerializer(app.secret_key)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("register"))
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        send_verification_email(user)
        flash("Registration successful. Check your email to confirm your account.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/confirm/<token>")
def confirm_email(token):
    try:
        email = s.loads(token, max_age=3600)
    except:
        flash("The confirmation link is invalid or has expired.")
        return redirect(url_for("login"))
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash("Account already confirmed.")
    else:
        user.confirmed = True
        db.session.commit()
        flash("Account confirmed.")
    return redirect(url_for("login"))

def send_verification_email(user):
    token = s.dumps(user.email)
    confirm_url = url_for("confirm_email", token=token, _external=True)
    message = Mail(
        from_email="your_email@example.com",
        to_emails=user.email,
        subject="Please confirm your email",
        html_content=f"Click to confirm your email: <a href='{confirm_url}'>{confirm_url}</a>"
    )
    try:
        sg = SendGridAPIClient("YOUR_SENDGRID_API_KEY")
        sg.send(message)
    except Exception as e:
        print("SendGrid error:", e)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email, password=password).first()
        if user and user.confirmed:
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid credentials or email not confirmed.")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
