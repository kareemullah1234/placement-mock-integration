import json
import tempfile
import os
from hdfs import InsecureClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HDFSClient:
    def __init__(self):
        self.config = settings.HDFS_CONFIG
        try:
            # Try primary connection
            self.client = InsecureClient(
                f'http://{self.config["HOST"]}:{self.config["PORT"]}/',
                user=self.config['USER'],# Add timeout
            )
            # Test connection
            self.client.list('/')
            logger.info(f"HDFS connection successful to {self.config['HOST']}:{self.config['PORT']}")
        except Exception as e:
            logger.error(f"HDFS connection failed: {e}")
            # Set client to None to handle gracefully
            self.client = None

    def is_connected(self):
        """Check if HDFS is connected"""
        return self.client is not None

    def get_student_folder_name(self, user, attempt_number):
        """Generate folder name: user_full_name_student_id_attempt_no"""
        # Sanitize full name for use in path
        full_name = f"{user.first_name}_{user.last_name}".replace(' ', '_').replace('.', '').replace('/', '')
        student_id = user.student_profile.student_id if hasattr(user, 'student_profile') else str(user.id)
        return f"{full_name}_{student_id}_attempt_{attempt_number}"

    def get_audio_filename(self, question_id, user, attempt_number):
        """Generate audio filename: question_id_student_name_attempt_no"""
        # Sanitize names for use in filename
        student_name = f"{user.first_name}_{user.last_name}".replace(' ', '_').replace('.', '').replace('/', '')
        return f"{question_id}_{student_name}_attempt_{attempt_number}.webm"

    def save_audio_response(self, audio_file, question_id, user, attempt_number):
        """Save audio response to HDFS with new structure"""
        try:
            # Create folder structure
            folder_name = self.get_student_folder_name(user, attempt_number)
            folder_path = f"/student_audio_responses/{folder_name}"

            # Ensure directory exists with string permission
            try:
                self.client.makedirs(folder_path, permission='755')  # Changed from 0o755
            except Exception as e:
                if "File exists" not in str(e) and "already exists" not in str(e):
                    logger.warning(f"Could not create HDFS directory {folder_path}: {e}")

            # Generate filename
            filename = self.get_audio_filename(question_id, user, attempt_number)
            hdfs_path = f"{folder_path}/{filename}"

            # Handle different file types
            if hasattr(audio_file, 'chunks'):
                # Django UploadedFile object
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    for chunk in audio_file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name

                # Upload to HDFS
                self.client.upload(hdfs_path, temp_file_path, overwrite=True)
                os.unlink(temp_file_path)
                
            elif hasattr(audio_file, 'read'):
                # File-like object
                audio_content = audio_file.read()
                return self.write_file(hdfs_path, audio_content)
                
            else:
                # Raw bytes
                return self.write_file(hdfs_path, audio_file)

            return hdfs_path

        except Exception as e:
            logger.error(f"Error saving audio to HDFS: {e}")
            return None

    def save_frames(self, frames_data, user, attempt_number):
        """Save video frames to HDFS with new structure"""
        try:
            # Create folder structure: /frames/user_full_name_student_id_attempt_no/
            folder_name = self.get_student_folder_name(user, attempt_number)
            folder_path = f"/frames/{folder_name}"

            # Ensure directory exists
            try:
                self.client.makedirs(folder_path)
            except Exception as e:
                # Handle case where directory already exists or other mkdir errors
                if "File exists" not in str(e): # Ignore "File exists" error
                    print(f"Warning: Could not create HDFS directory {folder_path}: {e}")

            # Generate filename
            filename = f"frames_{user.first_name}_{user.last_name}_attempt_{attempt_number}.json".replace(' ', '_').replace('.', '').replace('/', '')
            hdfs_path = f"{folder_path}/{filename}"

            # Save frames as JSON
            with self.client.write(hdfs_path, encoding='utf-8', overwrite=True) as writer:
                json.dump(frames_data, writer)

            return hdfs_path

        except Exception as e:
            print(f"Error saving frames to HDFS: {e}")
            raise

    def load_frames(self, hdfs_path):
        """Load frames from HDFS"""
        try:
            with self.client.read(hdfs_path, encoding='utf-8') as reader:
                return json.load(reader)

        except Exception as e:
            print(f"Error loading frames from HDFS: {e}")
            raise

    def download_file(self, hdfs_path):
        """Download file from HDFS with error handling"""
        if not self.is_connected():
            logger.error("HDFS not connected")
            return None

        try:
            with self.client.read(hdfs_path) as reader:
                return reader.read()

        except Exception as e:
            logger.error(f"Error downloading file from HDFS: {e}")
            return None

    def list_files(self, hdfs_path):
        """List files in HDFS directory with error handling"""
        if not self.is_connected():
            logger.error("HDFS not connected")
            return []

        try:
            return self.client.list(hdfs_path)
        except Exception as e:
            logger.error(f"Error listing files in HDFS: {e}")
            return []

    def get_student_audio_files(self, user, attempt_number):
        """Get all audio files for a specific student attempt"""
        try:
            folder_name = self.get_student_folder_name(user, attempt_number)
            folder_path = f"/student_audio_responses/{folder_name}"
            return self.client.list(folder_path)
        except Exception as e:
            print(f"Error getting student audio files: {e}")
            return []

    def get_student_frame_files(self, user, attempt_number):
        """Get frame files for a specific student attempt"""
        try:
            folder_name = self.get_student_folder_name(user, attempt_number)
            folder_path = f"/frames/{folder_name}"
            return self.client.list(folder_path)
        except Exception as e:
            print(f"Error getting student frame files: {e}")
            return []
    def write_file(self, hdfs_path, data):
        """Write data to HDFS file with corrected permissions"""
        if not self.is_connected():
            logger.error("HDFS not connected")
            return False
            
        try:
            logger.info(f"Starting HDFS write operation to: {hdfs_path}")
            
            if isinstance(data, str):
                data = data.encode('utf-8')

            # Create directory with string permission (octal)
            dir_path = '/'.join(hdfs_path.split('/')[:-1])
            
            if dir_path and dir_path != '/':
                try:
                    logger.info(f"Creating directory: {dir_path}")
                    # Use string representation of octal permission
                    self.client.makedirs(dir_path, permission='755')  # Instead of 0o755
                    logger.info(f"Directory created: {dir_path}")
                except Exception as mkdir_error:
                    if "File exists" not in str(mkdir_error) and "already exists" not in str(mkdir_error):
                        logger.error(f"Failed to create directory {dir_path}: {mkdir_error}")
                        return False

            # Write file with string permission
            logger.info(f"Writing file: {hdfs_path}")
            with self.client.write(hdfs_path, overwrite=True, permission='644') as writer:  # Instead of 0o644
                writer.write(data)
                
            logger.info(f"Successfully wrote {len(data)} bytes to HDFS: {hdfs_path}")
            
            # Verify file exists
            try:
                status = self.client.status(hdfs_path)
                logger.info(f"File verification successful. Size: {status['length']} bytes")
                return True
            except Exception as verify_error:
                logger.error(f"File verification failed: {verify_error}")
                return False

        except Exception as e:
            logger.error(f"Error writing to HDFS {hdfs_path}: {e}")
            return False
