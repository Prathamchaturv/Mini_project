#!/usr/bin/env python3
"""
Motion detector using laptop camera (OpenCV). On motion it saves a frame and posts it to the FastAPI backend upload endpoint.

Usage:
    python motion_detector.py --url http://127.0.0.1:5501/upload-alert/ --min-area 500 --cooldown 5

Requirements:
    pip install opencv-python requests

Notes:
- This uses simple frame differencing; it's lightweight and works without a heavy ML model.
- Set --headless to avoid opening a preview window (useful on headless systems).
"""
import argparse
import time
import os
import sys
import cv2
import requests

DEFAULT_URL = "http://127.0.0.1:5501/upload-alert/"


def post_alert(url, image_path, message='Motion detected', alert_type='security', priority='normal'):
    try:
        with open(image_path, 'rb') as fh:
            files = {'file': ('alert.jpg', fh, 'image/jpeg')}
            data = {'message': message, 'alert_type': alert_type, 'priority': priority}
            resp = requests.post(url, data=data, files=files, timeout=10)
            print(f"Posted alert: status={resp.status_code}")
            return resp.status_code in (200,201,303)
    except Exception as e:
        print('Failed to post alert:', e)
        return False


def main():
    parser = argparse.ArgumentParser(description='Simple motion detector that posts images to a backend')
    parser.add_argument('--url', default=DEFAULT_URL, help='Upload endpoint URL')
    parser.add_argument('--device', default=0, help='Camera device index (default 0)')
    parser.add_argument('--min-area', type=int, default=500, help='Minimum area size in pixels to consider motion')
    parser.add_argument('--threshold', type=int, default=25, help='Threshold to binarize difference image')
    parser.add_argument('--cooldown', type=float, default=5.0, help='Seconds to wait after sending an alert')
    parser.add_argument('--headless', action='store_true', help='Run without preview window')
    args = parser.parse_args()

    cap = cv2.VideoCapture(int(args.device) if str(args.device).isdigit() else args.device)
    if not cap.isOpened():
        print('Error: cannot open camera', args.device)
        sys.exit(1)

    # Use the first frame as background reference (grayscale, blurred)
    ret, frame = cap.read()
    if not ret:
        print('Error: cannot read from camera')
        sys.exit(1)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    last_sent = 0
    tmp_dir = os.path.join(os.getcwd(), 'simulator_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    print('Starting motion detector. Press q in the preview window to quit.')
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

            # Compute difference between background and current frame
            frame_delta = cv2.absdiff(gray, gray_frame)
            thresh = cv2.threshold(frame_delta, args.threshold, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            motion_found = False
            for c in contours:
                if cv2.contourArea(c) < args.min_area:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                motion_found = True

            # Display preview unless headless
            if not args.headless:
                cv2.imshow('Motion Detector (q to quit)', frame)

            # If motion found and cooldown elapsed, send alert
            if motion_found and (time.time() - last_sent) > args.cooldown:
                timestamp = int(time.time())
                image_path = os.path.join(tmp_dir, f'motion_{timestamp}.jpg')
                cv2.imwrite(image_path, frame)
                ok = post_alert(args.url, image_path, message='Motion detected', alert_type='security', priority='normal')
                if ok:
                    last_sent = time.time()
                try:
                    os.remove(image_path)
                except Exception:
                    pass

            # Update background slowly to adapt to lighting changes
            # Here we do running average using a small alpha
            gray = cv2.addWeighted(gray, 0.95, gray_frame, 0.05, 0)

            # quit key
            if not args.headless:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
