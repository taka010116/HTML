import os
from flask import Flask
from .routes import main
from flask_socketio import SocketIO
from config import Config
from app import socketio

#socketio = SocketIO(cors_allowed_origins="*")
#socketio = SocketIO()
socketio = SocketIO(cors_allowed_origins="*")

LOBBY_PASSWORD = "あいことば"
players = []

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    from app.routes import main
    app.register_blueprint(main)

    socketio.init_app(app)
    
    return app

app = create_app()
@socketio.on("message")
def handle_message(data):
    print("受信:", data)
    socketio.emit("message", {"msg": data}, broadcast=True)

@socketio.on("join")
def handle_join(data):
    password == data.get("password")
    if password == LOBBY_PASSWORD:
        player_name = f"Player{len(players)+1}"
        players.append(player_name)
        emit("login_result", {"success": True, "name": player_name})
        broadcast_players()
    else:
        emit("login_result", {"success": False})

def broadcast_players():
    emit("update_players", {"players": players}, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    # 今の簡易版ではプレイヤー名を管理できないので未実装
    pass

if __name__ == "__main__":
    #app.run()
    #socketio.run(app)
    socketio.run(app, host="0.0.0.0", port=5000)
