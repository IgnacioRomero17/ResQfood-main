from .models_cart import Cart


def cart_badge(request):
    count = 0
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            cart = Cart.objects.get(user=user)
            count = cart.item_count()
        except Cart.DoesNotExist:
            count = 0
    return {"cart_count": count}

