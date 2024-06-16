# Tech Shopping

## Video Demo

[Watch the Flask Shopping Cart App demonstration video](/static/appshopping.mp4.mp4)

## Overview

This is a shopping cart app built using Flask, a lightweight framework for web applications in Python. The app allows users to view a list of products, add products to the cart, and clear the cart when necessary. Products are stored in an SQLite database and are dynamically retrieved and displayed on the home page.

## Functionalities

- **Home Page**: Displays a list of products available for purchase.
 # Route to home page
 @app.route("/", methods=["GET"])
def index():
 # Query to retrieve all products
 query_products = db.execute("SELECT * FROM products")
 return render_template("index.html", query_products=query_products)


- **Add to Cart**: Allows users to add products to the cart by specifying the desired quantity.
 # Route to add a new product to the cart
@app.route("/add", methods=["POST"])
def add_product():
 if 'user_id' not in session:
 return redirect(url_for('login'))

 # Receive the request from the web browser
 _quant = int(request.form['quant'])
 _code = request.form['code']

 # Validation of fields and request method
 if _quant and _code and request.method == "POST":
 # Execute the query to get the product with the given code
 query_product = db.execute("SELECT * FROM products WHERE code = :code", code=_code)

 # Check if the product was found
 if query_product:
 # Retrieves the first result in the list (there must be only one result)
 product = query_product[0]
 # Create a dictionary with the details of the item added to the cart
 item_dict = {
 product['code']: {
 'name': product['name'],
 'code': product['code'],
 'quant': _quant,
 'price': product['price'],
 'image': product['image'],
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

 # Indicates that the session has been modified
 session.modified = True

 # Redirects to home page
 return redirect(url_for('index'))
 else:
 return "Error: Missing parameters"


- **Quantity Update**: If a product is already in the cart, the application updates the quantity and total price of the product in the cart.
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

 # Update grand total
 total_quant = sum(item['quant'] for item in session['cart_item'].values())
 total_price = sum(item['total_price'] for item in session['cart_item'].values())

 session['all_total_quant'] = total_quant
 session['all_total_price'] = total_price

 session.modified = True

 return redirect(url_for('checkout'))


- **Clear Cart**: Users have the option to clear all contents of the cart.
# Route to empty the cart
@app.route('/empty')
def empty_cart():
 try:
 session.clear()
 return redirect(url_for('index'))
 except Exception as e:
 print(e)


- **User Login and Registration**: Users can login and register new accounts.
# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
 if request.method == 'POST':
 # Receive the form credentials
 username = request.form['username']
 password = request.form['password']

 # Query to search for the user
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

# Registration Route
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


- **Checkout**: where users can review the items in the cart and complete the purchase. It displays a list of items in the cart along with the total to be paid. Users can click "Checkout" to process payment using Stripe.
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


- **Online Payment**: Users can make payments online using Stripe for secure payment processing.
- **Payment Processing**: The app integrates Stripe to process secure online payments.
#payment route
@app.route('/process_payment', methods=['POST'])
def process_payment():
 if 'user_id' not in session:
 return redirect(url_for('login'))

 # Collect session cart data
 cart_items = session.get('cart_item', {})
 total_price = session.get('all_total_price', 0)

 if not cart_items:
 flash('Your cart is empty.')
 return redirect(url_for('index'))

 try:
 # Create a payment session on Stripe
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


#successful payment route
@app.route('/success')
def success():
 return render_template('index.html')

#payment canceled route
@app.route('/cancel')
def cancel():
 return render_template('index.html')


- **User Sessions**: The application uses user sessions to track cart status and user authentication.
- **User Logout**: Users can log out of their accounts to exit the application.
# Logout route
@app.route('/logout')
def logout():
 session.clear()
 flash('You have logged out of your account.')
 return redirect(url_for('index'))


- **Session Management**: The application manages user sessions to track cart status and other user information.

## Project Structure

The project is made up of several files and folders:

### `app.py` file

This is the main file that contains the Flask code for the application. It defines the routes, handles client requests, and interacts with the database.

### `templates/` folder

This folder contains the HTML files used to render the web pages.

#### File `index.html`

- **`index.html`**: This file is used to display the home page with the product list.
 <!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <title>Store</title>
 <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" rel="stylesheet">
 <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js"></script>
 <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
 <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
 <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
 <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">

 {% with messages = get_flashed_messages() %}
 {% if messages %}
 <ul class="flashes">
 {% for message in messages %}
 <li>{{ message }}</li>
 {% endfor %}
 </ul>
 {% endif %}
 {%endwith%}

 <h1>Products</h1>
 <ul>
 {% for product in query_products %}
 <li>
 <img src="{{ url_for('static', filename='images/' ~ product.image) }}" alt="{{ product.name }}">
 <h2>{{ product.name }}</h2>
 <p>Price: ${{ product.price }}</p>
 <form action="{{ url_for('add_product') }}" method="post">
 <input type="hidden" name="code" value="{{ product.code }}">
 <input type="number" name="quant" value="1" min="1">
 {% if session.user_id %}
 <button type="submit">Add to Cart</button>
 {% else %}
 <a href="{{ url_for('login') }}">Login to Add to Cart</a>
 {% endif %}
 </form>
 </li>
 {% endfor %}
 </ul>

 {% if session.user_id %}
 <a href="{{ url_for('checkout') }}">Checkout</a>
 <a href="{{ url_for('logout') }}" class="btn btn-secondary">Logout</a>
 {% endif %}

 {% if session.cart_item %}
 <h2>Cart</h2>
 <ul>
 {% for code, item in session.cart_item.items() %}
 <li class="cart-item">
 <img src="{{ url_for('static', filename='images/' ~ item.image) }}" alt="{{ item.name }}">
 <div class="cart-item-details">
 <h3>{{ item.name }}</h3>
 <p>Quantity: {{ item.quant }}</p>
 <p>Total: ${{ item.total_price }}</p>
 </div>
 <form action="{{ url_for('remove_product', code=item.code) }}" method="post">
 <input type="hidden" name="code" value="{{ item.code }}">
 <button type="submit" class="remove-btn">Remove</button>
 </form>

 </li>
 {% endfor %}
 </ul>
 <p>Total Items: {{ session.all_total_quant }}</p>
 <p>Grand Total: ${{ session.all_total_price }}</p>
 <a href="{{ url_for('empty_cart') }}">Empty Cart</a>
 {% endif %}
</body>
</html>


#### `checkout.html` file

-**`checkout.html`** is used to display the checkout page where users can review the items in the cart and finalize the purchase. It displays a list of items in the cart along with the total to be paid. Users can click "Checkout" to process payment using Stripe.

<!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <title>Checkout</title>
 <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" rel="stylesheet">
 <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js"></script>
 <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
 <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
 <div class="container">
 <h2>Checkout</h2>
 {% with messages = get_flashed_messages() %}
 {% if messages %}
 <ul class="flashes">
 {% for message in messages %}
 <li>{{ message }}</li>
 {% endfor %}
 </ul>
 {% endif %}
 {%endwith%}

 <ul class="list-group mb-4">
 {% for item in cart_items.values() %}
 <li class="list-group-item d-flex justify-content-between align-items-center">
 <div class="d-flex align-items-center">
 <img src="{{ url_for('static', filename='images/' ~ item.image) }}" alt="{{ item.name }}" style="width: 50px; height: 50px; margin -right: 10px;">
 <div>
 <h5 class="mb-1">{{ item.name }}</h5>
 <p class="mb-1">{{ item.quant }} x ${{ item.price }} = ${{ item.total_price }}</p>
 </div>
 </div>
 <span class="badge badge-primary badge-pill">${{ item.total_price }}</span>
 </li>
 {% endfor %}
 </ul>
 <div class="d-flex justify-content-between">
 <h3>Total: ${{ total_price }}</h3>
 <form action="{{ url_for('process_payment') }}" method="post">
 <button type="submit" class="btn btn-primary">Checkout</button>
 </form>

 <!-- Logout button -->
 <a href="{{ url_for('logout') }}" class="btn btn-secondary">Logout</a>
 </div>
 </div>
</body>
</html>



#### `payment.html` file

-**`payment.html`**This file is used to display the payment page, where users can review the items in their cart before checking out and processing payment. He contains:

- A list of items in the cart, including their names, quantities, unit prices and total prices.
- The total to be paid.
- A button to process payment, which sends the purchase details to the `process_payment` route of the Flask app.
- A section to display user feedback messages, such as confirmations of success or errors during the payment process.
<!DOCTYPE html>
<html>
<head>
 <title>Payment</title>
 <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" rel="stylesheet">
 <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js"></script>
 <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
</head>
<body>
 <div class="container">
 <div class="row">
 <h2>Payment</h2>
 <div class="col-sm-12">
 <div>
 {% with messages = get_flashed_messages() %}
 {% if messages %}
 <ul class="flashes">
 {% for message in messages %}
 <li>{{ message }}</li>
 {% endfor %}
 </ul>
 {% endif %}
 {%endwith%}
 </div>

 <form action="{{ url_for('process_payment') }}" method="post">
 <h3>Items in cart</h3>
 <ul>
 {% for code, item in cart_items.items() %}
 <li>{{ item['name'] }} - {{ item['quant'] }} x ${{ item['price'] }} = ${{ item['total_price'] }}</ li>
 {% endfor %}
 </ul>
 <h3>Total: ${{ total_price }}</h3>
 <button type="submit" class="btn btn-primary">Process Payment</button>
 </form>
 </div>
 </div>
 </div>
</body>
</html>


#### `login.html` file

-**`login.html`**This file is responsible for displaying the login page, where users can enter their credentials to access the application. He contains:

- A form with fields for the username and password.
- A "Login" button that sends the entered data to the Flask app's `login` route for authentication.
- A link to the registration page (`register.html`) where users can create new accounts if they don't already have one.

When users submit the form, they will be redirected to the home page (`index.html`) if login is successful or will receive error messages if there is a problem with the credentials provided.
<!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <title>Login</title>
 <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" rel="stylesheet">
 <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js"></script>
 <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
 <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
 <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
 <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">

 {% with messages = get_flashed_messages() %}
 {% if messages %}
 <ul class="flashes">
 {% for message in messages %}
 <li>{{ message }}</li>
 {% endfor %}
 </ul>
 {% endif %}
 {%endwith%}

 <div class="container">
 <h1>Login</h1>
 <form action="{{ url_for('login') }}" method="post" class="form-container">
 <div class="form-group">
 <label for="username">Username</label>
 <input type="text" name="username" id="username" class="form-control" required>
 </div>
 <div class="form-group">
 <label for="password">Password</label>
 <input type="password" name="password" id="password" class="form-control" required>
 </div>
 <button type="submit" class="btn btn-primary btn-block">Login</button>
 </form>
 <a href="{{ url_for('register') }}">Register</a>
 </div>
</body>
</html>



#### `register.html` file

-**`register.html`**This file is responsible for displaying the registration page, where users can create new accounts in the application. He contains:

- A form with fields for the username and password.
- A "Register" button that sends the entered data to the Flask app's `register` route to create a new account.
- A link to the login page (`login.html`) where users can log in after registering.

When users submit the form, they will be redirected to the login page (`login.html`) if registration is successful or will receive error messages if there is a problem during the registration process.
<!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <title>Registration</title>
 <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/css/bootstrap.min.css" rel="stylesheet">
 <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.1/js/bootstrap.min.js"></script>
 <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>
 <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
 <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
 <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">

 {% with messages = get_flashed_messages() %}
 {% if messages %}
 <ul class="flashes">
 {% for message in messages %}
 <li>{{ message }}</li>
 {% endfor %}
 </ul>
 {% endif %}
 {%endwith%}

 <div class="container">
 <h1>Registration</h1>
 <form action="{{ url_for('register') }}" method="post" class="form-container">
 <div class="form-group">
 <label for="username">Username</label>
 <input type="text" name="username" id="username" class="form-control" required>
 </div>
 <div class="form-group">
 <label for="password">Password</label>
 <input type="password" name="password" id="password" class="form-control" required>
 </div>
 <button type="submit" class="btn btn-primary btn-block">Register</button>
 </form>
 <a href="{{ url_for('login') }}">Already have an account? Login</a>
 </div>
</body>
</html>



#### `success.html` file

-**`success.html`**This file is responsible for displaying a page informing the user that the payment was made successfully. He contains:

- A message indicating that the payment was successful.
- A link to return to the home page (`index.html`).

When users successfully complete the payment process, they are redirected to this page, where they receive confirmation that the payment was successful and have the option to return to the app's home page.
<!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <title>Success</title>
</head>
<body>
 <h1>Payment made successfully!</h1>
 <a href="{{ url_for('index') }}">Return to home page</a>
</body>
</html>



#### File `cancel.html`

-**`cancel.html`**This file is responsible for displaying a page informing the user that the payment has been canceled. He contains:

- A message indicating that the payment has been cancelled.
- A link to return to the home page (`index.html`).

When users cancel the payment process, they are redirected to this page, where they receive confirmation that the payment has been canceled and have the option to return to the app's home page.
<!DOCTYPE html>
<html lang="en">
<head>
 <meta charset="UTF-8">
 <title>Cancelled</title>
</head>
<body>
 <h1>Payment cancelled.</h1>
 <a href="{{ url_for('index') }}">Return to home page</a>
</body>
</html>


### `static/` folder

The `static` folder contains static files such as images, CSS stylesheets, and JavaScript scripts.

#### `static/css/` folder

This folder contains the CSS files used to style HTML pages.

- **`styles.css`**: This file contains the style rules for the layout and design of HTML pages.
 /* Site-wide styles */
body {
 font-family: Arial, sans-serif;
 background-color: #f8f9fa;
}

.container {
 max-width: 1200px;
 margin: 0 auto;
 padding: 20px;
}

h1, h2 {
 color: #343a40;
 text-align: center;
 margin-bottom: 30px;
}

.card {
 border: 1px solid #dee2e6;
 border-radius: 5px;
 box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
 background-color: #ffffff;
 margin-bottom: 20px;
}

.card img {
 border-bottom: 1px solid #dee2e6;
 border-top-left-radius: 5px;
 border-top-right-radius: 5px;
 max-height: 200px;
 object-fit: cover;
 width: 100%;
}

.card-body {
 padding: 15px;
}

.card-title {
 font-size: 1.25rem;
 color: #343a40;
}

.card-text {
 color: #495057;
}

.btn-primary {
 background-color: #007bff;
 border-color: #007bff;
}

.btn-primary:hover {
 background-color: #0056b3;
 border-color: #004085;
}

.btn-secondary {
 background-color: #6c757d;
 border-color: #6c757d;
}

.btn-secondary:hover {
 background-color: #5a6268;
 border-color: #545b62;
}

.input-quantity {
 width: 60px;
 display: inline-block;
}

.list-group-item {
 display: flex;
 justify-content: space-between;
 align-items: center;
}

.list-group-item img {
 width: 50px;
 height: 50px;
 margin-right: 10px;
}

.list-group-item h5 {
 margin-bottom: 5px;
 font-size: 1rem;
 color: #343a40;
}

.list-group-item p {
 margin-bottom: 0;
 color: #495057;
}

.badge {
 font-size: 1rem;
 padding: 10px;
}

.flashes {
 list-style-type: none;
 padding: 0;
}

.flashes li {
 background-color: #ffdddd;
 border-left: 6px solid #1ac500;
 margin-bottom: 15px;
 padding: 10px 15px;
}

.btn-block {
 width: 100%;
 margin-top: 10px;
}

.my-4 {
 margin-top: 1.5rem !important;
 margin-bottom: 1.5rem !important;
}

/* Styles for products in the cart */
.cart-item {
 display: flex;
 margin-bottom: 20px;
}

.cart-item img {
 width: 100px;
 margin-right: 20px;
}

.cart-item-details {
 flex: 1;
}

.remove-btn {
 background-color: #dc3545;
 color: #fff;
 padding: 5px 10px;
 border: none;
 cursor: pointer;
}

.remove-btn:hover {
 background-color: #c82333;
}

/* Styles for forms */
.form-container {
 max-width: 500px;
 margin: 0 auto;
 background-color: #ffffff;
 padding: 20px;
 border: 1px solid #dee2e6;
 border-radius: 5px;
 box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-group {
 margin-bottom: 15px;
}

.form-group label {
 display: block;
 margin-bottom: 5px;
 color: #495057;
}

.form-group input,
.form-group select {
 width: 100%;
 padding: 10px;
 border: 1px solid #ced4da;
 border-radius: 4px;
 box-sizing: border-box;
}

#### `static/images/` folder

This folder contains product images used for insertion into the database.

#### Folder `static/video/`

This folder contains the project demonstration video.

### File `db_product.db`

This is the SQLite database that stores information about users' products available for purchase.

### File `README.md`

This file contains detailed information about the project, its structure, functionalities and how to run it.

### File `requirements.txt`

The `requirements.txt` file contains the project dependencies. It lists all the libraries and frameworks required to run the Flask application, including Flask, Jinja2, Stripe, and other libraries.

### Secret Key

The `app.py` file contains the definition of the secret key (`app.secret_key`). The secret key is used to protect user session data and other sensitive data in the application. It is important to keep the secret key secure and unique for each Flask application.


## Client-Server Architecture

The application follows the client-server architecture. Here's an overview of how it works:

- **Client**: The client is the web browser. It sends HTTP requests to the server when the user interacts with the user interface, such as adding products to the cart or clearing the cart. The browser displays the server-rendered HTML pages and allows the user to interact with the application.
- **Server**: The server is implemented using Flask. It handles HTTP requests from clients, processes them, and sends appropriate responses. It also communicates with the database to retrieve product information and manage the shopping cart.

## Types of HTTP Requests

The application uses the following types of HTTP requests:

- **GET**: Used to retrieve resources such as the home page and available products.
- **POST**: Used to send data from the browser to the server, such as adding products to the cart.
- **GET (or POST)**: In some parts of the application, such as clearing the cart, both GET and POST requests can be used.

## Dependencies

The project depends on the following libraries and frameworks:

- **Flask**: Python web framework to build the server-side application.
- **Jinja2**: Template library to render HTML pages dynamically.
- **Stripe**: Library for online payment processing.
- **Werkzeug**: A WSGI library for handling HTTP requests, authentication, security and other web-related functionality.

## How to Execute

To run the application, follow these steps:

1. Install the dependencies listed in the `requirements.txt` file using the `pip install -r requirements.txt` command.
2. Make sure you have the Stripe secret key configured in the `app.py` file.
3. Run the `app.py` file using Python. You can do this by running the `python app.py` command in the terminal.
4. Open a web browser and go to `http://localhost:5000` to view the application.

Make sure Python and Flask are correctly configured in your development environment before running your application.

---
This README has been updated with detailed information about each application functionality. If you need anything else or want to make any changes, just let me know!