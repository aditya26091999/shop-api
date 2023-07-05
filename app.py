from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import base64

app = Flask(__name__)

# Configure MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['hardware-shop']

@app.route('/', methods=['GET'])
def hello():
    return jsonify({'success': 'Hello from Hardware Shop API'}), 200

@app.route('/createbill', methods=['POST'])
def create_bill():
    
    collection = db['bills']
    transactions_collection = db['transactions']
    # Get request data
    data = request.get_json()
    bill_number = data.get('billnumber')
    customer_name = data.get('customername')
    items = data.get('items')

    # Check if bill number already exists
    if collection.find_one({'bill_number': bill_number}):
        return jsonify({'error': 'Bill number already exists.'}), 400

    # Calculate total price
    total_price = sum(item['price'] for item in items)

    # Get current datetime
    current_datetime = datetime.now()

    # Prepare document to insert into MongoDB
    document = {
        'bill_number': bill_number,
        'customer_name': customer_name,
        'items': items,
        'total_price': total_price,
        'datetime': current_datetime
    }

    # Insert document into MongoDB collection
    collection.insert_one(document)

    transactiondocument = {
        'customer_name': customer_name,
        'datetime': current_datetime,
        'payment_amount':total_price
    }

    # Insert or update the document in the transactions collection
    transactions_collection.insert_one(transactiondocument)

    return jsonify({'success': 'Bill created successfully.'}), 201

@app.route('/uploadbillimage', methods=['POST'])
def upload_bill_image():
    collection = db['bills']
    # Get the image file from the request
    image_file = request.files['image']

    # Read and encode the image file as base64
    image_data = base64.b64encode(image_file.read())

    # Prepare document to update in MongoDB
    bill_number = request.form.get('billnumber')
    document = collection.find_one({'bill_number': bill_number})

    # Check if the bill number exists
    if document is None:
        return jsonify({'error': 'Bill does not exist for the uploaded bill image.'}), 400

    # Update the document in the MongoDB collection with the image data
    collection.update_one({'bill_number': bill_number}, {'$set': {'image': image_data.decode('utf-8')}})

    return jsonify({'success': 'Bill image uploaded successfully.'}), 201

@app.route('/showbalance', methods=['GET'])
def total_balance():
    transactions_collection = db['transactions']
    pipeline = pipeline = [
        {
            '$group': {
                '_id': '$customer_name',
                'outstanding_amount': {'$sum': '$payment_amount'}
            }
        },
        {
            '$project': {
                '_id': 0,
                'customer_name': '$_id',
                'outstanding_amount': 1
            }
        }
    ]
    result = list(transactions_collection.aggregate(pipeline))

    return jsonify(result), 200

@app.route('/recordpayment', methods=['POST'])
def record_payment():

    transactions_collection = db['transactions']

    # Get the request payload
    payload = request.json

    # Extract the necessary data from the payload
    customer_name = payload['customername']
    payment_amount = payload['paymentamount']
    current_datetime = datetime.now()

    # Create the document to insert or update in the transactions collection
    document = {
        'customer_name': customer_name,
        'payment_amount': -payment_amount,
        'datetime': current_datetime,
    }

    # Insert or update the document in the transactions collection
    transactions_collection.insert_one(document)

    return jsonify({'success': 'Payment recorded successfully.'}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)