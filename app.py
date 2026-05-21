import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
jsessionid = None

@app.route('/set-session', methods=['POST'])
def set_session():
    global jsessionid
    data = request.get_json()
    if not data or 'jsessionid' not in data:
        return jsonify({'error': 'Campo jsessionid é obrigatório'}), 400
    jsessionid = data['jsessionid']
    app.logger.info('JSESSIONID atualizado com sucesso')
    return jsonify({'message': 'JSESSIONID salvo com sucesso'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'autenticado': jsessionid is not None}), 200

@app.route('/fetch', methods=['POST'])
def fetch():
    global jsessionid
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Campo url é obrigatório'}), 400

    url = data['url']
    if not url.startswith('/'):
        url = '/' + url

    target_url = f'https://logus.gfsis.com.br{url}'
    cookies = {}
    if jsessionid:
        cookies['JSESSIONID'] = jsessionid

    try:
        response = requests.get(target_url, cookies=cookies, timeout=30)
        return jsonify({
            'status': response.status_code,
            'body': response.text,
            'url': response.url
        }), 200
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Erro na requisição', 'details': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
