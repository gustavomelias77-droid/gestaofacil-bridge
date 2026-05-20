import os, logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))
USERNAME = os.environ.get('USERNAME', 'teste2')
SENHA = os.environ.get('SENHA', '654321')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = 'https://logus.gfsis.com.br'
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'session_alive': bool(session.cookies.get('JSESSIONID'))})

@app.route('/login', methods=['POST'])
def login():
    try:
        # Passo 1: acessar página de login para capturar cookies
        r = session.get(f'{BASE}/gestaofacil/login/Index', timeout=30)
        logger.info(f'GET login: status={r.status_code}, cookies={len(session.cookies)}')
        
        # Passo 2: POST para autenticação
        r2 = session.post(
            f'{BASE}/gestaofacil/login/neo_security_manager',
            data={'username': USERNAME, 'password': SENHA},
            timeout=30
        )
        logger.info(f'POST login: status={r2.status_code}, url={r2.url}')
        
        # Passo 3: acessar home pra ver se logou
        r3 = session.get(f'{BASE}/gestaofacil/', timeout=30, allow_redirects=True)
        logger.info(f'GET home: status={r3.status_code}, url={r3.url}')
        
        if 'login' not in r3.url.lower():
            return jsonify({'success': True, 'url': r3.url})
        
        return jsonify({'error': 'Login falhou', 'url_final': r3.url, 'status': r3.status_code}), 502
        
    except Exception as e:
        logger.error(f'Erro: {e}')
        return jsonify({'error': str(e)}), 502

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatória'}), 400
    
    jid = session.cookies.get('JSESSIONID')
    if not jid:
        return jsonify({'error': 'Não autenticado. Execute /login primeiro.'}), 401
    
    try:
        r = session.get(data['url'], timeout=30, allow_redirects=True)
        return jsonify({
            'status': r.status_code,
            'body': r.text,
            'url': r.url
        })
    except Exception as e:
        logger.error(f'Erro fetch: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
