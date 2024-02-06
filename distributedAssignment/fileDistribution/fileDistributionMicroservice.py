import os
import hashlib
import sys
from flask import Flask, send_file, make_response, jsonify

app = Flask(__name__)

@app.route('/download_song/<song>', methods=['GET'])
def download_song(song):
    print()
    print(f"Client connected and requested to download: {song}")
    current_location = os.path.dirname(os.path.abspath(__file__))
    song_location = f"./music/{song}"
    song_to_send = os.path.join(current_location, song_location)

    if not os.path.exists(song_to_send):
        return "File not found", 404

    md5_checksum = hashlib.md5()
    with open(song_to_send, 'rb') as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            md5_checksum.update(byte_block)
    print(f"Generated MD5 checksum: {md5_checksum.hexdigest()}")
    response = make_response(send_file(
        song_to_send,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=song
    ))
    response.headers['MD5-Checksum'] = md5_checksum.hexdigest()
    print(f"{song} successfully sent to user")
    return response

@app.route('/get_music_to_download', methods=['GET'])
def get_music_to_download():
    print()
    print(f"Client connected, requested audio list")
    current_location = os.path.dirname(os.path.abspath(__file__))
    music_location = f"./music"
    music_music_location = os.path.join(current_location, music_location)
    music_to_send = [file for file in os.listdir(music_music_location) if file.endswith(('.mp3', '.wav', '.ogg'))]
    return jsonify({'music_titles': music_to_send})

if __name__ == '__main__':
    ip = 'localhost'
    port = 50007
    if len(sys.argv) > 2:
        ip = sys.argv[1]
        port = int(sys.argv[2])
    app.run(host=ip, port=port, debug=True)
