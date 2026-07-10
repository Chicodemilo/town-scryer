#!/usr/bin/env python3
"""
Security Integration Test Script
Tests the backend security middleware functionality
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:5151'
TEST_USER = {'username': 'admin', 'password': 'admin123'}

def test_security_endpoints():
    """Test all security-enhanced endpoints"""
    print("🔒 Testing API Security Integration")
    print("=" * 60)
    
    # Test 1: Basic API status
    print("\n1. Testing basic API status...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Check security headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection',
            'Referrer-Policy'
        ]
        
        print("   Security Headers:")
        for header in security_headers:
            value = response.headers.get(header, 'Not Set')
            print(f"     {header}: {value}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Health check
    print("\n2. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/healthz")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Security status endpoint
    print("\n3. Testing security status...")
    try:
        response = requests.get(f"{BASE_URL}/api/security/status")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Login endpoint
    print("\n4. Testing login endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_USER,
            headers={'Content-Type': 'application/json'}
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            login_data = response.json()
            print(f"   ✅ Login successful!")
            print(f"   User: {login_data['user']['username']}")
            print(f"   Roles: {login_data['user']['roles']}")
            
            # Store token for further tests
            token = login_data['token']
            
            # Test 5: Token verification
            print("\n5. Testing token verification...")
            auth_headers = {'Authorization': f'Bearer {token}'}
            verify_response = requests.get(
                f"{BASE_URL}/api/auth/verify",
                headers=auth_headers
            )
            print(f"   Status: {verify_response.status_code}")
            print(f"   Response: {verify_response.json()}")
            
            # Test 6: Admin security dashboard
            print("\n6. Testing admin security dashboard...")
            admin_response = requests.get(
                f"{BASE_URL}/api/admin/security",
                headers=auth_headers
            )
            print(f"   Status: {admin_response.status_code}")
            if admin_response.status_code == 200:
                admin_data = admin_response.json()
                print(f"   ✅ Admin dashboard accessible!")
                print(f"   Active clients: {admin_data['rate_limiter']['active_clients']}")
                print(f"   System status: {admin_data['system_status']}")
            else:
                print(f"   Response: {admin_response.json()}")
                
        else:
            print(f"   ❌ Login failed: {response.json()}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 7: Rate limiting
    print("\n7. Testing rate limiting...")
    try:
        print("   Making rapid requests to test rate limiting...")
        rate_limit_hit = False
        
        for i in range(15):  # Try to exceed rate limit
            response = requests.get(f"{BASE_URL}/api/security/status")
            if response.status_code == 429:  # Too Many Requests
                print(f"   ✅ Rate limit triggered after {i+1} requests!")
                print(f"   Response: {response.json()}")
                rate_limit_hit = True
                break
            time.sleep(0.1)  # Small delay between requests
        
        if not rate_limit_hit:
            print("   ⚠️  Rate limit not triggered (may need more requests)")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 8: Invalid authentication
    print("\n8. Testing invalid authentication...")
    try:
        invalid_headers = {'Authorization': 'Bearer invalid-token'}
        response = requests.get(
            f"{BASE_URL}/api/auth/verify",
            headers=invalid_headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Invalid token properly rejected!")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Security integration test completed!")
    print("Check the API logs for detailed security monitoring output.")

if __name__ == '__main__':
    test_security_endpoints()
