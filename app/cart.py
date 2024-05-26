class CartStore:
    def __init__(self):
        self._cart = []
        self._listeners = []

    @property
    def cart(self):
        return self._cart

    def _notify_listeners(self):
        for listener in self._listeners:
            listener(self._cart)

    def add_to_cart(self, product):
        self._cart.append(product)
        self._notify_listeners()

    def remove_from_cart(self, product_id):
        self._cart = [p for p in self._cart if p.get("id") != product_id]
        self._notify_listeners()

    def increment_quantity(self, product_id):
        for i, product in enumerate(self._cart):
            if product.get("id") == product_id:
                self._cart[i] = {
                    **product,
                    "quantity": product.get("quantity", 1) + 1,
                }
                break
        self._notify_listeners()

    def decrement_quantity(self, product_id):
        for i, product in enumerate(self._cart):
            if product.get("id") == product_id and product.get("quantity", 1) > 1:
                self._cart[i] = {
                    **product,
                    "quantity": product.get("quantity", 1) - 1,
                }
                break
        self._notify_listeners()

    def subscribe(self, listener):
        self._listeners.append(listener)

        # Llama al listener inmediatamente para obtener el estado inicial
        listener(self._cart)

        return lambda: self._listeners.remove(listener)
