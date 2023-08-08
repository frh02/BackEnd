# Simple Image Gallery WebApp

# About Project

This application is a “Cloud Image Gallery” which allows the user to upload images to the AWS cloud storage, browse images by key, view image gallery and perform image processing and recognition operations on them. We came up with this solution as it provides an entire package for image processing and image recognition in one place. The application provides multiple options to perform image processing and editing any image according to the user's choice and also leverages a powerful cloud object detection model for predicting different labels in any given image. Users can easily store processed images to our gallery. The front end of the project was deployed by zappa, while the back end part in another repository was deployed by Amazon EC2

![Screenshot](https://user-images.githubusercontent.com/52727328/221229125-53d868c9-fd97-4aeb-a1dc-cd51db46a59d.png)

The above image summarizes the different pages of the application. The description of the individual functions are given below:

The first page displays a set of 5 buttons linked to different tabs - Image Gallery, Upload image, Browse image, Image Processing and Image Recognition respectively.
Image Gallery: All the images stored in S3 bucket are displayed as a gallery.
Upload Image: You can upload an image from your local file system with a specific key to AWS S3 bucket using this feature.
Browse Image: This feature helps you to retrieve any image stored in the AWS S3 using its key.
Image Processing: We provided six image processing functions (resizing, sharpening, thresholding, color conversion, blurring, and image rotation). Users can upload images and specify the corresponding parameters for desired features to get the processed images. Users are also given an option to save the image in S3 after processing.
Image Recognition: This feature can be used to perform object detection on the image provided. This gives the label of the object detected and its confidence level.


Key components include:

* A web browser that initiates requests
* A web front end that manages requests and operations
* A local file system where all data is stored
* A mem-cache that provides faster access
* A DynamoDB database
