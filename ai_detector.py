#!/usr/bin/env python3
"""
Simple AI detector using laptop camera + YOLOv8 (ultralytics) that sends alerts to the FastAPI backend.

Usage:
    python ai_detector.py --url http://127.0.0.1:5501/upload-alert/ --threshold 0.4 --cooldown 10

Requirements:
    pip install ultralytics opencv-python requests

Note: If YOLOv8 weights are not present the ultralytics package will download the default model (yolov8n).
"""
import argparse
import time
import os
import sys
import cv2
import requests

try:
    from ultralytics import YOLO
except Exception:
    print("ERROR: ultralytics package is required. Install with: pip install ultralytics")
    sys.exit(2)

DEFAULT_URL = "http://127.0.0.1:5501/upload-alert/"


def draw_boxes(frame, boxes, names):
    for b in boxes:
        x1, y1, x2, y2 = map(int, b.xyxy[0]) if hasattr(b, 'xyxy') else (0,0,0,0)
        conf = float(b.conf[0]) if hasattr(b, 'conf') else 0.0
        cls = int(b.cls[0]) if hasattr(b, 'cls') else 0
        label = names.get(cls, str(cls))
        color = (0, 255, 0) if label == 'person' else (255, 0, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}"
        cv2.putText(frame, text, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    return frame


def post_alert(url, image_path, message='Person detected', alert_type='security', priority='high'):
    try:
        with open(image_path, 'rb') as fh:
            files = {'file': ('alert.jpg', fh, 'image/jpeg')}
            data = {'message': message, 'alert_type': alert_type, 'priority': priority}
            resp = requests.post(url, data=data, files=files, timeout=10)
            print(f"Posted alert: status={resp.status_code}")
            return resp.status_code == 200 or resp.status_code == 201 or resp.status_code == 303
    except Exception as e:
        print('Failed to post alert:', e)
        return False


def main():
    p = argparse.ArgumentParser(description='AI detector - camera -> YOLOv8 -> backend')
    p.add_argument('--url', default=DEFAULT_URL, help='Upload endpoint URL')
    p.add_argument('--threshold', type=float, default=0.4, help='Confidence threshold')
    p.add_argument('--cooldown', type=float, default=10.0, help='Cooldown seconds after sending an alert')
    p.add_argument('--device', default=0, help='Camera device index or path')
    p.add_argument('--weights', default='yolov8n.pt', help='YOLOv8 weights (default: yolov8n.pt)')
    args = p.parse_args()

    # Load model
    print('Loading YOLO model...')
    model = YOLO(args.weights)
    names = model.model.names if hasattr(model, 'model') and hasattr(model.model, 'names') else {i: n for i, n in enumerate(model.names)}
    print('Model loaded, classes:', names)

    cap = cv2.VideoCapture(int(args.device) if str(args.device).isdigit() else args.device)
    if not cap.isOpened():
        print('Cannot open camera', args.device)
        sys.exit(1)

    last_sent = 0
    tmp_dir = os.path.join(os.getcwd(), 'simulator_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print('Failed to read frame from camera')
                break

            # Run detection
            results = model(frame, imgsz=640, conf=args.threshold)
            # results is a list; take first
            r = results[0]
            boxes = r.boxes
            person_detected = False
            if boxes is not None and len(boxes) > 0:
                for b in boxes:
                    cls = int(b.cls[0]) if hasattr(b, 'cls') else None
                    name = names.get(cls, str(cls))
                    conf = float(b.conf[0]) if hasattr(b, 'conf') else 0.0
                    if name == 'person' and conf >= args.threshold:
                        person_detected = True
                        break

            # Draw boxes for visualization
            try:
                vis = frame.copy()
                vis = draw_boxes(vis, boxes or [], names)
                cv2.imshow('AI Detector (press q to quit)', vis)
            except Exception:
                pass

            if person_detected and (time.time() - last_sent) > args.cooldown:
                timestamp = int(time.time())
                img_path = os.path.join(tmp_dir, f'detect_{timestamp}.jpg')
                cv2.imwrite(img_path, frame)
                ok = post_alert(args.url, img_path, message='Person detected by AI detector', alert_type='security', priority='high')
                if ok:
                    last_sent = time.time()
                # remove temp image
                try:
                    os.remove(img_path)
                except Exception:
                    pass

            # handle keypress
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
