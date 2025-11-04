import requests
from PIL import Image, ImageDraw
import argparse
import os
import sys
import time
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_URL = "http://127.0.0.1:5501/upload-alert/"

def make_fake_image(path: str):
    import requests
    from PIL import Image, ImageDraw
    import argparse
    import os
    import sys
    import time
    import urllib3

    # Disable SSL warnings for local testing
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    DEFAULT_URL = "http://127.0.0.1:5501/upload-alert/"


    def make_fake_image(path: str):
        """Create a simple test image and save to `path`."""
        img = Image.new("RGB", (400, 300), color="#2f2f2f")
        draw = ImageDraw.Draw(img)

        # Draw a simplified person silhouette
        x, y = 200, 150
        draw.ellipse([x - 20, y - 60, x + 20, y - 20], fill="#808080")
        draw.rectangle([x - 30, y - 20, x + 30, y + 60], fill="#808080")
        draw.rectangle([x - 25, y + 60, x - 5, y + 120], fill="#808080")
        draw.rectangle([x + 5, y + 60, x + 25, y + 120], fill="#808080")

        # Ensure directory exists
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        img.save(path, quality=95)


    def send_alert(api_url: str, image_path: str, message: str, alert_type: str = 'security', priority: str = 'high') -> bool:
        """Send an alert (image + form fields) to the API. Returns True on success."""
        max_retries = 3
        retry_delay = 2

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Sending alert to {api_url} (attempt {attempt}/{max_retries})")
                with open(image_path, 'rb') as fh:
                    files = {'file': ('alert.jpg', fh, 'image/jpeg')}
                    data = {
                        'message': message,
                        'alert_type': alert_type,
                        'priority': priority,
                        'location': 'Main Entrance'
                    }

                    session = requests.Session()
                    resp = session.post(api_url, data=data, files=files, timeout=30, verify=False)
                    print(f"Response: {resp.status_code} {resp.reason}")
                    # Print a short excerpt of response for debugging
                    text = (resp.text or '')
                    print(f"Body (excerpt): {text[:200]}")
                    resp.raise_for_status()

                print("Alert sent successfully")
                return True

            except requests.exceptions.RequestException as e:
                print(f"Request failed (attempt {attempt}): {e}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("Max retries exceeded")
                    return False

            except Exception as e:
                print(f"Unexpected error sending alert: {e}")
                return False


    def main() -> int:
        p = argparse.ArgumentParser(description="Send a test alert to the dashboard API")
        p.add_argument('--url', default=DEFAULT_URL, help='Full endpoint URL')
        p.add_argument('--message', default='Security Alert (Test)', help='Alert message')
        p.add_argument('--type', default='security', choices=['security', 'environmental', 'general'], help='Type of alert')
        p.add_argument('--priority', default='high', choices=['high', 'normal', 'low'], help='Alert priority')
        p.add_argument('--out', default='test_alert.jpg', help='Output image file name')

        args = p.parse_args()

        image_path = args.out

        # If user provided a filename without dir, save to current simulator dir
        if not os.path.isabs(image_path):
            image_path = os.path.join(os.getcwd(), image_path)

        try:
            make_fake_image(image_path)
        except Exception as e:
            print(f"Failed to create test image: {e}")
            return 2

        success = send_alert(args.url, image_path, args.message, args.type, args.priority)

        if success:
            print('\nTest Results:')
            print('-------------')
            print('1. Alert sent successfully')
            print('2. Image uploaded')
            print(f'3. Alert type: {args.type}')
            print(f'4. Priority: {args.priority}')
            print('\nNext Steps:')
            print('1. Open http://127.0.0.1:5501 in your browser')
            print('2. Check the dashboard for the new alert')

        # Cleanup
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Warning: could not remove temp image: {e}")

        return 0 if success else 1


    if __name__ == '__main__':
        sys.exit(main())
