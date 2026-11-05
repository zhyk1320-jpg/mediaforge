import os
import shutil
import tempfile

import yt_dlp
from flask import Flask, jsonify, render_template, request, send_file

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(base_dir, 'templates'))


def find_ffmpeg_dir():
    """Если рядом с app.py лежит ffmpeg.exe — используем его, иначе берём системный ffmpeg."""
    if os.path.exists(os.path.join(base_dir, 'ffmpeg.exe')):
        return base_dir
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get('url') or '').strip()

    if not url:
        return jsonify({'error': 'Не указана ссылка'}), 400

    temp_dir = tempfile.mkdtemp()

    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title).150B.%(ext)s'),
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'socket_timeout': 30,
        'quiet': True,
        'no_warnings': True,
    }

    ffmpeg_dir = find_ffmpeg_dir()
    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        # после слияния расширение может стать .mp4
        if not file_path.endswith('.mp4'):
            candidate = os.path.splitext(file_path)[0] + '.mp4'
            if os.path.exists(candidate):
                file_path = candidate

        title = info.get('title') or 'MediaForge_Video'
        ext = os.path.splitext(file_path)[1] or '.mp4'

        response = send_file(file_path, as_attachment=True, download_name=f'{title}{ext}')

        # удаляем временную папку после отправки файла
        response.call_on_close(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        return response

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'ok', 200

if __name__ == '__main__':
    try:
        print("Сервер запущен! Открой в браузере: http://127.0.0.1:5000")
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        input("Нажми Enter для выхода...")
