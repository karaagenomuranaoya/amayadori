import eventlet
# 【重要】これが競合エラーを防ぐおまじないです（必ず一番上に！）
eventlet.monkey_patch()

import os
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

app = Flask(__name__)
# セキュリティキー（本番環境変数があれば使用）
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
socketio = SocketIO(app)

# --- 設定とグローバル変数 ---
API_KEY = os.getenv("OWM_API_KEY")
CITY_NAME = "Tokyo"
MAX_HISTORY = 100  # ログ保存数

# 会話ログ（メモリ保存）
chat_history = [] 

def is_raining_now():
    """
    天気を取得し、雨判定(True/False)と詳細を返す
    """
    if not API_KEY:
        return False, "APIキー未設定"

    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={API_KEY}&lang=ja&units=metric"
    
    try:
        response = requests.get(url)
        # 通信失敗時
        if response.status_code != 200:
            return False, f"通信エラー ({response.status_code})"

        data = response.json()
        weather_main = data["weather"][0]["main"]
        description = data["weather"][0]["description"]
        
        # 雨と判定する種類
        rain_conditions = ["Rain", "Drizzle", "Thunderstorm"]
        
        # ★本番用ロジック
        is_rain = weather_main in rain_conditions
        
        # ★テスト用：晴れでも強制的に開けたい場合はここを True にする
        is_rain = True 
        
        return is_rain, description

    except Exception as e:
        print(f"天気取得エラー: {e}")
        return False, "取得失敗"

@app.route('/')
def index():
    global chat_history
    is_open, weather_desc = is_raining_now()
    
    # 雨が止んでいたら（晴れなら）、ログを全消去してリセット
    if not is_open:
        if len(chat_history) > 0:
            chat_history = []
            print("☀ 雨が止んだため、ログを水に流しました。")
    
    return render_template('index.html', is_open=is_open, weather_desc=weather_desc)

# --- WebSocketイベント ---

@socketio.on('connect')
def handle_connect():
    """接続した人にだけ、過去ログを送る"""
    emit('load_history', chat_history)

@socketio.on('send_message')
def handle_message(data):
    """メッセージを受信・保存・配信"""
    global chat_history
    
    # リストに保存
    chat_history.append(data)
    
    # 古いログを捨てる（容量制限）
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0)
    
    # 全員に配信
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)