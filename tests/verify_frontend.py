import requests
import sys

# LIVE URL
BASE_URL = "https://caparox-bot-971646936342.us-central1.run.app"

def verify_frontend():
    print(f"Checking Frontend at {BASE_URL}...")
    try:
        r = requests.get(BASE_URL, timeout=10)
        print(f"Status Code: {r.status_code}")
        
        # Check if it's HTML
        content_type = r.headers.get('Content-Type', '')
        print(f"Content-Type: {content_type}")
        
        if 'text/html' in content_type:
            print("✅ Content-Type is HTML")
            
            # Check for title or key content
            if '<title>' in r.text or '<div id="root">' in r.text or '<body' in r.text:
                 print("✅ Found HTML structure")
                 print(f"Preview: {r.text[:200]}...")
                 return True
            else:
                 print("⚠️ HTML content seems empty or invalid for SPA")
                 print(f"Content: {r.text[:500]}")
                 return False
        else:
            print(f"❌ Content-Type is NOT HTML: {content_type}")
            print(f"Content: {r.text[:500]}")
            return False
            
    except Exception as e:
        print(f"Request Failed: {e}")
        return False

if __name__ == "__main__":
    if verify_frontend():
        print("Frontend Verification Passed!")
        sys.exit(0)
    else:
        print("Frontend Verification Failed!")
        sys.exit(1)
