import base64
import os
import logging
from flask import render_template, request, g, redirect, url_for
from FrontEnd import webapp
from flask_paginate import Pagination
import json
from FrontEnd.memcache import subPUT, subCLEAR, subInvalidateKey, subGET
from botocore.exceptions import ClientError
import boto3
from FrontEnd.config import ConfigAWS
import requests

# Configure logging
logging.basicConfig(filename='image_processing.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.gif', '.tif', '.bmp', '.raw', '.cr2', '.nef', '.orf', '.sr2',
                      '.psd', '.xcf', '.ai', 'cdr'}
global bucket
bucket_name = 'images'
s3_boto = boto3.resource('s3',
                         region_name='us-east-1',
                         aws_access_key_id=ConfigAWS["aws_access_key_id"],
                         aws_secret_access_key=ConfigAWS['aws_secret_access_key'])
dynamodb = boto3.resource('dynamodb', region_name='us-east-1',
                          aws_access_key_id=ConfigAWS["aws_access_key_id"],
                          aws_secret_access_key=ConfigAWS['aws_secret_access_key'])
global table
global results
global URL

# Function to check if the file exists in the bucket
def checkKeyBucket(file):
    """Check if the file exists in the S3 bucket.

    Args:
        file (str): The file name (Key) to check in the S3 bucket.

    Returns:
        bool: True if the file exists in the bucket, False otherwise.
    """
    try:
        s3_boto.meta.client.head_object(Bucket=bucket_name, Key=file)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        logging.error(f"Error checking S3 bucket: {e}")
        raise


def processDuplicateFilename(filename):
    """If a duplicate file name is found, add a number after it to make it unique.

    Args:
        filename (str): The original filename to process.

    Returns:
        str: The final unique filename after handling duplicates.
    """
    finalName = filename
    count = 1
    if checkKeyBucket(finalName):
        name, extension = os.path.splitext(finalName)
        finalName = name + str(count) + extension
    while checkKeyBucket(finalName):
        count = count + 1
        name, extension = os.path.splitext(finalName)
        finalName = name[:-1] + str(count) + extension
    return finalName


def upload_to_S3(image_path):
    """Upload the image to the S3 bucket.

    If the filename already exists in the bucket, it handles the duplicate filename scenario
    by adding a unique number after the filename.

    Args:
        image_path (FileStorage): The uploaded image file object.

    Returns:
        str: The S3 object key (file path) where the image is saved.
    """
    filename = "image/" + image_path.filename
    # save image to s3
    try:
        s3_boto.meta.client.upload_fileobj(image_path, bucket_name, filename)
    except ClientError as e:
        return redirect(url_for('failure', msg="Upload error"))

    return filename


@webapp.route('/delete_table', methods=['GET', 'POST'])
def delete_table():
    """Delete the DynamoDB table 'images' if it exists.

    This function deletes the table 'images' and waits until the table is deleted before returning.

    Returns:
        Redirect: Redirects to the 'failure' page if there's an error, otherwise, returns None.
    """
    try:
        response = dynamodb.meta.client.delete_table(TableName='images')
        waiter = dynamodb.meta.client.get_waiter('table_not_exists')
        waiter.wait(TableName="images")
    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        pass
    except Exception as e:
        logging.error(f"Error deleting table: {e}")
        return redirect(url_for('failure', msg="Error deleting table"))

@webapp.route('/truncate_table', methods=['GET', 'POST'])
def truncate_table():
    """Empty the DynamoDB table 'images'.

    This function scans all items in the 'images' table and deletes them in batches.

    Returns:
        Redirect: Redirects to the 'failure' page if there's an error, otherwise, returns None.
    """
    try:
        scan = table.scan()
        with table.batch_writer() as batch:
            for each in scan['Items']:
                batch.delete_item(
                    Key={
                        'image_key': each['image_key']
                    }
                )
    except Exception as e:
        logging.error(f"Error truncating table: {e}")
        return redirect(url_for('failure', msg="Error truncating table"))

@webapp.route('/create_table', methods=['GET', 'POST'])
def create_table():
    """Create the DynamoDB table 'images' if it does not exist.

    This function creates the table 'images' with a primary key 'image_key' if it does not already exist.

    Returns:
        Redirect: Redirects to the 'failure' page if there's an error, otherwise, returns a JSON response.
    """
    try:
        new_table = dynamodb.create_table(
            TableName='images',
            KeySchema=[
                {
                    'AttributeName': 'image_key',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'image_key',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        # wait until the table is created
        waiter = dynamodb.meta.client.get_waiter('table_exists')
        waiter.wait(TableName='images')
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        pass
    except Exception as e:
        logging.error(f"Error creating table: {e}")
        return redirect(url_for('failure', msg="Error creating table"))

    global table
    table = dynamodb.Table('images')
    data = {
        "success": "true",
    }
    response = webapp.response_class(
        response=json.dumps(data),
        status=200,
        mimetype='application/json')
    return response

@webapp.route('/clearImageData', methods=['GET', 'POST'])
def clearImageData():
    """Clear all image data from the S3 bucket and DynamoDB table 'images'.

    This function deletes all objects in the S3 bucket and empties the 'images' table in DynamoDB.

    Returns:
        Response: A JSON response indicating the success or failure of the data clearing process.
    """
    try:
        # clear s3 data
        bucket.objects.all().delete()
        truncate_table()
        data = {
            "success": "true",
        }
        response = webapp.response_class(
            response=json.dumps(data),
            status=200,
            mimetype='application/json')
    except Exception as e:
        logging.error(f"Error clearing image data: {e}")
        data = {
            "success": "false",
            "error": {
                "code": 500,
                "message": "Clear Data Error"
            }}
        response = webapp.response_class(
            response=json.dumps(data),
            status=500,
            mimetype='application/json')
    return response

def waitTableActive():
    """Wait until the DynamoDB table 'images' is in the 'ACTIVE' state.

    This function continuously checks the status of the 'images' table until it becomes active.

    Returns:
        None: Once the table becomes active, the function returns.
    """
    while True:
        response = dynamodb.meta.client.describe_table(
            TableName='images'
        )
        if response['Table']['TableStatus'] == 'ACTIVE':
            break


@webapp.before_first_request
def runOnAppStart():
    """This function is executed before the first request to the Flask app.

    It creates or retrieves the S3 bucket 'group-31-images', clears the image data from the S3 bucket,
    creates the DynamoDB table 'images', and stores the public IP address in the 'URL' variable.

    Returns:
        None: This function only performs setup tasks on app start.
    """
    global bucket
    # either create a new bucket or return existing bucket if already exists
    bucket = s3_boto.create_bucket(Bucket=bucket_name)
    # clean images in the s3 bucket upon application start
    # bucket.objects.all().delete()
    # clearImageData()
    create_table()
    ec2_client = boto3.resource('ec2', aws_access_key_id=ConfigAWS["aws_access_key_id"],
                                aws_secret_access_key=ConfigAWS['aws_secret_access_key'])

    instance = ec2_client.Instance("i-0c841e13abbf09d94")
    public_IP = instance.public_ip_address
    global URL
    URL = "http://" + public_IP + ":5001"


def allowed_file(filename):
    """Check if the file type is allowed.

    This function checks if the given filename has an allowed file extension based on the ALLOWED_EXTENSIONS set.

    Args:
        filename (str): The name of the file to be checked.

    Returns:
        bool: True if the file type is allowed, False otherwise.
    """
    return '.' in filename and ('.' + filename.rsplit('.', 1)[1]) in ALLOWED_EXTENSIONS


@webapp.route('/')
@webapp.route('/home')
def home():
    """Render the homepage.

    Returns:
        Rendered Template: The rendered HTML template for the homepage.
    """
    return render_template("home.html")


@webapp.route('/success')
def success():
    """Render the success page.

    Returns:
        Rendered Template: The rendered HTML template for the success page.
    """
    msg = request.args.get('msg')
    return render_template("success.html", msg=msg)


@webapp.route('/failure')
def failure():
    """Render the failure page.

    Returns:
        Rendered Template: The rendered HTML template for the failure page.
    """
    msg = request.args.get('msg')
    return render_template("failure.html", msg=msg)


def get_images(offset=0, per_page=4):
    """Get images from the DynamoDB table 'images' with pagination.

    This function retrieves images from the 'images' table in DynamoDB and paginates the results.

    Args:
        offset (int, optional): The starting index for pagination. Defaults to 0.
        per_page (int, optional): The number of images per page. Defaults to 4.

    Returns:
        list: A list of images with the specified pagination settings.
    """
    response = table.scan()
    global results
    results = response['Items']
    for i in range(len(results)):
        path = results[i]['image_path']
        try:
            obj = bucket.Object(path)
            base64_image = base64.b64encode(obj.get()['Body'].read()).decode('utf-8')
            results[i]['image_path'] = base64_image
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return redirect(url_for('failure', msg="Key not exist in S3 error"))
    return results[offset: offset + per_page]


@webapp.route('/image_gallery', methods=['GET', 'POST'])
def image_gallery():
    """Render the image gallery page.

    Returns:
        Rendered Template: The rendered HTML template for the image gallery page.
    """

    page = int(request.args.get('page', 1))
    per_page = 4
    offset = (page - 1) * per_page

    pagination_images = get_images(offset=offset, per_page=4)
    pagination = Pagination(page=page, per_page=4, total=len(results), css_framework="bootstrap5")
    return render_template("image_gallery.html",
                           images=pagination_images,
                           page=page,
                           per_page=per_page,
                           pagination=pagination)


@webapp.route('/retrieve_key_form')
def retrieve_key_form():
    """Display an empty HTML form that allows users to browse images by key.

    Returns:
        Rendered Template: The rendered HTML template for the key retrieval form.
    """
    return render_template("key_form.html")


@webapp.route('/key', methods=['POST'])
def key():
    """Display the image that the user browsed by key.

    Returns:
        Rendered Template: The rendered HTML template for displaying the image by key.
    """
    if request.method == 'POST':
        image_key = request.form['key']
    else:
        return redirect(url_for('failure', msg="Method not allowed"))

    if not image_key:
        return redirect(url_for('failure', msg="Key is not given"))

    if image_key == '':
        return redirect(url_for('failure', msg="Key is empty"))

    # get image directly if in cache
    res = subGET(image_key)
    if res:
        return render_template('show_image.html', key=image_key, image=res)

    # if image not in cache, get image from database
    # check if database has the key or not
    response = dynamodb.meta.client.get_item(
        TableName="images",
        Key={
            'image_key': image_key
        }
    )

    # database has the key, store the image key and the encoded image content pair in cache for next retrieval
    if 'Item' in response:
        path = response['Item']['image_path']
        try:
            obj = bucket.Object(path)
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return redirect(url_for('failure', msg="Key not exist in S3 error"))
        base64_image = base64.b64encode(obj.get()['Body'].read()).decode('utf-8')
        # put image in memcache
        res = subPUT(image_key, base64_image)
        if res:
            return render_template('show_image.html', key=image_key, image=base64_image)
        else:
            return redirect(url_for('failure', msg="Memcache Put Error"))
    else:
        return redirect(url_for('failure', msg="Unknown Key"))


@webapp.route('/upload_form')
def upload_form():
    """Display an empty HTML form that allows users to upload a new key-image pair.

    Returns:
        Rendered Template: The rendered HTML template for the upload form.
    """
    return render_template("upload_form.html")


@webapp.route('/upload', methods=['POST'])
def upload():
    """Upload the key-image pair, store the image in the S3 bucket, and save the file location in the database.

    Returns:
        Redirect: Redirects to the success page if the image upload is successful, or the failure page otherwise.
    """
    if request.method == 'POST':
        image_key = request.form['key']
        image_file = request.files['file']
    else:
        return redirect(url_for('failure', msg="Method not allowed"))

    if not image_file or not image_key:
        return redirect(url_for('failure', msg="Missing image file or key"))

    # check if file is empty
    if image_file.filename == '' or image_key == '':
        return redirect(url_for('failure', msg="Image file or key is empty"))

    # check if the uploaded file type is allowed
    if not allowed_file(image_file.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    # check if database has the key or not
    response = dynamodb.meta.client.get_item(
        TableName="images",
        Key={
            'image_key': image_key
        }
    )
    # handle duplicate filename
    filename = "userImages/" + processDuplicateFilename(image_file.filename)

    # if the database has the key, delete the associated image in the s3 bucket
    # save new image in s3 bucket
    # and replace the old file name in the database with the new one
    if 'Item' in response:
        rows = response['Item']
        file_to_delete = rows['image_path']
        s3_boto.Object(bucket_name, file_to_delete).delete()
        try:
            s3_boto.meta.client.upload_fileobj(image_file, bucket_name, filename)
        except ClientError as e:
            return redirect(url_for('failure', msg="S3 Upload error"))
        try:
            response = table.update_item(
                Key={
                    'image_key': image_key
                },
                UpdateExpression="set image_path = :p",
                ExpressionAttributeValues={
                    ':p': filename
                })
        except ClientError as err:
            return redirect(url_for('failure', msg="DB Update error"))

    # if database doesn't have the key, insert key, image pair into it.
    # save new image in s3 bucket
    else:
        try:
            s3_boto.meta.client.upload_fileobj(image_file, bucket_name, filename)
        except ClientError as e:
            return redirect(url_for('failure', msg="Upload error"))
        try:
            response = table.put_item(
                Item={
                    'image_key': image_key,
                    'image_path': filename
                }
            )
        except ClientError as err:
            return redirect(url_for('failure', msg="DB Put error"))
    res = subInvalidateKey(image_key)
    if not res:
        return redirect(url_for('failure', msg="Invalidate key error"))
    else:
        waitTableActive()
        return redirect(url_for('success', msg="Image Successfully Uploaded"))


@webapp.route('/clear_data')
def clear_data():
    """Clear image data and redirect to the success page.

    Returns:
        Redirect: Redirects to the success page if the data clearing is successful, or the failure page otherwise.
    """
    clearImageData()
    res = subCLEAR()
    if not res:
        return redirect(url_for('failure', msg="Memcache data clearing error"))
    return redirect(url_for('success', msg="All Image Data Cleared Successfully"))


"""Image Processing Part"""


@webapp.route('/image_edits')
def image_edits():
    """Render the image edits form.

    Returns:
        Rendered Template: The rendered HTML template for the image edits form.
    """
    return render_template('image_edits.html')


@webapp.route('/save_image', methods=['POST'])
def save_image():
    """Save the edited image after applying various image processing techniques.

    Returns:
        Rendered Template: The rendered HTML template for displaying the edited image.
    """
    image_key = request.form['key']
    image_path = "userImages/" + image_key
    image_string = request.form['image']
    image_string = base64.b64decode(image_string)
    # check if database has the key or not
    response = dynamodb.meta.client.get_item(
        TableName="images",
        Key={
            'image_key': image_key
        }
    )
    # if the database has the key, delete the associated image in the s3 bucket
    # save new image in s3 bucket
    # and replace the old file name in the database with the new one
    if 'Item' in response:
        rows = response['Item']
        file_to_delete = rows['image_path']
        s3_boto.Object(bucket_name, file_to_delete).delete()
        try:
            s3_boto.meta.client.put_object(Bucket=bucket_name, Key=image_path, Body=image_string)
        except ClientError as e:
            return redirect(url_for('failure', msg="S3 Upload error"))
        try:
            response = table.update_item(
                Key={
                    'image_key': image_key
                },
                UpdateExpression="set image_path = :p",
                ExpressionAttributeValues={
                    ':p': image_path
                })
        except ClientError as err:
            return redirect(url_for('failure', msg="DB Update error"))

    # if database doesn't have the key, insert key, image pair into it.
    # save new image in s3 bucket
    else:
        try:
            s3_boto.meta.client.put_object(Bucket=bucket_name, Key=image_path, Body=image_string)
        except ClientError as e:
            return redirect(url_for('failure', msg="Upload error"))
        try:
            response = table.put_item(
                Item={
                    'image_key': image_key,
                    'image_path': image_path
                }
            )
        except ClientError as err:
            return redirect(url_for('failure', msg="DB Put error"))
    return render_template('success.html', msg="Image Saved successfully")


@webapp.route('/resize_form')
def resize_form():
    """Render the resize form.

    Returns:
        Rendered Template: The rendered HTML template for the image resize form.
    """
    return render_template('resize_form.html')


@webapp.route('/image_resize', methods=["POST"])
def resize():
    """Resize the image based on user input and display the resized image.

    Returns:
        Rendered Template: The rendered HTML template for displaying the resized image.
    """
    if request.method == "POST":
        image_path = request.files['file']
        width = request.form['width']
        height = request.form['height']
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path or not width or not height:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '' or width == '' or height == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))
    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image_path": image, "width": int(width), "height": int(height)}
    res = requests.post(URL + "/resize_image",
                        json=dataSend)
    content = res.json()["image_string"]
    return render_template('show_image_resize.html', key=image_path, image=content)


"""Sharpen"""


@webapp.route('/sharpen_form')
def sharpen_form():
    """Render the sharpen form.

    Returns:
        Rendered Template: The rendered HTML template for the sharpen form.
    """
    return render_template('sharpen_form.html')


@webapp.route('/image_sharpen', methods=["POST"])
def sharpen():
    """Apply sharpening to the image and display the sharpened image.

    Returns:
        Rendered Template: The rendered HTML template for displaying the sharpened image.
    """
    if request.method == "POST":
        image_path = request.files['file']
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image_path": image}
    res = requests.post(URL + "/sharpen_image",
                        json=dataSend)
    content = res.json()["image_string"]
    return render_template('show_image_after_process.html', key=image_path, image=content)


"""Blur"""


@webapp.route('/blurr_form')
def blurr_form():
    """Render the blur form.

    Returns:
        Rendered Template: The rendered HTML template for the blur form.
    """
    return render_template('blurr_form.html')


@webapp.route('/image_blur', methods=["GET", "POST"])
def blur():
    """Apply blur to the image based on user input and display the blurred image.

    Returns:
        Rendered Template: The rendered HTML template for displaying the blurred image.
    """
    if request.method == "POST":
        image_path = request.files['file']
        kernel_size = int(request.form['kernel_size'])
        image_type = request.form.get('filter_type')
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path or not image_type:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '' or image_type == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    if (image_type == 'gaussian' or image_type == 'median') and (kernel_size % 2 == 0):
        print("here")
        return redirect(url_for('failure', msg="Kernel size should be an odd number for gaussian and median mode"))

    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image_path": image, "kernel_size": kernel_size, "filter": image_type}
    res = requests.post(URL + "/blurr_image",
                        json=dataSend)
    content = res.json()["image_string"]
    return render_template('show_image_after_process.html', key=image_path, image=content)


"""Rotate Image"""


@webapp.route('/rotate_form')
def rotate_form():
    """Render the rotate form.

    Returns:
        Rendered Template: The rendered HTML template for the rotate form.
    """
    return render_template('rotate_form.html')


@webapp.route('/image_rotate', methods=["POST"])
def rotate():
    """Rotate the image based on user input and display the rotated image.

    Returns:
        Rendered Template: The rendered HTML template for displaying the rotated image.
    """
    if request.method == "POST":
        image_path = request.files['file']
        degree = request.form['degree']
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path or not degree:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '' or degree == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image_path": image, "degree": int(degree)}
    res = requests.post(URL + "/rotate_image",
                        json=dataSend)
    content = res.json()["image_string"]
    return render_template('show_image_after_process.html', key=image_path, image=content)


"""GrayScale"""


@webapp.route('/grayscale_form')
def grayscale_form():
    """Render the grayscale form.

    Returns:
        Rendered Template: The rendered HTML template for the grayscale form.
    """
    return render_template('grayscale_form.html')


@webapp.route('/image_convert', methods=["POST"])
def grayscale():
    """Convert the image to grayscale and display the grayscale image.

    Returns:
        Rendered Template: The rendered HTML template for displaying the grayscale image.
    """
    if request.method == "POST":
        image_path = request.files['file']
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image_path": image}
    res = requests.post(URL + "/grayscale_image",
                        json=dataSend)
    content = res.json()["image_string"]
    return render_template('show_image_after_process.html', key=image_path, image=content)


"""Threshold"""


@webapp.route('/threshold_form')
def threshold_form():
    """Render the threshold form.

    Returns:
        Rendered Template: The rendered HTML template for the threshold form.
    """
    return render_template('threshold_form.html')


@webapp.route('/image_threshold', methods=["GET", "POST"])
def threshold():
    """Apply thresholding to the image based on user input and display the thresholded image.

    Returns:
        Rendered Template: The rendered HTML template for displaying the thresholded image.
    """
    if request.method == "POST":
        image_path = request.files['file']
        image_type = request.form.get('threshold_type')
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path or not image_type:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '' or image_type == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image_path": image, "type": image_type}
    res = requests.post(URL + "/threshold_image",
                        json=dataSend)
    content = res.json()["image_string"]
    return render_template('show_image_after_process.html', key=image_path, image=content)


@webapp.route('/image_label_form')
def image_label_form():
    """Render the image label form.

    Returns:
        Rendered Template: The rendered HTML template for the image label form.
    """
    return render_template('image_label_form.html')


@webapp.route('/detection', methods=['POST'])
def detection():
    """Detect objects in the image using a pre-trained model and display the image with bounding boxes.

    Returns:
        Rendered Template: The rendered HTML template for displaying the image with bounding boxes.
    """
    if request.method == "POST":
        image_path = request.files['file']
    else:
        return redirect(url_for('failure', msg="Method not allowed!"))

    if not image_path:
        return redirect(url_for('failure', msg="Missing information!"))

    if image_path.filename == '':
        return redirect(url_for('failure', msg="Fields cannot be empty!"))

    if not allowed_file(image_path.filename):
        return redirect(url_for('failure', msg="Image file type not supported"))

    image_path = upload_to_S3(image_path)
    image = bucket.Object(image_path).get()['Body'].read()
    image = base64.b64encode(image).decode('utf-8')

    dataSend = {"image": image}
    res = requests.post(URL + "/get_label",
                        json=dataSend)
    content = res.json()["image_string"]
    label_list = res.json()["label_list"]
    confidence_list = res.json()["confidence_list"]

    return render_template('show_label.html', key=image_path, content=content, labels=label_list,
                           image=image, confidence=confidence_list)
