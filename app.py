import qrcode
import requests
from flask import Flask, request, jsonify, render_template_string
from io import BytesIO

app = Flask(__name__)

# Hardcoded Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = 'your_telegram_bot_token'  # Replace with your bot token
TELEGRAM_CHAT_ID = 'your_telegram_chat_id'  # Replace with your chat ID
WEBHOOK_URL = "https://example.com/confirm"  # Replace with your webhook URL

# HTML content with embedded CSS and JavaScript
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UPI Payment QR Code Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            text-align: center;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        input, button {
            padding: 10px;
            margin: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            background-color: #28a745;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background-color: #218838;
        }
        #qrImage {
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Generate UPI QR Code</h2>
        <input type="text" id="upiId" placeholder="Enter UPI ID (e.g., 87878787@paytm)">
        <input type="number" id="amount" placeholder="Enter Amount">
        <input type="text" id="transactionId" placeholder="Enter Transaction ID">
        <button onclick="generateQr()">Generate QR Code</button>
        <img id="qrImage" src="" alt="QR Code" style="display:none;">
        <p id="result"></p>
    </div>

    <script>
        function generateQr() {
            const upiId = document.getElementById('upiId').value;
            const amount = document.getElementById('amount').value;
            const transactionId = document.getElementById('transactionId').value;

            if (!upiId || !amount || !transactionId) {
                alert('Please fill all fields!');
                return;
            }

            fetch('/generate_qr', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ upi_id: upiId, amount: amount, transaction_id: transactionId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'QR code sent to Telegram') {
                    document.getElementById('result').innerText = 'QR Code sent to Telegram!';
                } else {
                    document.getElementById('result').innerText = 'Failed to send QR Code.';
                }
            })
            .catch((error) => {
                console.error('Error:', error);
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html_content)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json
    upi_id = data['upi_id']  # UPI ID (e.g., '87878787@paytm')
    amount = data['amount']  # Amount to be paid
    transaction_id = data['transaction_id']  # Unique Transaction ID

    # UPI Payment String format
    upi_string = f"upi://pay?pa={upi_id}&am={amount}&tr={transaction_id}&cu=INR"

    # Generate QR Code from UPI String
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(upi_string)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Save the QR Code image in memory
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    # Send QR Code to Telegram with inline buttons
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': img_io}
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'Please pay ₹{amount} to UPI ID: {upi_id}. Transaction ID: {transaction_id}',
        'reply_markup': {
            'inline_keyboard': [[
                {'text': 'Received', 'callback_data': f'received_{transaction_id}'},
                {'text': 'Not Received', 'callback_data': f'not_received_{transaction_id}'}
            ]]
        }
    }
    response = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': data['caption']}, files=files, json=data['reply_markup'])

    if response.status_code == 200:
        return jsonify({'status': 'QR code sent to Telegram', 'transaction_id': transaction_id})
    else:
        return jsonify({'status': 'Failed to send QR code'}), 500

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    if 'callback_query' in update:
        callback_query = update['callback_query']
        callback_data = callback_query['data']
        transaction_id = callback_data.split('_')[1]

        # Check if 'Received' or 'Not Received'
        if callback_data.startswith('received'):
            # Confirm Payment via Webhook
            webhook_response = requests.post(WEBHOOK_URL, json={'transaction_id': transaction_id, 'status': 'confirmed'})
            confirmation_message = f"Payment for Transaction ID {transaction_id} confirmed!"
        else:
            confirmation_message = f"Payment for Transaction ID {transaction_id} not received."

        # Send confirmation message back to Telegram
        send_message_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        message_data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': confirmation_message
        }
        requests.post(send_message_url, json=message_data)

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
