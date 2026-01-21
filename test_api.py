"""
Test script for SwagSearch v2 API

Tests all 6 endpoints with example requests.
Run this after starting the API server with: uvicorn api:app --reload
"""

import requests
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

# Test Discord user ID
TEST_USER_ID = "123456789"

# ANSI color codes for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title: str):
    """Print a section header"""
    print(f"\n{BLUE}{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}{RESET}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")


def print_info(message: str):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")


def test_health_check():
    """Test GET /api/health"""
    print_section("TEST 1: Health Check")

    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json()["status"] == "ok":
            print_success("Health check passed")
            return True
        else:
            print_error("Health check failed")
            return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_get_filters_empty():
    """Test GET /api/filters with no filters"""
    print_section("TEST 2: Get Filters (Empty)")

    try:
        response = requests.get(f"{BASE_URL}/api/filters", params={"discord_id": TEST_USER_ID})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print_success(f"Get filters passed (found {len(response.json())} filters)")
            return True
        else:
            print_error("Get filters failed")
            return False
    except Exception as e:
        print_error(f"Get filters failed: {e}")
        return False


def test_create_filter():
    """Test POST /api/filters"""
    print_section("TEST 3: Create Filter")

    filter_data = {
        "discord_id": TEST_USER_ID,
        "name": "Budget Rick Owens",
        "brands": ["Rick Owens", "DRKSHDW"],
        "keywords": ["ramones", "geobasket"],
        "min_price": 0,
        "max_price": 50000,
        "markets": ["yahoo", "mercari"],
        "active": True
    }

    try:
        response = requests.post(f"{BASE_URL}/api/filters", json=filter_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 201:
            filter_id = response.json()["id"]
            print_success(f"Filter created with ID: {filter_id}")
            return filter_id
        else:
            print_error("Create filter failed")
            return None
    except Exception as e:
        print_error(f"Create filter failed: {e}")
        return None


def test_get_filters_with_data(expected_count: int = 1):
    """Test GET /api/filters with filters"""
    print_section("TEST 4: Get Filters (With Data)")

    try:
        response = requests.get(f"{BASE_URL}/api/filters", params={"discord_id": TEST_USER_ID})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            filters = response.json()
            if len(filters) >= expected_count:
                print_success(f"Get filters passed (found {len(filters)} filters)")
                return filters
            else:
                print_error(f"Expected at least {expected_count} filters, found {len(filters)}")
                return None
        else:
            print_error("Get filters failed")
            return None
    except Exception as e:
        print_error(f"Get filters failed: {e}")
        return None


def test_update_filter(filter_id: int):
    """Test PUT /api/filters/{filter_id}"""
    print_section("TEST 5: Update Filter")

    update_data = {
        "name": "Updated Rick Owens Filter",
        "max_price": 40000,
        "active": True
    }

    try:
        response = requests.put(
            f"{BASE_URL}/api/filters/{filter_id}",
            params={"discord_id": TEST_USER_ID},
            json=update_data
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            updated_filter = response.json()
            if updated_filter["name"] == update_data["name"] and updated_filter["max_price"] == update_data["max_price"]:
                print_success("Filter updated successfully")
                return True
            else:
                print_error("Filter update values don't match")
                return False
        else:
            print_error("Update filter failed")
            return False
    except Exception as e:
        print_error(f"Update filter failed: {e}")
        return False


def test_update_filter_unauthorized():
    """Test PUT /api/filters/{filter_id} with wrong user"""
    print_section("TEST 6: Update Filter (Unauthorized)")

    # Create a filter
    filter_data = {
        "discord_id": TEST_USER_ID,
        "name": "Test Filter for Authorization",
        "markets": ["yahoo"],
        "active": True
    }

    try:
        create_response = requests.post(f"{BASE_URL}/api/filters", json=filter_data)
        if create_response.status_code != 201:
            print_error("Failed to create test filter")
            return False

        filter_id = create_response.json()["id"]

        # Try to update with different user
        update_data = {"name": "Hacked Filter"}
        response = requests.put(
            f"{BASE_URL}/api/filters/{filter_id}",
            params={"discord_id": "999999999"},  # Different user
            json=update_data
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 403:
            print_success("Authorization check passed (403 Forbidden)")
            return True
        else:
            print_error(f"Expected 403, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Authorization test failed: {e}")
        return False


def test_get_feed():
    """Test GET /api/feed"""
    print_section("TEST 7: Get Feed")

    try:
        response = requests.get(
            f"{BASE_URL}/api/feed",
            params={
                "discord_id": TEST_USER_ID,
                "limit": 10
            }
        )
        print(f"Status Code: {response.status_code}")
        listings = response.json()
        print(f"Response: Found {len(listings)} listings")

        if len(listings) > 0:
            print(f"First listing: {json.dumps(listings[0], indent=2)}")

        if response.status_code == 200:
            print_success(f"Get feed passed (found {len(listings)} listings)")
            return True
        else:
            print_error("Get feed failed")
            return False
    except Exception as e:
        print_error(f"Get feed failed: {e}")
        return False


def test_get_feed_with_filter(filter_id: int):
    """Test GET /api/feed with specific filter"""
    print_section("TEST 8: Get Feed (Specific Filter)")

    try:
        response = requests.get(
            f"{BASE_URL}/api/feed",
            params={
                "discord_id": TEST_USER_ID,
                "filter_id": filter_id,
                "limit": 5
            }
        )
        print(f"Status Code: {response.status_code}")
        listings = response.json()
        print(f"Response: Found {len(listings)} listings")

        if response.status_code == 200:
            print_success(f"Get feed with filter passed (found {len(listings)} listings)")
            return True
        else:
            print_error("Get feed with filter failed")
            return False
    except Exception as e:
        print_error(f"Get feed with filter failed: {e}")
        return False


def test_delete_filter(filter_id: int):
    """Test DELETE /api/filters/{filter_id}"""
    print_section("TEST 9: Delete Filter")

    try:
        response = requests.delete(
            f"{BASE_URL}/api/filters/{filter_id}",
            params={"discord_id": TEST_USER_ID}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json()["success"]:
            print_success(f"Filter {filter_id} deleted successfully")
            return True
        else:
            print_error("Delete filter failed")
            return False
    except Exception as e:
        print_error(f"Delete filter failed: {e}")
        return False


def test_delete_filter_unauthorized():
    """Test DELETE /api/filters/{filter_id} with wrong user"""
    print_section("TEST 10: Delete Filter (Unauthorized)")

    # Create a filter
    filter_data = {
        "discord_id": TEST_USER_ID,
        "name": "Test Filter for Delete Authorization",
        "markets": ["yahoo"],
        "active": True
    }

    try:
        create_response = requests.post(f"{BASE_URL}/api/filters", json=filter_data)
        if create_response.status_code != 201:
            print_error("Failed to create test filter")
            return False

        filter_id = create_response.json()["id"]

        # Try to delete with different user
        response = requests.delete(
            f"{BASE_URL}/api/filters/{filter_id}",
            params={"discord_id": "999999999"}  # Different user
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 403:
            print_success("Authorization check passed (403 Forbidden)")
            # Clean up the filter
            requests.delete(
                f"{BASE_URL}/api/filters/{filter_id}",
                params={"discord_id": TEST_USER_ID}
            )
            return True
        else:
            print_error(f"Expected 403, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Authorization test failed: {e}")
        return False


def test_validation_errors():
    """Test validation error handling"""
    print_section("TEST 11: Validation Errors")

    # Test missing required field
    print_info("Testing missing required field (discord_id)...")
    invalid_data = {
        "name": "Invalid Filter",
        "markets": ["yahoo"]
    }

    try:
        response = requests.post(f"{BASE_URL}/api/filters", json=invalid_data)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 422:  # Validation error
            print_success("Validation error correctly returned (422)")
        else:
            print_error(f"Expected 422, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Validation test failed: {e}")
        return False

    # Test invalid market
    print_info("Testing invalid market...")
    invalid_data = {
        "discord_id": TEST_USER_ID,
        "name": "Invalid Market Filter",
        "markets": ["invalid_market"]
    }

    try:
        response = requests.post(f"{BASE_URL}/api/filters", json=invalid_data)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 422:  # Validation error
            print_success("Invalid market correctly rejected (422)")
            return True
        else:
            print_error(f"Expected 422, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Validation test failed: {e}")
        return False


def run_all_tests():
    """Run all API tests in sequence"""
    print(f"\n{BLUE}{'=' * 80}")
    print(f"SwagSearch v2 API Test Suite")
    print(f"Testing API at: {BASE_URL}")
    print(f"Test User ID: {TEST_USER_ID}")
    print(f"{'=' * 80}{RESET}\n")

    results = []

    # Test 1: Health check
    results.append(("Health Check", test_health_check()))

    # Test 2: Get filters (empty)
    results.append(("Get Filters (Empty)", test_get_filters_empty()))

    # Test 3: Create filter
    filter_id = test_create_filter()
    results.append(("Create Filter", filter_id is not None))

    if filter_id:
        # Test 4: Get filters (with data)
        filters = test_get_filters_with_data()
        results.append(("Get Filters (With Data)", filters is not None))

        # Test 5: Update filter
        results.append(("Update Filter", test_update_filter(filter_id)))

        # Test 6: Update filter (unauthorized)
        results.append(("Update Filter (Unauthorized)", test_update_filter_unauthorized()))

        # Test 7: Get feed
        results.append(("Get Feed", test_get_feed()))

        # Test 8: Get feed with filter
        results.append(("Get Feed (Specific Filter)", test_get_feed_with_filter(filter_id)))

        # Test 9: Delete filter
        results.append(("Delete Filter", test_delete_filter(filter_id)))

        # Test 10: Delete filter (unauthorized)
        results.append(("Delete Filter (Unauthorized)", test_delete_filter_unauthorized()))

    # Test 11: Validation errors
    results.append(("Validation Errors", test_validation_errors()))

    # Print summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{GREEN}✅ PASSED{RESET}" if result else f"{RED}❌ FAILED{RESET}"
        print(f"{test_name}: {status}")

    print(f"\n{BLUE}{'=' * 80}")
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print(f"{GREEN}🎉 All tests passed!{RESET}")
    else:
        print(f"{RED}⚠️  Some tests failed{RESET}")

    print(f"{'=' * 80}{RESET}\n")


if __name__ == "__main__":
    print(f"\n{YELLOW}⚠️  Make sure the API server is running:{RESET}")
    print(f"   {BLUE}uvicorn api:app --reload{RESET}\n")

    input("Press Enter to start tests...")

    run_all_tests()
