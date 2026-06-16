from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,date
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "finance_secret_key"
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
# USER TABLE
class User(db.Model, UserMixin):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    username = db.Column(
        db.String(100),
        nullable=False
    )
    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )
    password = db.Column(
        db.String(200),
        nullable=False
    )
# BUDGET TABLE
class Budget(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    amount = db.Column(
        db.Float,
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )
class SavingsGoal(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    goal = db.Column(
        db.String(100),
        nullable=False
    )
    target = db.Column(
        db.Float,
        nullable=False
    )
    saved = db.Column(
        db.Float,
        default=0
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )
# TRANSACTION TABLE
class Transaction(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    title = db.Column(
        db.String(100)
    )
    amount = db.Column(
        db.Float
    )
    category = db.Column(
        db.String(50)
    )
    type = db.Column(
        db.String(20)
    )
    notes = db.Column(
        db.String(200)
    )
    date = db.Column(
        db.DateTime,
        default=datetime.now
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        username=request.form["username"]
        email=request.form["email"]
        password=generate_password_hash(
            request.form["password"]
        )
        user=User(
            username=username,
            email=email,
            password=password
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")
# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"]
        password=request.form["password"]
        user=User.query.filter_by(
            email=email
        ).first()
        if user and check_password_hash(
            user.password,
            password
        ):
            login_user(user)
            return redirect("/")
    return render_template("login.html")
# LOGOUT
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")
# DASHBOARD
@app.route("/")
@login_required
def home():

    search = request.args.get("search", "")

    selected_category = request.args.get("category", "All")

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    income = sum(
        t.amount for t in transactions
        if t.type == "Income"
    )
    expense = sum(
        t.amount for t in transactions
        if t.type == "Expense"
    )
    balance = income - expense
    # THIS MONTH SPENDING
    today = datetime.now()
    month_expense = sum(
        t.amount for t in transactions
        if t.type == "Expense"
        and t.date.month == today.month
        and t.date.year == today.year
    )
    average_expense = 0
    if today.day > 0:
        average_expense = month_expense / today.day
    # CATEGORY CHART
    categories = {}
    for t in transactions:
        if t.type == "Expense":
            categories[t.category] = (
                categories.get(t.category,0)
                + t.amount
            )
    # TOP CATEGORY
    top_category = "No Data"
    if categories:
        top_category = max(
            categories,
            key=categories.get
        )
    # MONTHLY TREND CHART
    monthly_expense = {
        "Jan":0,
        "Feb":0,
        "Mar":0,
        "Apr":0,
        "May":0,
        "Jun":0,
        "Jul":0,
        "Aug":0,
        "Sep":0,
        "Oct":0,
        "Nov":0,
        "Dec":0
    }
    for t in transactions:
        if t.type == "Expense" and t.date.year == today.year:
            month = t.date.strftime("%b")
            monthly_expense[month] += t.amount
    # BUDGET (compared against TOTAL expense)
    budget = Budget.query.filter_by(
        user_id=current_user.id
    ).first()
    budget_amount = 0
    warning = False
    exceeded = False
    remaining = 0
    if budget:
        budget_amount = budget.amount
        remaining = budget_amount - expense
        if expense >= budget_amount:
            exceeded = True
        elif expense >= budget_amount * 0.9:
            warning = True
    # SAVINGS GOAL
    goal = SavingsGoal.query.filter_by(
        user_id=current_user.id
    ).first()
    progress = 0
    if goal and goal.target > 0:
        progress = int(
            (goal.saved / goal.target) * 100
        )
    # SMART SPENDING TIP
    spending_tip = ""
    if categories and expense > 0:
        top_amount = categories[top_category]
        top_share = (top_amount / expense) * 100
        if top_share >= 40:
            spending_tip = "Your " + top_category + " expenses are high this month. Try reducing " + top_category + " spending by 10%."
        else:
            spending_tip = "Your spending looks balanced across categories. Keep it up!"

    filtered_expenses = transactions

    if search:

        filtered_expenses = [

            t for t in filtered_expenses

            if search.lower() in t.title.lower()

        ]

    if selected_category and selected_category != "All":

        filtered_expenses = [

            t for t in filtered_expenses

            if t.category == selected_category

        ]

    filtered_expenses = sorted(

        filtered_expenses,

        key=lambda t: t.date,

        reverse=True

    )

    return render_template(
        "index.html",
        expenses=filtered_expenses,
        income=income,
        expense=expense,
        balance=balance,
        categories=categories,
        budget=budget_amount,
        warning=warning,
        exceeded=exceeded,
        remaining=remaining,
        month_expense=round(month_expense,2),
        average_expense=round(
            average_expense,
            2
        ),
        top_category=top_category,
        goal=goal,
        progress=progress,
        monthly_expense=monthly_expense,
        spending_tip=spending_tip,
        search=search,
        selected_category=selected_category
    )
# ADD
@app.route("/add",methods=["GET","POST"])
@login_required
def add_expense():
    if request.method=="POST":
        entry_date = request.form.get("date")
        if entry_date:
            entry_date = datetime.strptime(entry_date, "%Y-%m-%d")
        else:
            entry_date = datetime.now()
        data=Transaction(
            title=request.form["title"],
            amount=float(
                request.form["amount"]
            ),
            category=request.form["category"],
            type=request.form["type"],
            notes=request.form["notes"],
            date=entry_date,
            user_id=current_user.id
        )
        db.session.add(data)
        db.session.commit()
        return redirect("/")
    return render_template(
        "add_expense.html",
        today=date.today().isoformat()
    )
@app.route("/budget", methods=["GET","POST"])
@login_required
def budget():
    old_budget = Budget.query.filter_by(
        user_id=current_user.id
    ).first()
    if request.method=="POST":
        amount=float(
            request.form["amount"]
        )
        if old_budget:
            old_budget.amount = amount
        else:
            new_budget = Budget(
                amount=amount,
                user_id=current_user.id
            )
            db.session.add(new_budget)
        db.session.commit()
        return redirect("/")
    return render_template(
        "budget.html",
        budget=old_budget
    )
# DELETE
@app.route("/delete/<int:id>")
@login_required
def delete(id):
    transaction=Transaction.query.get_or_404(id)
    if transaction.user_id==current_user.id:
        db.session.delete(transaction)
        db.session.commit()
    return redirect("/")
# EDIT
@app.route("/edit/<int:id>", methods=["GET","POST"])
@login_required
def edit(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        return redirect("/")
    if request.method=="POST":
        entry_date = request.form.get("date")
        if entry_date:
            entry_date = datetime.strptime(entry_date, "%Y-%m-%d")
        else:
            entry_date = transaction.date
        transaction.title = request.form["title"]
        transaction.amount = float(
            request.form["amount"]
        )
        transaction.category = request.form["category"]
        transaction.type = request.form["type"]
        transaction.notes = request.form["notes"]
        transaction.date = entry_date
        db.session.commit()
        return redirect("/")
    return render_template(
        "edit_expense.html",
        transaction=transaction
    )
@app.route("/profile")
@login_required
def profile():
    return render_template(
        "profile.html",
        user=current_user
    )
@app.route("/savings", methods=["GET","POST"])
@login_required
def savings():
    old_goal = SavingsGoal.query.filter_by(
        user_id=current_user.id
    ).first()
    if request.method=="POST":
        action = request.form.get("action")
        if action == "topup" and old_goal:
            topup_amount = float(
                request.form["topup_amount"]
            )
            old_goal.saved += topup_amount
            db.session.commit()
            return redirect("/")
        goal_name=request.form["goal"]
        target=float(
            request.form["target"]
        )
        saved=float(
            request.form["saved"]
        )
        if old_goal:
            old_goal.goal=goal_name
            old_goal.target=target
            old_goal.saved=saved
        else:
            new_goal=SavingsGoal(
                goal=goal_name,
                target=target,
                saved=saved,
                user_id=current_user.id
            )
            db.session.add(new_goal)
        db.session.commit()
        return redirect("/")
    return render_template(
        "savings.html",
        goal=old_goal
    )
if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)