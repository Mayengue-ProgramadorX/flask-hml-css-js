from flask import Flask, render_template, redirect, url_for, request, session, flash
from cs50 import SQL
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)

# Configure the Stripe secret key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Initialize the SQL object
db = SQL(os.getenv('DATABASE_URL'))

# Route for the home page
@app.route("/", methods=["GET"])
def index():
    # Query to retrieve all products
    query_products = db.execute("SELECT * FROM products")
    return render_template("index.html", query_products=query_products)

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get credentials from the form
        username = request.form['username']
        password = request.form['password']

        # Query to find the user
        user = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        if len(user) == 1 and check_password_hash(user[0]['password'], password):
            session['user_id'] = user[0]['id']
            session['username'] = user[0]['username']
            flash('Login successful!')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))
    return render_template('login.html')

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hash the password using pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                       username=username, password=hashed_password)
            flash('Registration successful! You can now log in.')
            return redirect(url_for('login'))
        except:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('register'))
    return render_template('register.html')

# Route to add a new product to the cart
@app.route("/add", methods=["POST"])
def add_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Receive the request from the web browser
    _quant = int(request.form['quant'])
    _code = request.form['code']

    # Validate the fields and request method
    if _quant and _code and request.method == "POST":
        # Execute the query to get the product with the given code
        query_product = db.execute("SELECT * FROM products WHERE code = :code", code=_code)

        # Check if the product was found
        if query_product:
            # Retrieve the first result from the list (there should only be one result)
            product = query_product[0]
            # Create a dictionary with the details of the item added to the cart
            item_dict = {
                product['code']: {
                    'name': product['name'],
                    'price': product['price'],
                    'quant': _quant,
                    'total_price': _quant * product['price']
                }
            }

            all_total_price = 0
            all_total_quant = 0

            # Check if the 'cart_item' key is present in the session
            if 'cart_item' in session:
                if product['code'] in session['cart_item']:
                    for key, value in session['cart_item'].items():
                        if product['code'] == key:
                            old_quant = session['cart_item'][key]['quant']
                            total_quant = old_quant + _quant
                            session['cart_item'][key]['quant'] = total_quant
                            session['cart_item'][key]['total_price'] = total_quant * product['price']
                else:
                    session['cart_item'][product['code']] = item_dict[product['code']]
            else:
                session['cart_item'] = item_dict

            for key, value in session['cart_item'].items():
                individual_quant = int(session['cart_item'][key]['quant'])
                individual_price = float(session['cart_item'][key]['total_price'])
                all_total_quant += individual_quant
                all_total_price += individual_price

        else:
            session['cart_item'] = item_dict
            all_total_quant = _quant
            all_total_price = _quant * product['price']

        session['all_total_quant'] = all_total_quant
        session['all_total_price'] = all_total_price

        # Indicate that the session has been modified
        session.modified = True

        # Redirect to the home page
        return redirect(url_for('index'))
    else:
        return "Error: Missing parameters"

# Route to display the checkout page
@app.route('/checkout', methods=['GET'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('process_payment'))

    cart_items = session.get('cart_item', {})
    total_price = session.get('all_total_price', 0)

    if not cart_items:
        flash('Your cart is empty.')
        return redirect(url_for('index'))

    return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

# Payment processing route
@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Collect cart data from the session
    cart_items = session.get('cart_item', {})
    total_price = session.get('all_total_price', 0)

    if not cart_items:
        flash('Your cart is empty.')
        return redirect(url_for('index'))

    try:
        # Create a payment session in Stripe
        session_checkout = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item['name'],
                    },
                    'unit_amount': int(item['price'] * 100),
                },
                'quantity': item['quant'],
            } for item in cart_items.values()],
            mode='payment',
            success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('cancel', _external=True),
        )

        return redirect(session_checkout.url, code=303)
    except stripe.error.StripeError as e:
        flash('There was an error processing your payment: {}'.format(e.user_message))
        return redirect(url_for('index'))

# Route for successful payment
@app.route('/success')
def success():
    return render_template('index.html')

# Route for canceled payment
@app.route('/cancel')
def cancel():
    return render_template('index.html')

# Route to empty the cart
@app.route('/empty')
def empty_cart():
    try:
        session.clear()
        return redirect(url_for('index'))
    except Exception as e:
        print(e)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

# Route to remove a product from the cart
@app.route("/remove/<code>", methods=["GET", "POST"])
def remove_product(code):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        if 'cart_item' in session and code in session['cart_item']:
            # Remove the product from the cart
            session['cart_item'].pop(code)

            # Update the total
            all_total_price = 0
            all_total_quant = 0
            for key, value in session['cart_item'].items():
                individual_quant = int(session['cart_item'][key]['quant'])
                individual_price = float(session['cart_item'][key]['total_price'])
                all_total_quant += individual_quant
                all_total_price += individual_price

            session['all_total_quant'] = all_total_quant
            session['all_total_price'] = all_total_price

            # Indicate that the session has been modified
            session.modified = True

            # Redirect back to the cart
            return redirect(url_for('index'))
        else:
            return "Error: Product not found in cart"
    else:
        return redirect(url_for('index'))

# Route to update the quantity of a product in the cart
@app.route("/update_quantity", methods=["POST"])
def update_quantity():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    code = request.form.get('code')
    new_quantity = int(request.form.get('quantity'))

    if 'cart_item' in session and code in session['cart_item']:
        session['cart_item'][code]['quant'] = new_quantity
        session['cart_item'][code]['total_price'] = new_quantity * session['cart_item'][code]['price']

        # Update the overall total
        total_quant = sum(item['quant'] for item in session['cart_item'].values())
        total_price = sum(item['total_price'] for item in session['cart_item'].values())

        session['all_total_quant'] = total_quant
        session['all_total_price'] = total_price

        session.modified = True

    return redirect(url_for('checkout'))

# Run the Flask app
if __name__ == '__main__':
    app.secret_key = 'supersecretkey'  # Replace with a real secret key
    app.run(debug=True)
