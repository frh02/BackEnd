import os
import numpy as np

# Use environment variables for sensitive information
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

if aws_access_key_id is None or aws_secret_access_key is None:
    raise ValueError("AWS access key and secret access key must be set as environment variables.")
    
# Define the sharpen kernel
SHARPEN_KERNEL = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
