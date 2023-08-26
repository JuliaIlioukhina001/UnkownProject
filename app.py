from accounts import *
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
import os

load_dotenv()

# Set the environment variables
app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login a user. If the user is successfully logged we redirect them to the main page.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username and password:
            try:
                user_data = login_user(username, password)
                if user_data:
                    session["username"] = user_data["username"]
                    session["wallet_id"] = user_data["wallet_id"]
                    session["address"] = user_data["address"]
                    return redirect(url_for("index"))
                else:
                    return render_template("login.html", error="Invalid username or password.")
            except Exception as e:
                print(f"Error logging in user: {e}")
                return render_template("login.html", error="Error logging in user.")
        else:
            return render_template("login.html", error="Please fill out all fields.")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Logout a user.
    """
    if "username" not in session:
        return redirect(url_for("login"))
    session.clear()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Register a user. If the user is successfully registered we redirect them to the main page.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if check_username(username):
            return render_template("register.html", error="Username already exists.")
        else:
            if username and password:
                try:
                    user_data = create_wallet(username, password)
                    add_goals(username, 5)
                    if user_data:
                        session["username"] = user_data["username"]
                        session["wallet_id"] = user_data["wallet_id"]
                        session["address"] = user_data["address"]
                        return redirect(url_for("index"))
                    else:
                        return render_template("register.html", error="Error registering user.")
                except Exception as e:
                    print(f"Error registering user: {e}")
                    return render_template("register.html", error="Error registering user.")
            else:
                return render_template("register.html", error="Please fill out all fields.")
    else:
        return render_template("register.html")


@app.route("/")
def index():
    """
    The main page of the application. If the user is not logged in we redirect them to the login page.
    """
    if "username" in session:
        return render_template("index.html", username=session["username"], wallet_id=session["wallet_id"],
                               address=session["address"])
    else:
        return redirect(url_for("login"))


@app.route("/complete", methods=["GET", "POST"])
def complete():
    """
    The endpoint for completing a goal. If the user is not logged in we redirect them to the login page.
    """
    if "username" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        image = request.form.get("image")
        username = session["username"]
        goal_name = request.form.get("goal_name")
        if complete_goal(username, goal_name, image):
            return redirect(url_for("congrats"))
        else:
            return render_template("index.html", error="Error completing goal.")
    else:
        return render_template("index.html")

@app.route("/balance")
def balance():
    """
    Get the balance of a wallet of the user. If the user is not logged in we redirect them to the login page.
    """
    if "username" not in session:
        return redirect(url_for("login"))
    try:
        balance = get_balance(session["wallet_id"])
        return render_template("balance.html", balance=balance)
    except Exception as e:
        print(f"Error getting balance: {e}")
        return render_template("balance.html", error="Error getting balance.")

@app.route("/goals")
def goals():
    """
    Get the goals of the user. If the user is not logged in we redirect them to the login page. Uses forms for each goal to allow the user to complete them as long as they upload a photo along with it,
    """
    if "username" not in session:
        return redirect(url_for("login"))
    try:
        goals = get_goals(session["username"])
        return render_template("goals.html", goals=goals)
    except Exception as e:
        print(f"Error getting goals: {e}")
        return render_template("goals.html", error="Error getting goals.")


@app.route("/complete_goal", methods=["POST"])
def complete_goal():
    if "username" not in session:
        return redirect(url_for("login"))

    goal_name = request.form.get("goal_name")
    image = request.files.get("image")

    if not goal_name or not image:
        return render_template("goals.html", error="Please provide goal name and image.")

    try:
        success = complete_goal(session["username"], goal_name,
                                image)  # Replace with your function to complete the goal
        if success:
            return redirect(url_for("goals"))
        else:
            return render_template("goals.html", error="Error completing goal.")
    except Exception as e:
        print(f"Error completing goal: {e}")
        return render_template("goals.html", error="Error completing goal.")


if __name__ == "__main__":
    app.run(debug=True)
