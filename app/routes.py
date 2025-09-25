from flask import Blueprint, redirect, url_for, Flask, jsonify, render_template, flash, render_template_string, request,g, session
#from flask_socketio import emit
#from app import socketio

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


"""
@socketio.on("message")
def handle_message(data):
    print("受信:", data)
    emit("message", {"msg": f"サーバーが受け取った: {data}"}, broadcast=True)
"""