import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:8001"

def test_endpoint(name, method, endpoint, data=None, params=None, session=None, is_json=True):
    url = f"{BASE_URL}/{endpoint}"
    print(f"[{name}] {method} {url}...")
    try:
        caller = session if session else requests
        if method == "POST":
            if is_json:
                response = caller.post(url, json=data)
            else:
                response = caller.post(url, data=data)
        else:
            response = caller.get(url, params=params)
            
        print(f"   Status: {response.status_code}")
        try:
            body = response.json()
            if isinstance(body, list):
                print(f"   Body: [List with {len(body)} items]")
            else:
                print(f"   Body: {json.dumps(body, indent=2)}")
        except:
            print(f"   Body Snippet: {response.text[:150]}...")
        return response
    except Exception as e:
        print(f"   Connection Error: {e}")
        return None

if __name__ == "__main__":
    print("=== STARTING COMPREHENSIVE BACKEND API TESTS ===\n")
    
    session = requests.Session()
    unique_id = uuid.uuid4().hex[:6]
    test_user = f"api_tester_{unique_id}@example.com"
    test_pwd = "password123"

    # 1. ACCOUNTS APP
    print(">>> Testing ACCOUNTS App APIs")
    reg_data = {
        "name": "API Tester",
        "email": test_user,
        "password": test_pwd
    }
    reg_res = test_endpoint("Register API", "POST", "accounts/api/register/", data=reg_data)
    
    login_data = {"username": test_user, "password": test_pwd}
    login_res = test_endpoint("Login API", "POST", "accounts/api/login/", data=login_data, session=session)
    
    user_id = None
    if login_res and login_res.status_code == 200:
        user_id = login_res.json().get("user_id")

    print("\n" + "="*50 + "\n")

    # 2. CANDIDATES APP
    print(">>> Testing CANDIDATES App APIs")
    test_endpoint("Candidate Dashboard API", "GET", "candidates/dashboard-api/", session=session)
    
    # 3. COMMON APP
    print("\n>>> Testing COMMON App APIs")
    stats_res = test_endpoint("Admin Stats API", "GET", "common/admin/stats/", session=session)
    users_res = test_endpoint("Admin Users API", "GET", "common/admin/users/", session=session)
    
    if not user_id and users_res and users_res.status_code == 200:
        users = users_res.json().get("users", [])
        for u in users:
            if u['email'] == test_user:
                user_id = u['id']
                break
    
    if user_id:
        test_endpoint("Get Profile API", "GET", "candidates/profile/get/", params={"user_id": user_id}, session=session)
        # Update profile (using is_json=False because it uses request.POST)
        update_data = {"user_id": user_id, "phone": "1234567890"}
        test_endpoint("Update Profile API", "POST", "candidates/profile/update/", data=update_data, session=session, is_json=False)

    # 4. ASSESSMENTS APP
    print("\n>>> Testing ASSESSMENTS App APIs")
    coding_data = {
        "code": "def solve(n):\n    return n * 2",
        "function_name": "solve",
        "language": 71,
        "test_cases": [{"input": 5, "output": 10}]
    }
    test_endpoint("Run Code API", "POST", "assessments/run-code/", data=coding_data, session=session)

    print("\n=== ALL SYSTEM APIS CHECKED ===")
