import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

# We use the B2 S3-compatible API endpoint with explicit SigV4
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('B2_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('B2_KEY_ID'),
    aws_secret_access_key=os.getenv('B2_APPLICATION_KEY'),
    config=Config(signature_version='s3v4')
)

BUCKET_NAME = os.getenv('B2_BUCKET_NAME')
PUBLIC_PREFIX = os.getenv('B2_PUBLIC_URL_PREFIX', '').rstrip('/')

def upload_video_to_b2(file_path: str, filename: str) -> str:
    """Upload a file to B2 and return its public URL."""
    s3.upload_file(
        file_path, 
        BUCKET_NAME, 
        filename,
        ExtraArgs={'ContentType': 'video/mp4'}
    )
    return f"{PUBLIC_PREFIX}/{filename}"

def get_presigned_url(filename: str, expiration=3600) -> str:
    """Generate a temporary presigned URL for a private B2 bucket."""
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': filename},
        ExpiresIn=expiration
    )

