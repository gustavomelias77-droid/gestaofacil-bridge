import os, logging, json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))
USERNAME = os.environ.get('USERNAME', 'TESTE2')
SENHA = os.environ.get('SENHA', '654321')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = 'https://logus.gfsis.com.br'
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'session_alive': bool(session.cookies.get('JSESSIONID'))})

@app.route('/login', methods=['POST'])
def login():
    try:
        # Passo 1: GET da página de login
        r1 = session.get(f'{BASE}/gestaofacil/login/Index', timeout=30)
        logger.info(f'GET login: status={r1.status_code}, cookies={dict(session.cookies)}')

        # Extrai campos ocultos do formulário
        hidden = {}
        import re
        for match in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', r1.text, re.I):
            name = re.search(r'name=["\']([^"\']+)["\']', match.group())
            value = re.search(r'value=["\']([^"\']*)["\']', match.group())
            n = name.group(1) if name else None
            v = value.group(1) if value else ''
            if n:
                hidden[n] = v

        logger.info(f'Campos ocultos: {hidden}')

        # Prepara dados do form
        form_data = {'username': USERNAME, 'password': SENHA}
        form_data.update(hidden)

        # Passo 2: POST para autenticação - tentativa 1 (form-urlencoded)
        r2 = session.post(
            f'{BASE}/gestaofacil/login/neo_security_manager',
            data=form_data,
            headers={'Referer': f'{BASE}/gestaofacil/login/Index',
                     'Origin': BASE},
            timeout=30,
            allow_redirects=True
        )
        logger.info(f'POST login: status={r2.status_code}, url={r2.url}, cookies={dict(session.cookies)}')

        # Passo 3: verificar se logou
        r3 = session.get(f'{BASE}/gestaofacil/', timeout=30, allow_redirects=True)
        logger.info(f'GET home: status={r3.status_code}, url={r3.url}')

        if 'login' not in r3.url.lower():
            return jsonify({'success': True, 'url': r3.url})

        # Passo 4: tentativa 2 - submit com Content-Type diferente
        r4 = session.post(
            f'{BASE}/gestaofacil/login/neo_security_manager',
            data=form_data,
            headers={
                'Referer': f'{BASE}/gestaofacil/login/Index',
                'Origin': BASE,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            timeout=30,
            allow_redirects=True
        )
        logger.info(f'POST login (tentativa 2): status={r4.status_code}, url={r4.url}')

        r5 = session.get(f'{BASE}/gestaofacil/', timeout=30, allow_redirects=True)
        logger.info(f'GET home (tentativa 2): status={r5.status_code}, url={r5.url}')

        if 'login' not in r5.url.lower():
            return jsonify({'success': True, 'url': r5.url, 'tentativa': 2})

        return jsonify({
            'error': 'Login falhou',
            'debug': {
                'status_get_login': r1.status_code,
                'status_post': r2.status_code,
                'url_pos_post': r2.url,
                'url_home': r3.url,
                'cookies': {k: v[:20] for k, v in session.cookies.items()},
                'hidden_fields': hidden,
                'response_preview': r2.text[:500]
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
    if not session.cookies.get('JSESSIONID'):
        return jsonify({'error': 'Não autenticado. Execute /login primeiro.'}), 401
    try:
        r = session.get(data['url'], timeout=30, allow_redirects=True)
        return jsonify({'status': r.status_code, 'body': r.text, 'url': r.url})
    except Exception as e:
        logger.error(f'Erro fetch: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
