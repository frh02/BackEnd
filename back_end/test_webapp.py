# Add the following import at the top of the file
import pytest

# Define a fixture for the Flask app
@pytest.fixture
def app():
    from back.webapp import webapp
    app = webapp
    app.config['TESTING'] = True
    return app

# Add test cases using pytest
def test_home(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.data == b'home'

def test_resize_image(client):
    data = {
        "image_path": "YOUR_BASE64_ENCODED_IMAGE_STRING",
        "width": 50,
        "height": 50
    }
    response = client.post('/resize_image', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json

# Add test cases for the other routes

def test_sharpen_image(client):
    data = {
        "image_path": "YOUR_BASE64_ENCODED_IMAGE_STRING",
    }
    response = client.post('/sharpen_image', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json

def test_blurr_image(client):
    data = {
        "image_path": "YOUR_BASE64_ENCODED_IMAGE_STRING",
        "kernel_size": 5,
        "filter": "gaussian"
    }
    response = client.post('/blurr_image', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json

def test_rotate_image(client):
    data = {
        "image_path": "YOUR_BASE64_ENCODED_IMAGE_STRING",
        "degree": 45
    }
    response = client.post('/rotate_image', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json

def test_threshold_image(client):
    data = {
        "image_path": "YOUR_BASE64_ENCODED_IMAGE_STRING",
        "type": "Binary"
    }
    response = client.post('/threshold_image', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json

def test_grayscale_image(client):
    data = {
        "image_path": "YOUR_BASE64_ENCODED_IMAGE_STRING",
    }
    response = client.post('/grayscale_image', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json

def test_get_label(client):
    data = {
        "image": "YOUR_BASE64_ENCODED_IMAGE_STRING",
    }
    response = client.post('/get_label', json=data)
    assert response.status_code == 200
    assert "image_string" in response.json
    assert "label_list" in response.json
    assert "confidence_list" in response.json


# Run the tests
if __name__ == '__main__':
    pytest.main()
