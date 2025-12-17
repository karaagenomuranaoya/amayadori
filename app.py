import os
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

app = Flask(__name__)
# セキュリティキー（本番では環境変数推奨、なければデフォルト値）
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
socketio = SocketIO(app)

# --- 設定とグローバル変数 ---
API_KEY = os.getenv("OWM_API_KEY")
CITY_NAME = "Tokyo"
MAX_HISTORY = 100  # 保存するログの最大数

# 会話ログを保存するリスト（メモリ内保存）
chat_history = [] 

def is_raining_now():
    # 1. まずAPIキーが届いているか確認
    if not API_KEY:
        return False, "⚠️ 環境変数 OWM_API_KEY が読み込めていません！"

    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={API_KEY}&lang=ja&units=metric"
    
    try:
        response = requests.get(url)
        
        # 2. ステータスコードが200（成功）以外ならエラーを表示
        if response.status_code != 200:
            return False, f"API通信エラー: {response.status_code} / {response.text}"

        data = response.json()
        weather_main = data["weather"][0]["main"]
        description = data["weather"][0]["description"]
        
        rain_conditions = ["Rain", "Drizzle", "Thunderstorm"]
        is_rain = weather_main in rain_conditions
        
        return is_rain, description

    except Exception as e:
        # 3. Python内部エラーを表示（ここが重要）
        # APIキーの一部を表示して、正しいキーか確認する（セキュリティ注意：あとで消す）
        key_preview = API_KEY[:4] + "***" if API_KEY else "None"
        return False, f"システムエラー: {e} (Key: {key_preview})"

@app.route('/')
def index():
    global chat_history
    is_open, weather_desc = is_raining_now()
    
    # 【重要】もし雨が降っていなければ、ログを水に流す（全消去）
    if not is_open:
        if len(chat_history) > 0:
            print("☀ 雨が止んだため、ログを消去しました。")
            chat_history = []
    
    return render_template('index.html', is_open=is_open, weather_desc=weather_desc)

# --- WebSocketイベント ---

@socketio.on('connect')
def handle_connect():
    """ユーザーが接続した時に、過去ログを送る"""
    emit('load_history', chat_history)

@socketio.on('send_message')
def handle_message(data):
    """メッセージを受信した時の処理"""
    global chat_history
    
    # 1. サーバーのリストに保存
    chat_history.append(data)
    
    # 2. リストが長すぎたら古いものを捨てる（容量制限）
    if len(chat_history) > MAX_HISTORY:
        chat_history.pop(0) # 先頭（一番古いもの）を削除
    
    # 3. 全員に配信
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    # ローカル開発用
    socketio.run(app, debug=True, port=5000)