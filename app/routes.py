from flask import Blueprint, redirect, url_for, Flask, jsonify, render_template, flash, render_template_string, request,g, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
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


#ここから下データベース
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, generate_password_hash(password)))
            conn.commit()
            flash("登録が完了しました！ログインしてください。")
            return redirect(url_for("main.login"))
        except:
            flash("このユーザー名はすでに使われています。")
        finally:
            conn.close()
    return render_template("register.html")

@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("ログイン成功！")
            return redirect(url_for("main.account"))
        else:
            flash("ユーザー名またはパスワードが間違っています。")
    return render_template("login.html")

@main.route("/account")
def account():
    if "user_id" not in session:
        flash("ログインしてください。")
        return redirect(url_for("main.login"))
    return render_template("account.html", username=session["username"])

@main.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。")
    return redirect(url_for("main.login"))

@main.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("main.login"))
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (session["user_id"],))
    conn.commit()
    conn.close()
    session.clear()
    flash("アカウントを削除しました。")
    return redirect(url_for("main.register"))

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