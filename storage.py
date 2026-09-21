import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def save_resume(file_obj):
    """
    Saves an uploaded resume either to local storage (default) or AWS S3.
    Returns the generated unique filename, or raises ValueError.
    """
    if not file_obj or file_obj.filename == '':
        raise ValueError("Please select a document to upload.")

    if not allowed_file(file_obj.filename):
        raise ValueError(f"Unsupported file format. Allowed types: {', '.join(sorted(Config.ALLOWED_EXTENSIONS)).upper()}")

    # Sanitize and create a collision-free filename
    orig_name = secure_filename(file_obj.filename)
    unique_prefix = uuid.uuid4().hex[:10]
    safe_filename = f"{unique_prefix}_{orig_name}"

    if Config.STORAGE_TYPE == 's3':
        # AWS S3 Storage handler (Isolated and disabled by default in Phase 1)
        if not Config.AWS_S3_BUCKET_NAME:
            raise ValueError("AWS S3 bucket name is not configured.")
        import boto3
        s3_client_args = {'region_name': Config.AWS_REGION}
        if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
            s3_client_args['aws_access_key_id'] = Config.AWS_ACCESS_KEY_ID
            s3_client_args['aws_secret_access_key'] = Config.AWS_SECRET_ACCESS_KEY

        s3 = boto3.client('s3', **s3_client_args)
        s3.upload_fileobj(
            file_obj,
            Config.AWS_S3_BUCKET_NAME,
            f"resumes/{safe_filename}",
            ExtraArgs={'ContentType': file_obj.content_type or 'application/octet-stream'}
        )
        return safe_filename
    else:
        # Local Storage handler (Default for Phase 1)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(Config.UPLOAD_FOLDER, safe_filename)
        file_obj.save(file_path)
        return safe_filename

def delete_resume(filename):
    """Safely removes a stored resume from local storage or S3."""
    if not filename:
        return

    if Config.STORAGE_TYPE == 's3':
        if Config.AWS_S3_BUCKET_NAME:
            import boto3
            s3_client_args = {'region_name': Config.AWS_REGION}
            if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
                s3_client_args['aws_access_key_id'] = Config.AWS_ACCESS_KEY_ID
                s3_client_args['aws_secret_access_key'] = Config.AWS_SECRET_ACCESS_KEY
            s3 = boto3.client('s3', **s3_client_args)
            try:
                s3.delete_object(Bucket=Config.AWS_S3_BUCKET_NAME, Key=f"resumes/{filename}")
            except Exception:
                pass
    else:
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

def get_file_path(filename):
    """Returns the local path for a saved resume."""
    return os.path.join(Config.UPLOAD_FOLDER, filename)
