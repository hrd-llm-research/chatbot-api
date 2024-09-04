from minio import Minio
from minio.error import S3Error

minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False # Set to True if you have configured TLS/SSL
)

def upload_file(bucket_name: str,object_name, file: str):
    """"
        Upload a file to MinIO storage
    """
    try:

        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)    

        # add file object into the bucket
        minio_client.fput_object(
            bucket_name,
            object_name,
            file,
        )
    except S3Error as e:
        raise e
    
def download_file_from_MinIO(bucket_name:str, file_name:str, savepath:str):

    try:
        minio_client.fget_object(bucket_name, file_name, savepath)
    except:
        raise