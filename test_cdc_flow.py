
import json
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"

CUSTOMER_ID = "cb01f5bd-313f-4f8b-a264-a05e4a0209e5"
KEYBOARD_PRODUCT_ID = "2183648b-f019-4b78-910c-ba01b4bf75c0"


def api_request(path, method="GET", body=None):
    data = None
    headers = {}

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"API error: HTTP {exc.code}")
        print(error_body)
        raise


order_payload = {
    "customer_id": CUSTOMER_ID,
    "currency": "INR",
    "shipping_address_snapshot": {
        "name": "Alice Smith",
        "line1": "Test Address",
        "city": "Test City",
        "country": "US",
    },
    "items": [
        {
            "product_id": KEYBOARD_PRODUCT_ID,
            "quantity": 1,
        }
    ],
    "tax_amount": "0",
    "shipping_amount": "0",
    "discount_amount": "0",
}

print("Creating a test order...")
status_code, order = api_request(
    "/orders",
    method="POST",
    body=order_payload,
)

print(f"\nCreation response: HTTP {status_code}")
print(json.dumps(order, indent=2))

order_id = order["id"]
print(f"\nOrder ID: {order_id}")
print(f"Order number: {order['order_number']}")
print(f"Initial status: {order['status']}")

if order["status"] == "pending":
    print("\nConfirming the new order...")
    confirm_status, confirmed_order = api_request(
        f"/orders/{order_id}/confirm",
        method="POST",
    )
    print(f"Confirmation response: HTTP {confirm_status}")
    print(json.dumps(confirmed_order, indent=2))
else:
    print(
        "\nThe order was not pending, so this script did not "
        "attempt confirmation."
    )

print("\nDone. Check Terminal 1 for the CDC events.")
