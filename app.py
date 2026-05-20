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

        # Todos inputs: hidden, text, etc
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
                form_
