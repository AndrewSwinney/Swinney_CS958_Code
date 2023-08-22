import pytest
import requests_mock
from flask import Flask, session
from pytest_mock import mocker
from opensearchpy import OpenSearch
from app import app, search_results, get_product_by_id

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
        
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def clear_session():
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess.clear()


def test_search_results(client, mocker):
    # Mock the OpenSearch client
    mock_client = mocker.patch("app.client")

    # Mock the search response
    mock_response = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "name": "Product 1",
                        "flavour": "Vanilla",
                        "price": 10.99,
                        "image_url": "https://example.com/product1.jpg",
                    },
                    "_id": "1",
                },
                {
                    "_source": {
                        "name": "Product 2",
                        "flavour": "Chocolate",
                        "price": 9.99,
                        "image_url": "https://example.com/product2.jpg",
                    },
                    "_id": "2",
                },
            ]
        }
    }
    mock_client.search.return_value = mock_response

    # Perform the search
    results = search_results("vanilla")

    # Assertions
    assert results is not None
    assert len(results) == 2
    assert results[0]["name"] == "Product 1"
    assert results[0]["flavour"] == "Vanilla"
    assert results[1]["name"] == "Product 2"
    assert results[1]["flavour"] == "Chocolate"


def test_get_product_by_id(client, mocker):
    # Mock the OpenSearch client
    mock_client = mocker.patch("app.client")

    # Mock the get response
    mock_response = {
        "_source": {
            "name": "Product 1",
            "flavour": "Vanilla",
            "price": 10.99,
            "image_url": "https://example.com/product1.jpg",
        },
        "_id": "1",
        "found": True,
    }
    mock_client.get.return_value = mock_response

    # Get the product by ID
    product = get_product_by_id("1")

    # Assertions
    assert product is not None
    assert product["name"] == "Product 1"
    assert product["flavour"] == "Vanilla"


def test_add_to_basket_route(client, mocker):
    # Mock the OpenSearch client
    mock_client = mocker.patch("app.client")

    # Mock the get product response
    mock_product = {
        "name": "Product 1",
        "flavour": "Vanilla",
        "price": 10.99,
        "image_url": "https://example.com/product1.jpg",
        "id": "1",
    }
    mock_client.get.return_value = {
        "_source": mock_product,
        "_id": "1",
        "found": True,
    }

    # Make a request to the add_to_basket route
    response = client.post("/add_to_basket", data={"product_id": "1"})

    # Assertions
    assert response.status_code == 302
    assert session["basket"] == [mock_product]


def test_remove_from_basket_route(client, mocker):
    # Set up the session with a product in the basket
    with client.session_transaction() as sess:
        sess["basket"] = [
            {
                "name": "Product 1",
                "flavour": "Vanilla",
                "price": 10.99,
                "image_url": "https://example.com/product1.jpg",
                "id": "1",
            }
        ]

    # Make a request to the remove_from_basket route
    response = client.post("/remove_from_basket", data={"product_id": "1"})

    # Assertions
    assert response.status_code == 302
    assert session["basket"] == []


def test_index_route_no_search(client, mocker):
    # Test the index route with no search term or filters
    response = client.get('/')
    assert response.status_code == 200
    assert b"<h1>All Products</h1>" in response.data


def test_index_route_with_search(client, mocker):
    # Test the index route with a search term
    mock_results = [
        {
            "name": "Product 1",
            "flavour": "Vanilla",
            "price": 10.99,
            "image_url": "https://example.com/product1.jpg",
            "id": "1",
        },
        # Add more mock search results if needed
    ]
    mocker.patch("app.search_results", return_value=mock_results)

    response = client.get('/?search_term=vanilla')
    assert response.status_code == 200
    assert b"<h1>Search Results</h1>" in response.data
    assert b"Product 1" in response.data
    assert b"Vanilla" in response.data


def test_add_to_basket_route_success(client, mocker):
    # Test the add_to_basket route with a valid product_id
    mock_product = {
        "name": "Product 1",
        "flavour": "Vanilla",
        "price": 10.99,
        "image_url": "https://example.com/product1.jpg",
        "id": "1",
    }
    mocker.patch("app.get_product_by_id", return_value=mock_product)

    response = client.post('/add_to_basket', data={"product_id": "1"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Item was successfully added to the basket." in response.data
    assert session["basket"] == [mock_product]


def test_add_to_basket_route_invalid_product(client, mocker):
    # Test the add_to_basket route with an invalid product_id
    mocker.patch("app.get_product_by_id", return_value=None)

    response = client.post('/add_to_basket', data={"product_id": "invalid_id"})
    assert response.status_code == 200
    assert b"Product not found" in response.data


def test_remove_from_basket_route_success(client, mocker):
    # Test the remove_from_basket route with a product in the basket
    mock_product = {
        "name": "Product 1",
        "flavour": "Vanilla",
        "price": 10.99,
        "image_url": "https://example.com/product1.jpg",
        "id": "1",
    }
    mocker.patch("app.get_product_by_id", return_value=mock_product)

    # Set up the session with a product in the basket
    with client.session_transaction() as sess:
        sess["basket"] = [mock_product]

    response = client.post('/remove_from_basket', data={"product_id": "1"}, follow_redirects=True)
    assert response.status_code == 200
    assert session["basket"] == []

def test_basket_route_with_products(client):
    # Set up the session with products in the basket
    with client.session_transaction() as sess:
        sess["basket"] = [
            {"name": "Product 1", "price": 15, "id": "1"},
            {"name": "Product 2", "price": 20, "id": "2"},
        ]

    # Send a GET request to the /basket route
    response = client.get('/basket')

    # Assert that the response is successful (status code 200)
    assert response.status_code == 200

    # Assert that the product data is present in the response
    assert b"<h1>Basket</h1>" in response.data
    assert b"Product 1" in response.data
    assert b"Product 2" in response.data

    # Calculate the total price manually based on the mock products
    total_price = sum(product['price'] for product in session["basket"])

    # Assert that the total price is present in the response
    assert total_price == 35
    
def test_search_empty_search_term(client, mocker):
    # Test searching with an empty search term
    mock_results = [
        {
            "name": "Product 1",
            "flavour": "Vanilla",
            "price": 10.99,
            "image_url": "https://example.com/product1.jpg",
            "id": "1",
        },
        {
            "name": "Product 2",
            "flavour": "Chocolate",
            "price": 9.99,
            "image_url": "https://example.com/product2.jpg",
            "id": "2",
        },
        # Add more mock search results if needed
    ]
    mocker.patch("app.search_results", return_value=mock_results)

    response = client.get('/?search_term=')
    assert response.status_code == 200
    assert b"<h1>All Products</h1>" in response.data
    assert b"Product 1" in response.data
    assert b"Product 2" in response.data



def test_search_with_filters(client, mocker):
    # Test searching with various combinations of filters
    mock_results = [
        {
            "name": "Product 1",
            "flavour": "Vanilla",
            "price": 10.99,
            "image_url": "https://example.com/product1.jpg",
            "id": "1",
        },
        {
            "name": "Product 2",
            "flavour": "Chocolate",
            "price": 9.99,
            "image_url": "https://example.com/product2.jpg",
            "id": "2",
        },
    ]
    
    mocker.patch("app.search_results", return_value=mock_results)

    response = client.get('/?min_price=5&max_price=15&flavour=Vanilla&product_type=Dessert')
    assert response.status_code == 200
    assert b"<h1>Search Results</h1>" in response.data
    assert b"Product 1" in response.data
    assert b"Product 2" in response.data

def test_checkout_empty_basket(client):
    # Test for checking out with an empty basket
    response = client.post('/checkout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Your basket is empty.' in response.data

def test_successful_checkout(client):
    # Test for a successful checkout process
    with client.session_transaction() as session:
        session['basket'] = [
            {'id': '1', 'name': 'Product A', 'price': 10.0},
            {'id': '2', 'name': 'Product B', 'price': 15.0}
        ]

    response = client.post('/checkout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Thank you for your order!' in response.data
    assert b'Your payment of \xc2\xa325.0 has been received.' in response.data
    
def test_add_to_basket_and_checkout(client, mocker):
    # Mock the OpenSearch client
    mock_client = mocker.patch("app.client")

    # Mock the get product response
    mock_product = {
        "name": "Product 1",
        "flavour": "Vanilla",
        "price": 10.99,
        "image_url": "https://example.com/product1.jpg",
        "id": "1",
    }
    mock_client.get.return_value = {
        "_source": mock_product,
        "_id": "1",
        "found": True,
    }

    # Add a product to the basket
    response = client.post("/add_to_basket", data={"product_id": "1"})

    # Assertions for adding to the basket
    assert response.status_code == 302
    assert session["basket"] == [mock_product]

    # Proceed to checkout
    response = client.post("/checkout")  # Use POST for checkout

    # Assertions for checkout process
    assert response.status_code == 200
    assert b'Thank you for your order! Your payment of \xc2\xa310.99 has been received. Your purchase will be delivered in 2-3 working days.' in response.data


if __name__ == '__main__':
    pytest.main()

