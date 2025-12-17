import os  # 追加
from dotenv import load_dotenv # 追加
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# .envファイルを読み込む（本番環境では無視されるのでエラーにならない）
load_dotenv()

app = Flask(__name__)
# SECRET_KEYも本番では環境変数にするのがベストですが、一旦このままでOK
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'secret!') 
socketio = SocketIO(app)

# --- 環境変数からキーを取得 ---
# 第2引数は、もし設定されていなかった時のエラー除け（Noneになる）
API_KEY = os.getenv("OWM_API_KEY") 

# APIキーがない場合の安全策（デバッグ用）
if not API_KEY:
    print("⚠ 警告: APIキーが設定されていません！")

CITY_NAME = "Tokyo"
URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY_NAME}&appid={API_KEY}&lang=ja&units=metric"

# ... (以下、is_raining_now関数やルーティングはそのまま) ...
def is_raining_now():
    """
    今、雨が降っているかを判定する関数
    Trueなら「雨（開店）」、Falseなら「晴れ（閉店）」を返す
    """
    try:
        response = requests.get(URL)
        data = response.json()
        weather_main = data["weather"][0]["main"]
        description = data["weather"][0]["description"]
        print(f"現在の天気: {weather_main} ({description})")

        # 雨判定 (Rain:雨, Drizzle:霧雨, Thunderstorm:雷雨)
        if weather_main in ["Rain", "Drizzle", "Thunderstorm"]:
            return True, description
        else:
            return True, description # 本番はここを False にする
            # ★テスト用：いま晴れてても強制的に開けたい場合はここを True に変える！

    except Exception as e:
        print("天気取得エラー:", e)
        return False, "不明" # エラー時はとりあえず閉じておく

# --- ページを開いた時の処理 ---
@app.route('/')
def index():
    # 天気をチェック！
    is_open, weather_desc = is_raining_now()
    
    # 画面（HTML）に「開店フラグ」と「天気の詳細」を渡す
    return render_template('index.html', is_open=is_open, weather_desc=weather_desc)

# --- チャット機能（さっきと同じ） ---
@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)