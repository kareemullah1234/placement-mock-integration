import requests
import json
import uuid

# We updated the host port to 8001 in docker-compose.yml to avoid conflicts
BASE_URL = "http://127.0.0.1:8001"

def test_endpoint(name, method, endpoint, data=None):
    url = f"{BASE_URL}/{endpoint}"
    print(f"[{name}] {method} {url}...")
    try:
        if method == "POST":
            response = requests.post(url, json=data)
        else:
            response = requests.get(url)
            
        print(f"   Status: {response.status_code}")
        try:
            print(f"   Body: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"   Body: {response.text[:100]}...")
        return response
    except Exception as e:
        print(f"   Connection Error: {e}")
        return None

if __name__ == "__main__":
    print("=== STARTING BACKEND API TESTS ===\n")

    # 1. Test registration with a unique user
    unique_id = uuid.uuid4().hex[:6]
    reg_data = {
        "name": f"Test User {unique_id}",
        "email": f"user_{unique_id}@example.com",
        "password": "testpassword123"
    }
    test_endpoint("Register API", "POST", "accounts/api/register/", reg_data)

    print("\n" + "-"*30 + "\n")

    # 2. Test Login API with the user we JUST created
    login_data = {
        "username": reg_data["email"],
        "password": reg_data["password"]
    }
    test_endpoint("Login API", "POST", "accounts/api/login/", login_data)

    print("\n" + "-"*30 + "\n")

    # 3. Test Candidate Dashboard API
    test_endpoint("Candidate API", "GET", "candidates/dashboard-api/")

    print("\n" + "-"*30 + "\n")

    # 4. Test Common API (Admin Stats)
    test_endpoint("Common API", "GET", "common/admin/stats/")

    print("\n" + "-"*30 + "\n")

    # 5. Test Assessment Coding Engine
    coding_data = {
        "code": "def solve(n):\n    return n * 2",
        "function_name": "solve",
        "language": 71,  # Python
        "test_cases": [
            {"input": 5, "output": 10},
            {"input": 10, "output": 20}
        ]
    }
    # Note: This requires the session to have 'questions' for function_name to work perfectly, 
    # but we're testing the endpoint connectivity here.
    test_endpoint("Assessment API", "POST", "assessments/run-code/", coding_data)

    print("\n=== TESTS COMPLETE ===")
