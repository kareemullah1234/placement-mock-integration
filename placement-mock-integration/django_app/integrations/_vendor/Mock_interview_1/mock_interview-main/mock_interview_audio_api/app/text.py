import os
import shutil

# Source and destination directories
source_dir = "C:/Users/hp/Desktop/transcription/audio"
destination_dir = "C:/Users/hp/Desktop/transcription/output"

# Ensure the destination directory exists
if not os.path.exists(destination_dir):
    os.makedirs(destination_dir)

# Loop through the files in the source directory
for file_name in os.listdir(source_dir):
    if file_name.endswith('.txt'):  # Check if the file is a text file
        # Full file path
        source_file = os.path.join(source_dir, file_name)
        destination_file = os.path.join(destination_dir, file_name)
        
        # Move the file
        shutil.move(source_file, destination_file)

print("All text files have been moved to the 'transcribed' folder.")
