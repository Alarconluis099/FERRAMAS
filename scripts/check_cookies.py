import sys
import os
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from app import app


# Script para verificar cookies/session usando test_client
def run_check():
    app.config['TESTING'] = True
    client = app.test_client()
    # Simular login estableciendo valores en session
    with client.session_transaction() as sess:
        sess['usuario'] = 'testuser'
        sess['id_user'] = 1
    # Llamar al endpoint debug
    # Llamar al endpoint debug
    resp = client.get('/__debug/cookies')
    print('Status code:', resp.status_code)
    try:
        print('Response JSON:', resp.get_json())
    except Exception as e:
        print('Could not parse JSON:', e)


if __name__ == '__main__':
    run_check()
