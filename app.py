import os, logging, re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 10000))
USERNAME = os.environ.get('USERNAME', 'gustavo')
SENHA = os.environ.get('SENHA', 'Guga1234')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE = 'https://logus.gfsis.com.br'

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/login', methods=['POST'])
def login():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })

    try:
        # Passo 1: GET da página de login
        r1 = session.get(f'{BASE}/gestaofacil/login/Index', timeout=30)
        logger.info(f'GET: {r1.status_code}')

        # Extrai TODOS os campos do formulário
        form_action = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', r1.text, re.I)
        action = form_action.group(1) if form_action else ''

        inputs = re.findall(r'<input[^>]+>', r1.text, re.I)
        form_data = {}
        for inp in inputs:
            name_m = re.search(r'name=["\']([^"\']+)["\']', inp)
            value_m = re.search(r'value=["\']([^"\']*)["\']', inp)
            type_m = re.search(r'type=["\']([^"\']+)["\']', inp)
            if name_m:
                nome = name_m.group(1)
                valor = value_m.group(1) if value_m else ''
                tipo = type_m.group(1).lower() if type_m else 'text'
                if tipo == 'submit':
                    continue
                form_data[nome] = valor

        logger.info(f'Campos do form ({len(form_data)}): {list(form_data.keys())}')

        form_data['username'] = USERNAME
        form_data['password'] = SENHA

        if not action or action == '#':
            action = '/gestaofacil/login/neo_security_manager'

        if action.startswith('http'):
            post_url = action
        elif action.startswith('/'):
            post_url = f'{BASE}{action}'
        else:
            post_url = f'{BASE}/gestaofacil/login/{action}'

        # Passo 2: POST com todos os campos
        r2 = session.post(post_url, data=form_data, timeout=30, allow_redirects=True)
        logger.info(f'POST: {r2.status_code} -> {r2.url}')

        # Passo 3: verifica se logou
        r3 = session.get(f'{BASE}/gestaofacil/', timeout=30, allow_redirects=True)
        logger.info(f'HOME: {r3.status_code} -> {r3.url}')

        if 'login' not in r3.url.lower():
            return jsonify({'success': True, 'url': r3.url})

        return jsonify({
            'error': 'Login falhou',
            'debug': {
                'campos_form': list(form_data.keys()),
                'action': action,
                'post_url': post_url,
                'status_get': r1.status_code,
                'status_post': r2.status_code,
                'url_post': r2.url,
                'url_home': r3.url,
                'cookies': {k: str(v)[:30] for k, v in session.cookies.items()}
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

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })

    try:
        r = session.get(data['url'], timeout=30, allow_redirects=True)
        return jsonify({'status': r.status_code, 'body': r.text, 'url': r.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
