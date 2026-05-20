import os, logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))
USERNAME = os.environ.get('USERNAME', 'gustavo')
SENHA = os.environ.get('SENHA', 'Guga1234')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE = 'https://logus.gfsis.com.br'
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9',
})

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'autenticado': 'JSESSIONID' in session.cookies,
        'cookies': list(session.cookies.keys())
    })

@app.route('/login', methods=['POST'])
def login():
    try:
        # Passo 1: GET da página de login
        r1 = session.get(f'{BASE}/gestaofacil/login/Index', timeout=30)
        logger.info(f'GET: status={r1.status_code} url={r1.url}')
        logger.info(f'Cookies: {dict(session.cookies)}')
        logger.info(f'Response preview: {r1.text[:300]}')

        # Passo 2: POST login
        r2 = session.post(
            f'{BASE}/gestaofacil/login/neo_security_manager',
            data={'username': USERNAME, 'password': SENHA},
            headers={
                'Referer': f'{BASE}/gestaofacil/login/Index',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=30,
            allow_redirects=True
        )
        logger.info(f'POST: status={r2.status_code} url={r2.url}')
        logger.info(f'Cookies pos: {dict(session.cookies)}')
        logger.info(f'Response: {r2.text[:300]}')

        # Passo 3: verifica se logou
        r3 = session.get(f'{BASE}/gestaofacil/', timeout=30, allow_redirects=True)
        logger.info(f'HOME: status={r3.status_code} url={r3.url}')

        if 'login' not in r3.url.lower():
            return jsonify({'success': True, 'url': r3.url})

        # Se falhou, retorna debug completo
        return jsonify({
            'error': 'Login falhou',
            'debug': {
                'status_get': r1.status_code,
                'url_get': r1.url,
                'status_post': r2.status_code,
                'url_post': r2.url,
                'status_home': r3.status_code,
                'url_home': r3.url,
                'cookies': {k: str(v)[:30] for k, v in session.cookies.items()},
                'response_get_preview': r1.text[:500],
                'response_post_preview': r2.text[:500]
            }
        }), 502

    except Exception as e:
        logger.error(f'Erro: {e}')
        return jsonify({'error': str(e)}), 502

@app.route('/fetch', methods=['POST'])
def fetch():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'url obrigatória'}), 400
    if 'JSESSIONID' not in session.cookies:
        return jsonify({'error': 'Não autenticado. Execute /login primeiro.'}), 401
    try:
        r = session.get(data['url'], timeout=30, allow_redirects=True)
        return jsonify({'status': r.status_code, 'body': r.text, 'url': r.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
