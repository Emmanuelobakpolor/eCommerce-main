from django.conf import settings
from django.shortcuts import render, get_object_or_404  # Import get_object_or_404
from django.http import JsonResponse
import json
import datetime

import requests
from .models import *
from .utils import cookieCart, cartData, guestOrder
from django.core.mail import send_mail
from .models import Order, OrderItem



def process_order(request):
    data = json.loads(request.body)
    reference = data.get('form').get('paystack_reference')

    # Verify transaction with Paystack
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'
    }
    response = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    result = response.json()

    if result['status'] and result['data']['status'] == 'success':
       
        return JsonResponse({'message': 'Payment successful'}, status=200)
    else:
        return JsonResponse({'error': 'Payment failed'}, status=400)

    # Email confirmation
    send_mail(
        'Order Confirmation',
        f'Your order with reference {transaction_ref} has been received. Total amount: ₦{user_form_data["total"]}',
        'your-email@example.com',
        [user_form_data['email']],
        fail_silently=False,
    )

    return JsonResponse("Payment processed", safe=False)



def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

def store(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    products = Product.objects.all()
    context = {'products': products, 'cartItems': cartItems}
    return render(request, 'store/store.html', context)


def cart(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/cart.html', context)


def checkout(request):
    data = cartData(request)

    cartItems = data['cartItems']
    order = data['order']
    items = data['items']

    context = {'items': items, 'order': order, 'cartItems': cartItems}
    return render(request, 'store/checkout.html', context)


def updateItem(request):
    data = json.loads(request.body)
    productId = data['productId']
    action = data['action']
    print('Action:', action)
    print('Product:', productId)

    customer = request.user.customer
    product = Product.objects.get(id=productId)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)

    orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        orderItem.quantity = (orderItem.quantity + 1)
    elif action == 'remove':
        orderItem.quantity = (orderItem.quantity - 1)

    orderItem.save()

    if orderItem.quantity <= 0:
        orderItem.delete()

    return JsonResponse('Item was added', safe=False)


def processOrder(request):
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
    else:
        customer, order = guestOrder(request, data)

    total = float(data['form']['total'])
    order.transaction_id = transaction_id

    if total == order.get_cart_total:
        order.complete = True
    order.save()

    if order.shipping == True:
        ShippingAddress.objects.create(
            customer=customer,
            order=order,
            address=data['shipping']['address'],
            city=data['shipping']['city'],
            state=data['shipping']['state'],
            zipcode=data['shipping']['zipcode'],
        )

    return JsonResponse('Payment submitted..', safe=False)