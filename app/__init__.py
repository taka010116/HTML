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
        emit("login_result", {"status": "error"}, room=request.sid)
        return

    # waiting_rooms に追加
    if password not in waiting_rooms:
        waiting_rooms[password] = []
    waiting_rooms[password].append(request.sid)

    # rooms にも部屋情報を作成
    if password not in rooms:
        rooms[password] = {
            "in_progress": False,
            "choices": {},
            "players": []
        }

    if request.sid not in rooms[password]["players"]:
        rooms[password]["players"].append(request.sid)
    
    join_room(password)

    #players = waiting_rooms[password]
    players = rooms[password]["players"]
    leader_sid = players[0]

    for sid in players:
        is_leader = (sid == leader_sid)
        emit("login_result", {"status": "ready", "isLeader": is_leader}, room=sid)

    # プレイヤーリスト更新
    emit("update_players", {"players": players}, room=password)

"""
    if len(players) == 1:
        emit("login_result", {"status": "waiting", "isLeader": True, "name": f"Player{len(players)}"}, room=request.sid)
    else:
        for i, sid in enumerate(players):
            is_leader = (sid == leader_sid)
            emit("login_result", {
                "status": "ready",
                "isLeader": is_leader,
                "name": f"Player{i+1}"
            }, room=sid)
        broadcast_players(password)

"""

def broadcast_players(password):
    players = rooms[password]["players"]
    player_names = [f"Player{i+1}" for i in range(len(players))]
    emit("update_players", {"players": player_names}, room=password)

#最初
@socketio.on("start_game")
def handle_start(data):
    password = data.get("password")
    room = rooms.get(password)
    if not password:
        emit("error", {"message": "パスワードが指定されていません"}, room=request.sid)
        return
    
    if not room:
        emit("error", {"message": "この部屋は存在しません"}, room=request.sid)
        return
    
    if room.get("in_progress"):
        emit("error", {"message": "ゲームは既に進行中です"}, room=request.sid)
        return
    if room["in_progress"]:
        emit("error", {"message": "ゲームは既に進行中です"}, room=request.sid)
        return

    room["in_progress"] = True  # このゲームは進行中
    #players = waiting_rooms.get(password, [])
    #if players:
    room["choices"] = {}
    emit("game_start", {}, room=password)
    print("game Start!")

#終わり
@socketio.on("end_round")
def handle_end_round(data):
    password = data.get("password")
    room = rooms.get(password)
    if room:
        room["in_progress"] = False
        room["choices"] = {}

"""
@socketio.on("disconnect")
def handle_disconnect():
    for pw, sids in list(waiting_rooms.items()):
        # SID を除外
        waiting_rooms[pw] = [s for s in sids if s != request.sid]

        # もしルームが空になったら削除＆進行中フラグクリア
        if not waiting_rooms[pw]:
            del waiting_rooms[pw]

            if pw in rooms:
                room = rooms[pw]
                room["in_progress"] = False
                room["choices"] = {}
"""

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    for password, room in list(rooms.items()):
        if "players" in room and sid in room["players"]:
            room["players"].remove(sid)
            emit("update_players", {"players": room["players"]}, room=password)
            if not room["players"]:
                del rooms[password]


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

#親がカードを選んだ→
@socketio.on("parent_choice")
def handle_parent_choice(data):
    password = data.get("password")
    players = waiting_rooms.get(password, [])
    #if not players:
    #    return
    if len(players) < 2:
        print("受信したが、子が未参加")
        return

    chosen = data.get("chosen", [])
    # 親の選んだカードを保存しておく
    if "round_data" not in waiting_rooms:
        waiting_rooms["round_data"] = {}
    waiting_rooms["round_data"][password] = {"parent_choice": chosen}

    print("親の選択")
    # 子にカードを送る
    cards = data.get("cards", [])
    parent_sid = players[0]
    #emit("hide_cards", {}, room=parent_sid)
    child_sid = players[1]
    emit("show_cards", {"cards": cards, "parent_choice" : chosen}, room=child_sid)
    print("カード送信OK")

@socketio.on("child_choice")
def handle_child_choice(data):
    password = data.get("password")
    chosen = data.get("chosen", [])
    players = waiting_rooms.get(password, [])

    if len(players) < 2:
        print("プレイヤー不足child_choice")
        return 

    round_data = waiting_rooms.get("round_data", {}).get(password, {})
    parent_choice = round_data.get("parent_choice", [])

    # 採点：子のカード合計、ただし親が選んだカードは無効
    #score = sum(int(c) for c in chosen if c not in map(int, parent_choice))

    parent_set = set(map(int, parent_choice))

    score = 0
    for c in chosen:
        c_int = int(c)
        if c_int not in parent_set:
            score += c_int

    # 両者に結果を通知
    result = {
        "parent_choice": parent_choice,
        "child_choice": chosen,
        "score_child": score
    }
    for sid in players:
        emit("round_result", result, room=sid)
    #test
    print(f"[DEBUG] 結果送信 parent={parent_choice}, child={chosen}, score={score} (room={password})")


@socketio.on("join_game")
def handle_join_game(data):
    password = data["password"]
    sid = request.sid
    join_room(password)

    if password not in waiting_rooms:
        waiting_rooms[password] = []
    waiting_rooms[password].append(sid)

    # 親がいなければこの人を親にする
    if password not in rooms:
        rooms[password] = {
            "leader": sid,    # 親
            "child": None,    # 子（初期化しておく）
            "choices": {}
        }
        emit("role", {"role": "parent", "isLeader": True}, room=sid)
    else:
        room = rooms[password]
        if room["child"] is None:
            # 子として登録
            room["child"] = sid
            emit("role", {"role": "child", "isLeader": False}, room=sid)
        else:
            # すでに親と子が揃っている → 満員
            emit("error", {"message": "この部屋はすでに満員です"}, room=sid)

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
