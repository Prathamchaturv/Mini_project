import requests
import time
from send_fake_alert import make_fake_image
import os

def send_test_alert(message, alert_type, priority):
    try:
        # Create test image
        image_path = f"test_{int(time.time())}.jpg"
        make_fake_image(image_path)
        
        # Prepare the data
        url = "http://127.0.0.1:5501/upload-alert/"
        files = {"file": open(image_path, "rb")}
        data = {
            "message": message,
            "alert_type": alert_type,
            "priority": priority,
            "location": "Test Location"
        }
        
        # Send the request
        response = requests.post(url, data=data, files=files)
        response.raise_for_status()
        
        print(f"✅ Alert sent successfully:")
        print(f"   Message: {message}")
        print(f"   Type: {alert_type}")
        print(f"   Priority: {priority}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send alert: {str(e)}")
        return False
        
    finally:
        # Clean up
        files["file"].close()
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass

def run_quick_test():
    print("\n🚀 Starting Quick Alert System Test")
    print("==================================")
    
    test_cases = [
        {
            "message": "🚨 HIGH PRIORITY: Security breach detected",
            "type": "security",
            "priority": "high"
        },
        {
            "message": "⚠️ MEDIUM PRIORITY: Unusual activity in backyard",
            "type": "security",
            "priority": "normal"
        },
        {
            "message": "ℹ️ LOW PRIORITY: Door left open",
            "type": "general",
            "priority": "low"
        }
    ]
    
    success = 0
    total = len(test_cases)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📋 Running Test {i}/{total}")
        print("-" * 40)
        
        if send_test_alert(test["message"], test["type"], test["priority"]):
            success += 1
        
        if i < total:
            print("\n⏳ Waiting 2 seconds before next test...")
            time.sleep(2)
    
    print("\n📊 Test Summary")
    print("=============")
    print(f"Total Tests: {total}")
    print(f"Successful: {success}")
    print(f"Failed: {total - success}")
    print(f"Success Rate: {(success/total)*100:.1f}%")
    
    if success == total:
        print("\n✨ All tests passed successfully!")
    else:
        print("\n⚠️ Some tests failed, please check the logs above.")
    
    print("\n📱 Next Steps:")
    print("1. Open http://127.0.0.1:5501 in your browser")
    print("2. Verify that the test alerts appear in the dashboard")
    print("3. Check if alert priorities are correctly color-coded")
    print("4. Try marking some alerts as resolved")
    print("5. Test the filtering system")

if __name__ == "__main__":
    run_quick_test()