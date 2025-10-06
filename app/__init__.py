import os
from flask import Flask, request
from .routes import main
from flask_socketio import SocketIO, emit, join_room
from config import Config
import random, string

rooms = {}

socketio = SocketIO(cors_allowed_origins="*")

room_players = {}
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

def broadcast_players(password):
    players = rooms[password]["players"]
    player_names = [f"Player{i+1}" for i in range(len(players))]
    emit("update_players", {"players": player_names}, room=password)

#最初
@socketio.on("start_game")
def handle_start(data):
    password = data.get("password")
    print("パスワード")
    print(password)
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
    room = rooms.get(password)
    if not room or not room.get("child"):
        print("親の選択を受信したが子がいない")
        return

    chosen = data.get("chosen", [])
    cards = data.get("cards", [])

    # 部屋ごとの round_data に保存
    room["round_data"] = {"parent_choice": chosen}

    parent_sid = room["leader"]
    child_sid = room["child"]

    # 子にカードを送信
    emit("show_cards", {"cards": cards, "parent_choice": chosen}, room=child_sid)
    print(f"[DEBUG] 親の選択を保存 room={password}, chosen={chosen}")

@socketio.on("child_choice")
def handle_child_choice(data):
    password = data.get("password")
    room = rooms.get(password)
    if not room:
        return

    chosen = data.get("chosen", [])
    parent_choice = room.get("round_data", {}).get("parent_choice", [])

    parent_set = set(map(int, parent_choice))
    score = sum(int(c) for c in chosen if int(c) not in parent_set)

    result = {
        "parent_choice": parent_choice,
        "child_choice": chosen,
        "score_child": score
    }

    # 部屋内の全員に結果送信
    for sid in room["players"]:
        emit("round_result", result, room=sid)

    print(f"[DEBUG] 結果送信 room={password}, parent={parent_choice}, child={chosen}, score={score}")

def generate_room_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

@socketio.on("join_game")
def handle_join_game(data):
    sid = request.sid
    password = data.get("password")  # ロビーで入力された合言葉
    print("join_gameで受け取ったパスワード:", password)

    if not password:
        emit("error", {"message": "パスワードが必要です"}, room=sid)
        return
    
    # 部屋がなければ作成
    if password not in rooms:
        rooms[password] = {"leader": None, "child": None}
        print(f"[DEBUG] 新しい部屋作成: {password}")

    room = rooms[password]

    # すでに親か子に参加済みならエラー
    if sid in (room.get("leader"), room.get("child")):
        emit("error", {"message": "すでにこの部屋に参加しています"}, room=sid)
        return

    # 親が空いていれば防衛
    if room["leader"] is None:
        room["leader"] = sid
        join_room(password)
        emit("role", {"role": "parent", "isLeader": True, "room_id": password}, room=sid)
        print(f"[DEBUG] 親(防衛)が参加: room={password}, leader={sid}")

    # 子が空いていれば攻撃
    elif room["child"] is None:
        room["child"] = sid
        join_room(password)
        emit("role", {"role": "child", "isLeader": False, "room_id": password}, room=sid)
        print(f"[DEBUG] 子(攻撃)が参加: room={password}, child={sid}")

    else:
        # 親子揃っている → 満員
        emit("error", {"message": "この部屋は満員です"}, room=sid)
        print(f"[DEBUG] 満員で拒否: room={password}, sid={sid}")


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
