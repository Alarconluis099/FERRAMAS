import json
from flask import Flask, request
import requests

app = Flask(__name__)

COMMERCE_CODE = "597055555532"
API_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
ENVIRONMENT = "integration"  

@app.route("/api/transbank/init", methods=["POST"])
def init_transbank_transaction():
    data = request.get_json()
    buy_order = data["buyOrder"][:20].replace(r"[^a-zA-Z0-9]", "") 
    session_id = data["sessionId"]
    amount = data["amount"]
    return_url = data["returnUrl"]

    transaction_data = {
        "buy_order": buy_order,
        "session_id": session_id,
        "amount": amount,
        "return_url": return_url,
    }

    headers = {
        "Tbk-Api-Key-Id": COMMERCE_CODE,
        "Tbk-Api-Key-Secret": API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions",
            data=json.dumps(transaction_data),
            headers=headers,
        )
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.RequestException as error:
        return {"message": "Error al iniciar la transacción", "error": str(error)}, 500

if __name__ == "__main__":
    app.run(port=3000)
