from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuration
TRANSBANK_API_URL = "https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions"
COMMERCE_CODE = "597055555532"  # Replace with your real commerce code
API_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"  # Replace with your real API key
ENVIRONMENT = "integration"  # Change to "production" in a production environment

@app.route("/api/transbank/init", methods=["POST"])
def init_transbank_transaction():
    data = request.get_json()
    buy_order = data["buyOrder"][:20].replace(r"[^a-zA-Z0-9]", "")

    payload = {
        "buy_order": buy_order,
        "session_id": data["sessionId"],
        "amount": data["amount"],
        "return_url": data["returnUrl"],
    }

    headers = {
        "Tbk-Api-Key-Id": COMMERCE_CODE,
        "Tbk-Api-Key-Secret": API_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(TRANSBANK_API_URL, json=payload, headers=headers)
        response.raise_for_status()  # Raise an exception for error responses

        response_data = response.json()
        return jsonify(response_data)
    
    except requests.exceptions.RequestException as error:
        return jsonify(
            {"message": "Error al iniciar la transacción", "error": str(error)}
        ), 500

if __name__ == "__main__":
    app.run(port=3000)
