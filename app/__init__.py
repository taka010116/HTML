import os
from flask import Flask, request
from .routes import main
from flask_socketio import SocketIO, emit
from config import Config

socketio = SocketIO(cors_allowed_origins="*")

# ロビーごとの管理: { "password": [sid1, sid2, ...] }
waiting_rooms = {}

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    from app.routes import main
    app.register_blueprint(main)

    socketio.init_app(app)
    return app

app = create_app()

@socketio.on("join")
def handle_join(data):
    password = data.get("password")
    if not password:
        emit("login_result", {"status": "error"})
        return

    # 部屋がなければ作成
    if password not in waiting_rooms:
        waiting_rooms[password] = []

    waiting_rooms[password].append(request.sid)

    players = waiting_rooms[password]

    if len(players) == 1:
        # 1人目 → 待機
        emit("login_result", {"status": "waiting"})
    elif len(players) == 2:
        # 2人揃った → 接続完了
        for sid in players:
            emit("login_result", {"status": "ready"}, room=sid)
        broadcast_players(password)

def broadcast_players(password):
    players = waiting_rooms.get(password, [])
    emit("update_players", {"players": players}, room=password)

@socketio.on("disconnect")
def handle_disconnect():
    for pw, sids in list(waiting_rooms.items()):
        waiting_rooms[pw] = [s for s in sids if s != request.sid]
        if not waiting_rooms[pw]:
            del waiting_rooms[pw]

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
