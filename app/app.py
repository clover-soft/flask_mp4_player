import os
from flask import Flask, render_template, Response, abort, request, abort
import logging
from logging.handlers import RotatingFileHandler
from settings import Settings
app = Flask(__name__, static_folder='/video')
Settings.load_config()
handler = RotatingFileHandler(
    '/var/log/backend.log', maxBytes=200*1024*1024, backupCount=10)
formatter = logging.Formatter('[%(asctime)s][%(name)s] => %(message)s')
handler.setFormatter(formatter)
logging.basicConfig(handlers=[handler], level=logging.INFO)
logger = logging.getLogger('backend app')
logger.info("Start backend worker...")


def checkAccess():
    if request.method != 'GET':
        abort(403, "Access denied")
    if request.args.get('key') != Settings.get_config_param('key'):
        abort(403, "Access denied")


@app.route('/playlist/<string:playlist>', methods=['GET'])
def playlist(playlist):
    checkAccess()
    folders_dict = dict(Settings.get_config_param('folders'))
    target_path = None
    logger.info("playlist: " + playlist)
    logger.info(folders_dict)
    for folder in folders_dict:
        if folder["name"] == playlist:
            target_path = folder["path"]
    if target_path is None:
        abort(403, "Access denied")
    mp4_list = get_mp4_files(target_path)
    logger.info(mp4_list)
    host = request.host
    replace_hosts = Settings.get_config_param('replace_hosts')
    for replace_host in replace_hosts:
        if host == replace_host["from"]:
            host = replace_host["to"]
    return render_template('playlist.html', mp4_list=mp4_list, host=host, key=request.args.get('key'), playlist=playlist)


@app.route('/get_media/<string:filename>')
def playvideo(filename):
    checkAccess()
    folders_dict = dict(Settings.get_config_param('folders'))
    playlist = request.args.get('playlist')
    target_path = None
    for folder in folders_dict:
        if folder["name"] == playlist:
            target_path = folder["path"]
    if target_path is None:
        abort(403, "Access denied")
    return render_template('videoplayer.html', mp4_file=filename, playlist=playlist)


def video(filename,playlist):
    folders_dict = dict(Settings.get_config_param('folders'))
    target_path = None
    for folder in folders_dict:
        if folder["name"] == playlist:
            target_path = folder["path"]
    if target_path is None:
        abort(403, "Access denied")
    video_path = f'{target_path}/{filename}'  # Путь к видеофайлу
    range_header = request.headers.get('Range')
    file_size = os.path.getsize(video_path)
    if range_header:
        ranges = range_header.replace('bytes=', '').split('-')
        start_range = int(ranges[0]) if ranges[0] else 0
        end_range = int(ranges[1]) if ranges[1] else file_size - 1
        if end_range == 1:
            end_range = file_size - 1
        logger.info(f'start_range: {start_range} end_range: {end_range}')

        def gen_range():
            with open(video_path, 'rb') as video_file:
                video_file.seek(start_range)
                remaining_bytes = end_range - start_range + 1
                while remaining_bytes > 0:
                    chunk_size = min(remaining_bytes, 1048576)
                    video_data = video_file.read(chunk_size)
                    yield video_data
                    remaining_bytes -= chunk_size
        response = Response(gen_range(), status=206,
                            mimetype='video/mp4', direct_passthrough=True)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Range'] = f'bytes {start_range}-{end_range}/{file_size}'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Size'] = 1048576
        return response
    else:
        def gen():
            with open(video_path, 'rb') as video_file:
                while True:
                    video_data = video_file.read(1048576)
                    if not video_data:
                        break
                    yield video_data
        response = Response(gen(), mimetype='video/mp4')
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Length'] = str(file_size)
        return response


def get_mp4_files(directory):
    mp4_files = []
    for file in os.listdir(directory):
        if file.endswith('.mp4'):
            mp4_files.append(file)
    return sorted(mp4_files)

# Обработчик для неопределенных маршрутов


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def unqnown_request(path):
    abort(403, "Access denied")


if __name__ == '__main__':
    app.run()
