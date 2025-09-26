import os
from flask import Flask, request
from .routes import main
from flask_socketio import SocketIO, emit, join_room
from config import Config
import random

rooms = {}

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
    leader_sid = players[0]

    if len(players) == 1:
        # 1人目 → 待機
        emit("login_result", {"status": "waiting", "isLeader": True, "name": f"Player{len(players)}"})
    elif len(players) == 2:
        for i, sid in enumerate(players):
            is_leader = (sid == leader_sid)
            emit("login_result", {
                "status": "ready",
                "isLeader": is_leader,
                "name": f"Player{i+1}"
            }, room=sid)
        broadcast_players(password)

def broadcast_players(password):
    players = waiting_rooms.get(password, [])
    player_names = [f"Player{i+1}" for i in range(len(players))]
    emit("update_players", {"players": player_names}, to=players)

@socketio.on("start_game")
def handle_start(data):
    password = data.get("password")
    players = waiting_rooms.get(password, [])
    for sid in players:
        emit("game_start", {}, room=sid)

@socketio.on("disconnect")
def handle_disconnect():
    for pw, sids in list(waiting_rooms.items()):
        waiting_rooms[pw] = [s for s in sids if s != request.sid]
        if not waiting_rooms[pw]:
            del waiting_rooms[pw]

#game1
@socketio.on("start_round")
def handle_start_round(data):
    password = data.get("password")
    players = waiting_rooms.get(password, [])
    if not players:
        return

    # 親にだけカードを送る
    cards = random.sample(range(1, 10), 4)
    leader_sid = players[0]
    emit("show_cards_parent", {"cards": cards}, room=leader_sid)

@socketio.on("parent_choice")
def handle_parent_choice(data):
    password = data.get("password")
    players = waiting_rooms.get(password, [])
    if not players:
        return

    chosen = data.get("chosen", [])
    # 親の選んだカードを保存しておく
    if "round_data" not in waiting_rooms:
        waiting_rooms["round_data"] = {}
    waiting_rooms["round_data"][password] = {"parent_choice": chosen}

    # 子にカードを送る
    cards = data.get("cards", [])
    child_sid = players[1]
    emit("show_cards_child", {"cards": cards}, room=child_sid)

@socketio.on("child_choice")
def handle_child_choice(data):
    password = data.get("password")
    chosen = data.get("chosen", [])
    players = waiting_rooms.get(password, [])
    round_data = waiting_rooms.get("round_data", {}).get(password, {})

    parent_choice = round_data.get("parent_choice", [])
    # 採点
    score = 0
    for c in chosen:
        if c not in parent_choice:
            score += 1

    # 両者に結果を通知
    for sid in players:
        emit("round_result", {
            "parent_choice": parent_choice,
            "child_choice": chosen,
            "score_child": score
        }, room=sid)

@socketio.on("join_game")
def handle_join_game(data):
    password = data["password"]
    join_room(password)

    # 親がいなければこの人をリーダーに
    if password not in rooms:
        rooms[password] = {"leader": request.sid, "choices": {}}
        emit("role", {"isLeader": True})
    else:
        emit("role", {"isLeader": False})

# 親の選択
@socketio.on("parent_choice")
def handle_parent_choice(data):
    password = data["password"]
    cards = data["cards"]
    choice = data["choice"]

    room = rooms[password]
    room["cards"] = cards
    room["choices"]["parent"] = choice

    # 子にカードを送る
    emit("show_cards", {"cards": cards}, room=password, include_self=False)


# 子の選択
@socketio.on("child_choice")
def handle_child_choice(data):
    password = data["password"]
    choice = data["choice"]

    room = rooms[password]
    room["choices"]["child"] = choice

    if "parent" in room["choices"] and "child" in room["choices"]:
        parent = room["choices"]["parent"]
        child = room["choices"]["child"]
        score = sum(c for c in child if c not in parent)

        emit("game_result", {"parent": parent, "child": child, "score": score}, room=password)
        room["choices"] = {}


@socketio.on("cards_generated")
def handle_cards(data):
    password = data["password"]
    cards = data["cards"]
    emit("show_cards", {"cards": cards}, room=password)

@socketio.on("submit_choice")
def handle_choice(data):
    password = data["password"]
    choice = data["choice"]
    room = rooms[password]
    role = "parent" if request.sid == room["leader"] else "child"
    room["choices"][role] = choice

    # 両方揃ったら結果判定
    if "parent" in room["choices"] and "child" in room["choices"]:
        parent = room["choices"]["parent"]
        child = room["choices"]["child"]
        # スコア計算
        score = sum(c for c in child if c not in parent)
        emit("game_result", {"parent": parent, "child": child, "score": score}, room=password)
        room["choices"] = {}

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
