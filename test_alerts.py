import time
from send_fake_alert import send_alert, make_fake_image
import os

def run_alert_tests():
    print("Starting Alert System Tests...")
    print("==============================")
    
    # Test scenarios
    test_cases = [
        {
            "message": "🚨 Intruder detected in garage",
            "type": "security",
            "priority": "high",
            "expected_time": 2
        },
        {
            "message": "⚠️ Smoke detected in kitchen",
            "type": "environmental",
            "priority": "high",
            "expected_time": 2
        },
        {
            "message": "📢 Motion detected in backyard",
            "type": "security",
            "priority": "normal",
            "expected_time": 2
        },
        {
            "message": "ℹ️ Door left open",
            "type": "general",
            "priority": "low",
            "expected_time": 2
        }
    ]
    
    success_count = 0
    api_url = "http://127.0.0.1:5501/upload-alert/"
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test['type'].title()} Alert - {test['priority'].upper()} Priority")
        print("-" * 50)
        
        # Create test image
        image_path = f"test_alert_{i}.jpg"
        make_fake_image(image_path)
        
        # Send alert
        start_time = time.time()
        success = send_alert(
            api_url=api_url,
            image_path=image_path,
            message=test['message'],
            alert_type=test['type'],
            priority=test['priority']
        )
        end_time = time.time()
        
        # Clean up test image
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception:
            pass
        
        # Verify results
        response_time = end_time - start_time
        if success:
            success_count += 1
            print(f"✅ Alert sent successfully")
            print(f"⏱️ Response time: {response_time:.2f}s")
            if response_time > test['expected_time']:
                print(f"⚠️ Warning: Response time higher than expected ({test['expected_time']}s)")
        else:
            print(f"❌ Alert failed to send")
        
        # Wait between tests
        if i < len(test_cases):
            print("\nWaiting 2 seconds before next test...")
            time.sleep(2)
    
    # Print summary
    print("\nTest Summary")
    print("============")
    print(f"Total Tests: {len(test_cases)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(test_cases) - success_count}")
    print(f"Success Rate: {(success_count/len(test_cases))*100:.1f}%")
    
    print("\nNext Steps:")
    print("1. Open http://127.0.0.1:5501 in your browser")
    print("2. Verify that all test alerts appear in the dashboard")
    print("3. Check alert priorities and types are correct")
    print("4. Verify images are displayed properly")
    print("5. Test alert interaction (marking as resolved, adding notes)")

if __name__ == "__main__":
    run_alert_tests()