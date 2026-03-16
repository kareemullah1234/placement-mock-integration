import urllib.request
import os

url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_smile.xml"
output_file = "/app/open_cv/haarcascade_smile.xml"

try:
    print("Downloading smile cascade...")
    urllib.request.urlretrieve(url, output_file)
    print(f"✅ Downloaded to {output_file}")
    print(f"📊 File size: {os.path.getsize(output_file)} bytes")
except Exception as e:
    print(f"❌ Download failed: {e}")
