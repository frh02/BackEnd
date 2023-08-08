import unittest
import logging
from unittest.mock import Mock, patch
from flask import Flask
from FrontEnd import webapp  # Replace 'your_module' with the actual module name

logging.basicConfig(level=logging.INFO)  # Set logging level to INFO

class TestApp(unittest.TestCase):
    """
    Test suite for the Flask web application.
    """

    def setUp(self):
        """
        Set up the Flask app and test client before each test case.
        """
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('FrontEnd.dynamodb')
    @patch('FrontEnd.s3_boto')
    def test_create_table(self, mock_s3_boto, mock_dynamodb):
        """
        Test the '/create_table' route.
        """
        logging.info("Testing '/create_table' route")
        response = self.client.post('/create_table')
        self.assertEqual(response.status_code, 200)  # Check if the response is successful

    @patch('FrontEnd.dynamodb')
    @patch('FrontEnd.s3_boto')
    def test_upload_to_S3(self, mock_s3_boto, mock_dynamodb):
        """
        Test the '/upload' route for uploading to S3.
        """
        logging.info("Testing '/upload' route for uploading to S3")
        with self.app.app_context():
            mock_bucket = Mock()
            mock_s3_boto.resource.return_value = mock_bucket

            response = self.client.post('/upload', data={'key': 'test_key'}, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 200)  # Check if the response is successful

    @patch('FrontEnd.dynamodb')
    @patch('FrontEnd.s3_boto')
    def test_get_images(self, mock_s3_boto, mock_dynamodb):
        """
        Test the '/image_gallery' route for retrieving images.
        """
        logging.info("Testing '/image_gallery' route for retrieving images")
        with self.app.app_context():
            mock_table = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_table.scan.return_value = {'Items': [{'image_key': 'key1', 'image_path': 'path1'}]}

            response = self.client.get('/image_gallery')
            self.assertEqual(response.status_code, 200)  # Check if the response is successful

    @patch('FrontEnd.dynamodb')
    @patch('FrontEnd.s3_boto')
    def test_key(self, mock_s3_boto, mock_dynamodb):
        """
        Test the '/key' route for retrieving an image by key.
        """
        logging.info("Testing '/key' route for retrieving an image by key")
        with self.app.app_context():
            mock_table = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_table.get_item.return_value = {'Item': {'image_key': 'key1', 'image_path': 'path1'}}

            response = self.client.post('/key', data={'key': 'key1'})
            self.assertEqual(response.status_code, 200)  # Check if the response is successful

if __name__ == '__main__':
    unittest.main()
