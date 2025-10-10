from flask import Blueprint, redirect, url_for, Flask, jsonify, render_template, flash, render_template_string, request,g, session
#from flask_socketio import emit
#from app import socketio
app = Flask(__name__)
#main = Blueprint('main', __name__)
main = Blueprint("main", __name__, template_folder="templates")

@main.route('/')
def index():
    
    return render_template('index.html')

@main.route("/game")
def game():
    return render_template("game.html")

@main.route("/game1")
def game1():
    return render_template("game1.html")

@main.route("/register")
def register():
    return render_template("register.html")

@main.route("/login")
def login():
    return render_template("login.html")

@main.route("/account")
def account():
    return render_template("account.html")

@main.route("/archive")
def archive():
    return render_template("archive.html")

app.register_blueprint(main)

if __name__ == "__main__":
    app.run(debug=True)

"""
@socketio.on("message")
def handle_message(data):
    print("受信:", data)
    emit("message", {"msg": f"サーバーが受け取った: {data}"}, broadcast=True)
"""