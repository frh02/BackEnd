# editfunc.py
from back import webapp
import cv2
import imutils
import numpy as np
import boto3
from back.config import ConfigAWS, SHARPEN_KERNEL
import base64
from flask import request
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = boto3.client('rekognition', region_name='us-east-1',
                      aws_access_key_id=ConfigAWS['aws_access_key_id'],
                      aws_secret_access_key=ConfigAWS['aws_secret_access_key'])


@webapp.route('/')
@webapp.route('/home')
def home():
    return "home"


def readb64(base64_string):
    decoded_data = base64.b64decode(base64_string)
    np_data = np.fromstring(decoded_data, np.uint8)
    img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
    return img


@webapp.route('/resize_image', methods=['GET', 'POST'])
# Resize an image by the given width and height
def resize_image():
    """
    Arguments:
        image_path : path to the image to be edited
        height : scale of height to change
        width : scale of width to change

    Function:
        Resizes the image based on the scale given as arguments

    Returns:
        path to resized image
    """
    try:
        image = request.json["image_path"]
        image = readb64(image)
        width = request.json["width"]
        height = request.json["height"]

        w = int(image.shape[1] * width / 100)
        h = int(image.shape[0] * height / 100)

        image_resized = cv2.resize(image, (w, h), interpolation=cv2.INTER_CUBIC)

        image_string = cv2.imencode('.png', image_resized)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')
        data = {"image_string": image_string}
        return data
    except Exception as e:
        logging.exception("Error occurred while resizing the image.")
        return {"error": "An error occurred while resizing the image."}, 500


@webapp.route('/sharpen_image', methods=['GET', 'POST'])
# Sharpen an image 
def sharpen_image():
    """
    Arguments:
        image_path : path to the image to be edited

    Function:
        Sharpens the given image and returns an image with depth as same as input image.

    Returns:
        path to sharpened image
    """
    try:
        image = request.json["image_path"]
        image = readb64(image)
        sharpened_image = cv2.filter2D(image, -1, SHARPEN_KERNEL)

        image_string = cv2.imencode('.png', sharpened_image)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')
        data = {"image_string": image_string}
        return data
    except Exception as e:
        logging.exception("Error occurred while sharpening the image.")
        return {"error": "An error occurred while sharpening the image."}, 500


@webapp.route('/blurr_image', methods=['GET', 'POST'])
# Blur an image based on the selected filter
def blurr_image():
    """
    Arguments:
        image_path : path to the image to be edited

    Function:
        Blurs the given image using OpenCV's blur which averages
        the pixel values based on the kernel size.

    Returns:
        path to blurred image
    """
    try:
        kernel_size = request.json["kernel_size"]
        filter_type = request.json["filter"]
        kernel = (kernel_size, kernel_size)
        image = request.json["image_path"]
        image = readb64(image)

        if filter_type == 'averaging':
            blurred_image = cv2.blur(image, kernel)
        elif filter_type == 'gaussian':
            blurred_image = cv2.GaussianBlur(image, kernel, 0)
        elif filter_type == 'median':
            blurred_image = cv2.medianBlur(image, kernel_size)

        image_string = cv2.imencode('.png', blurred_image)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')

        data = {"image_string": image_string}
        return data
    except Exception as e:
        logging.exception("Error occurred while blurring the image.")
        return {"error": "An error occurred while blurring the image."}, 500


@webapp.route('/rotate_image', methods=['GET', 'POST'])
# Rotate an image to the desired degree
def rotate_image():
    """
    Arguments:
        image_path : path to the image to be edited
        degree : degree to which the image should be rotated

    Function:
       Rotates an image to the desired degree.

    Returns:
        path to rotated image
    """
    try:
        image = request.json["image_path"]
        image = readb64(image)
        degree = request.json["degree"]
        rotated_image = imutils.rotate_bound(image, degree)

        image_string = cv2.imencode('.png', rotated_image)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')

        data = {"image_string": image_string}
        return data
    except Exception as e:
        logging.exception("Error occurred while rotating the image.")
        return {"error": "An error occurred while rotating the image."}, 500


@webapp.route('/threshold_image', methods=['GET', 'POST'])
# Adaptive Thresholding of an image using Gaussian filter
def threshold_image():
    """
    Arguments:
        image_path : path to the image to be edited

    Function:
        Applies the type of thresholding mentioned on the input image.

    Returns:
        path to thresholded image
    """
    try:
        image = request.json["image_path"]
        image = readb64(image)
        threshold_type = request.json["type"]
        image = cv2.medianBlur(image, 5)

        if threshold_type == 'Binary':
            ret, thresh = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        elif threshold_type == 'Adaptive':
            thresh = cv2.adaptiveThreshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 255, \
                                           cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        image_string = cv2.imencode('.png', thresh)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')

        data = {"image_string": image_string}
        return data
    except Exception as e:
        logging.exception("Error occurred while applying threshold to the image.")
        return {"error": "An error occurred while applying threshold to the image."}, 500


@webapp.route('/grayscale_image', methods=['GET', 'POST'])
# Convert the image to grayscale
def grayscale_image():
    """
    Arguments:
        image_path : path to the image to be edited

    Function:
        Change the color of the image to grayscale

    Returns:
        path to grayscale image
    """
    try:
        image = request.json["image_path"]
        image = readb64(image)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        image_string = cv2.imencode('.png', gray_image)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')

        data = {"image_string": image_string}
        return data
    except Exception as e:
        logging.exception("Error occurred while converting the image to grayscale.")
        return {"error": "An error occurred while converting the image to grayscale."}, 500


@webapp.route('/get_label', methods=['GET', 'POST'])
# Generate Labels for object Detection on image
def get_label():
    """
    Function:
        Generates labels for the input image
    Returns:
        path to image with bbox, detection labels
    """
    try:
        label_count = 3
        image = request.json["image"]
        image_cv = readb64(image)
        imgHeight, imgWidth, channels = image_cv.shape
        image = base64.b64decode(image)
        response = client.detect_labels(
            Image={
                'Bytes': image
            },
            MaxLabels=int(label_count),
            MinConfidence=80)

        res_response = {}
        for i in range(len(response['Labels'])):
            label_key = 'Label' + str(i)
            res_response[label_key] = {}
            res_response[label_key]['Name'] = response['Labels'][i]['Name']
            res_response[label_key]['Confidence'] = response['Labels'][i]['Confidence']
            if len(response['Labels'][i]['Instances']) == 0:
                res_response[label_key]['Instances'] = "Boundary Box Not Available"
            else:
                noOfBoundingBox = len(response['Labels'][i]["Instances"])
                for j in range(0, noOfBoundingBox):
                    dimensions = (response['Labels'][i]["Instances"][j]["BoundingBox"])
                    # Storing them in variables
                    boxWidth = dimensions['Width']
                    boxHeight = dimensions['Height']
                    boxLeft = dimensions['Left']
                    boxTop = dimensions['Top']
                    # Plotting points of rectangle
                    start_point = (int(boxLeft * imgWidth), int(boxTop * imgHeight))
                    end_point = (int((boxLeft + boxWidth) * imgWidth), int((boxTop + boxHeight) * imgHeight))
                    # Drawing Bounding Box on the coordinates
                    thickness = 2
                    color = (36, 255, 12)
                    image_cv = cv2.rectangle(image_cv, start_point, end_point, color, thickness)
                    cv2.putText(image_cv, response['Labels'][i]['Name'],
                                (int(boxLeft * imgWidth), (int(boxTop * imgHeight)) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                0.85,
                                color, thickness)
        image_string = cv2.imencode('.png', image_cv)[1].tostring()
        image_string = base64.b64encode(image_string).decode('utf-8')

        label_list = []
        confidence_list = []
        for label in response['Labels']:
            label_list.append(label['Name'])
            confidence_list.append(round(label['Confidence'], 2))

        data = {"image_string": image_string,
                "label_list": label_list,
                "confidence_list": confidence_list}
        return data
    except Exception as e:
        logging.exception("Error occurred while generating labels for the image.")
        return {"error": "An error occurred while generating labels for the image."}, 500
