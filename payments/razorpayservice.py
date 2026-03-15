import razorpay
from django.conf import settings

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

def create_payment_order(amount, booking_id):

    order = client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "booking_id": booking_id
        }
    })

    return order


def verify_payment(data):

    params = {
        "razorpay_order_id": data["order_id"],
        "razorpay_payment_id": data["payment_id"],
        "razorpay_signature": data["signature"]
    }

    client.utility.verify_payment_signature(params)