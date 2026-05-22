import os, logging
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
BASE_URL = "https://logus.gfsis.com.br"
store = {}

@app.route('/set-session', methods=['POST'])
def set_session():
    data = request.get_json()
    if not data or 'jsessionid' not in data:
        return jsonify({"success": False, "error": "jsessionid obrigatorio"}), 400
    store['jsessionid'] = data['jsessionid']
    logger.info("JSESSIONID armazenado")
    return jsonify({"success": True, "message": "Sessao armazenada"})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "autenticado": 'jsessionid' in store})

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"error": "url obrigatoria"}), 400

    cookies = {}
    if 'jsessionid' in store:
        cookies['JSESSIONID'] = store['jsessionid']
    else:
        return jsonify({"status": 0, "body": "sem sessao"})

    try:
        r = requests.get(BASE_URL + data['url'], cookies=cookies, timeout=30)
        return jsonify({"status": r.status_code, "body": r.text, "url": r.url})
    except Exception as e:
        return jsonify({"status": 0, "body": str(e)})

@app.route('/check-session', methods=['POST'])
def check_session():
    if 'jsessionid' not in store:
        return jsonify({"valida": False, "status_code": 0, "motivo": "nenhuma sessao armazenada"})

    try:
        r = requests.get(BASE_URL + "/gestaofacil/", cookies={'JSESSIONID': store['jsessionid']}, timeout=30)
        if 'btn-login' in r.text or 'ENTRAR' in r.text:
            return jsonify({"valida": False, "status_code": r.status_code, "motivo": "sessao expirada, precisa renovar"})
        return jsonify({"valida": True, "status_code": r.status_code, "motivo": "sessao valida"})
    except Exception as e:
        return jsonify({"valida": False, "status_code": 0, "motivo": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
