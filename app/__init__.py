import os
from flask import Flask
from .routes import main
from flask_socketio import SocketIO
from config import Config

#socketio = SocketIO(cors_allowed_origins="*")
socketio = SocketIO()

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    from app.routes import main
    app.register_blueprint(main)

    socketio.init_app(app)

    @socketio.on("message")
    def handle_message(data):
        print("受信:", data)
        socketio.emit("message", {"msg": f"サーバーが受け取った: {data}"}, broadcast=True)
    return app

app = create_app()

if __name__ == "__main__":
    #app.run()
    socketio.run(app)
