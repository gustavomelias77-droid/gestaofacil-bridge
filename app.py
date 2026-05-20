import os
import logging
from flask import Flask, jsonify, request
import requests

# Configuração de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Sessão global para armazenar a sessão autenticada
session = requests.Session()

# URLs base
BASE_URL = 'https://logus.gfsis.com.br/gestaofacil'
LOGIN_INDEX_URL = f'{BASE_URL}/login/Index'
LOGIN_POST_URL = f'{BASE_URL}/login/neo_security_manager'

# Credenciais do ambiente
USERNAME = os.environ.get('USERNAME', 'gustavo')
SENHA = os.environ.get('SENHA', 'Guga1234')
PORT = int(os.environ.get('PORT', 10000))

def realizar_login(username, password):
    """
    Realiza o login no sistema, tentando diferentes Content-Type se necessário.
    Retorna True se logado com sucesso, False caso contrário.
    """
    logger.info('Iniciando processo de login...')
    
    # Passo 1: GET para capturar cookies
    logger.debug(f'Fazendo GET em {LOGIN_INDEX_URL}')
    try:
        response_get = session.get(LOGIN_INDEX_URL, timeout=30)
        logger.debug(f'Status GET: {response_get.status_code}')
        logger.debug(f'URL final GET: {response_get.url}')
        logger.debug(f'Cookies recebidas: {dict(session.cookies)}')
        logger.debug(f'Headers da resposta GET: {dict(response_get.headers)}')
        logger.debug(f'Preview do texto da resposta GET: {response_get.text[:500]}')
    except Exception as e:
        logger.error(f'Erro no GET inicial: {e}')
        return False

    # Passo 2: POST com dados de login
    dados = {'username': username, 'password': password}
    headers_list = [
        {'Content-Type': 'application/x-www-form-urlencoded'},
        {'Content-Type': 'application/json'}
    ]

    for i, headers in enumerate(headers_list, 1):
        logger.debug(f'Tentativa {i} com Content-Type: {headers["Content-Type"]}')
        try:
            response_post = session.post(LOGIN_POST_URL, data=dados, headers=headers, timeout=30)
            logger.debug(f'Status POST: {response_post.status_code}')
            logger.debug(f'URL final POST: {response_post.url}')
            logger.debug(f'Cookies após POST: {dict(session.cookies)}')
            logger.debug(f'Headers da resposta POST: {dict(response_post.headers)}')
            logger.debug(f'Preview do texto da resposta POST: {response_post.text[:500]}')
            
            # Verifica se o login foi bem-sucedido (por exemplo, redirecionamento ou página esperada)
            if response_post.status_code == 200 and 'login' not in response_post.url.lower():
                logger.info('Login realizado com sucesso!')
                return True
            elif response_post.status_code == 302:
                logger.info('Login bem-sucedido com redirecionamento (302).')
                return True
            else:
                logger.warning(f'Tentativa {i} falhou. Status: {response_post.status_code}, URL: {response_post.url}')
        except Exception as e:
            logger.error(f'Erro no POST: {e}')
    
    logger.error('Todas as tentativas de login falharam.')
    return False

# Realiza login na inicialização da aplicação
def init_login():
    if not realizar_login(USERNAME, SENHA):
        logger.critical('Falha ao realizar login inicial. A aplicação pode não funcionar corretamente.')
    else:
        logger.info('Sessão autenticada armazenada com sucesso.')

init_login()

@app.route('/health', methods=['GET'])
def health():
    """
    Endpoint de health check.
    """
    return jsonify({'status': 'ok', 'autenticado': 'JSESSIONID' in session.cookies}), 200

@app.route('/fetch', methods=['GET'])
def fetch():
    """
    Endpoint exemplo que usa a sessão autenticada.
    """
    if 'JSESSIONID' not in session.cookies:
        return jsonify({'erro': 'Sessão não autenticada. Tente /login novamente.'}), 401
    # Exemplo: retorna um preview de uma página protegida
    try:
        response = session.get(f'{BASE_URL}/dashboard', timeout=30)
        return jsonify({'status': response.status_code, 'preview': response.text[:500]}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/login', methods=['POST'])
def login_endpoint():
    """
    Endpoint para forçar um novo login (útil se a sessão expirar).
    """
    data = request.get_json() or {}
    username = data.get('username', USERNAME)
    password = data.get('password', SENHA)
    if realizar_login(username, password):
        return jsonify({'mensagem': 'Login realizado com sucesso!'}), 200
    else:
        return jsonify({'erro': 'Falha no login.'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
