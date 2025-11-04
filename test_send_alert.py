import sys
import os
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so `import main` works when running from simulator/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from PIL import Image
from io import BytesIO

client = TestClient(app)

def send_test_alert():
    img = Image.new('RGB', (400,300), '#2f2f2f')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)

    files = {'file': ('alert.jpg', buf, 'image/jpeg')}
    data = {'message': 'Automated test alert', 'alert_type': 'security', 'priority': 'high', 'location': 'Main Entrance'}

    resp = client.post('/upload-alert/', data=data, files=files)
    print('STATUS:', resp.status_code)
    print('BODY:', resp.text[:1000])
    return resp

if __name__ == '__main__':
    r = send_test_alert()
    assert r.status_code in (200, 201, 303), f"Unexpected status: {r.status_code}"
    print('Test completed successfully')
