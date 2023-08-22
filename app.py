from opensearchpy import OpenSearch
from flask import Flask, render_template, request, session, redirect, url_for

# Initialise the Flask app
app = Flask(__name__)
app.secret_key = "4432157"  # Set your secret key for session encryption

# Initialise OpenSearch client
client = OpenSearch(
    hosts=["https://localhost:9200"],
    http_auth=("admin", "admin"),
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)

# Function to perform a search with various filters
def search_results(search_term, min_price=None, max_price=None, flavour=None, product_type=None):
    index_name = "products"

    # Create a list to store filter conditions
    filter_conditions = []

    if search_term:
        # Add search term filter
        filter_conditions.append({
            "multi_match": {
                "query": search_term,
                "fields": ["flavour", "name", "product_type"]
            }
        })

    if min_price or max_price:
        # Add price range filter
        price_range_filter = {
            "range": {
                "price": {}
            }
        }
        if min_price:
            price_range_filter["range"]["price"]["gte"] = min_price
        if max_price:
            price_range_filter["range"]["price"]["lte"] = max_price

        filter_conditions.append(price_range_filter)

    if flavour:
        # Add flavour filter using the "match" query
        filter_conditions.append({
            "match": {
                "flavour": flavour
            }
        })

    if product_type:
        # Add product type filter
        filter_conditions.append({
            "match": {
                "product_type": product_type
            }
        })

    # Combine all filter conditions using "must" (AND) logic
    search_body = {
        "query": {
            "bool": {
                "must": filter_conditions
            }
        }
    }

    # Perform the search
    response = client.search(index=index_name, body=search_body)
    hits = response["hits"]["hits"]

    # Process the search results
    search_results = []
    for hit in hits:
        source = hit["_source"]
        source["id"] = hit["_id"]
        search_results.append(source)

    if not search_results:
        search_results = None  # Set search results to None if no results found

    return search_results

# Function to get product details by ID
def get_product_by_id(product_id):
    index_name = "products"

    # Get a specific product by its ID
    response = client.get(index=index_name, id=product_id)

    if response.get('found'):
        product = response['_source']
        product['id'] = response['_id']
        return product

    return None

# Route for the homepage
@app.route('/', methods=['GET', 'POST'])
def index():
    search_with_filters = False
    success_message = request.args.get('success_message')

    # If the request method is POST, get the search_term from the form data
    if request.method == 'POST':
        search_term = request.form.get('search_term')
        if not search_term:
            return redirect(url_for('index'))
    else:
        # If the request method is GET, get the search_term and filter parameters from the query parameters
        search_term = request.args.get('search_term')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        flavour = request.args.get('flavour')
        product_type = request.args.get('product_type')

        # Check if any filters are applied
        if any([search_term, min_price, max_price, flavour, product_type]):
            search_with_filters = True

    # Perform the search based on the filters
    results = search_results(search_term, min_price, max_price, flavour, product_type)

    # Set the page_title variable based on the search_with_filters
    page_title = "Search Results" if search_with_filters else "All Products"

    # Set the no_results_message
    no_results_message = "No search results." if not results else None

    return render_template('index.html', search_term=search_term, results=results, page_title=page_title,
                           no_results_message=no_results_message, success_message=success_message)

# Route for adding a product to the basket
@app.route('/add_to_basket', methods=['POST'])
def add_to_basket():
    product_id = request.form.get('product_id')
    product = get_product_by_id(product_id)

    if product:
        basket = session.get('basket', [])  # Add the product to the user's basket
        basket.append(product)
        session['basket'] = basket
        # After adding an item to the basket
        success_message = "Item was successfully added to the basket."
        return redirect(url_for('index', success_message=success_message, **request.args))
    else:
        return "Product not found"

# Route for removing a product from the basket
@app.route('/remove_from_basket', methods=['POST'])
def remove_from_basket():
    product_id = request.form.get('product_id')
    basket = session.get('basket', [])
    
    # Find the index of the product with the matching product_id
    index_to_remove = next((index for index, product in enumerate(basket) if product['id'] == product_id), None)

    if index_to_remove is not None:
        # Remove the product from the basket using the index
        basket.pop(index_to_remove)

    session['basket'] = basket
    return redirect(url_for('basket'))

# Route for displaying the user's basket
@app.route('/basket')
def basket():
    basket = session.get('basket', [])
    total_price = sum(product['price'] for product in basket)
    return render_template('basket.html', basket=basket, total_price=total_price)


@app.route('/checkout', methods=['POST'])
def checkout():
    basket = session.get('basket', [])
    
    if not basket:  # Check if the basket is empty
        session['checkout_message'] = "You cannot check out, the basket is empty."
        return redirect(url_for('basket'))  # Redirect back to the basket page
    
    total_price = sum(product['price'] for product in basket)
    
    # Clear the basket after the checkout process
    session['basket'] = []

    return render_template('checkout.html', basket=basket, total_price=total_price)


# Run the Flask app if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True)
