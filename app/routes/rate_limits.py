from .auth import admin_required

def attach_rate_limits():
    from flask import current_app
    ext = getattr(current_app, 'extensions', {})
    limiter = ext.get('limiter') if ext else None
    if not limiter:
        return
    # Importar dentro para evitar ciclos
    from .auth import iniciar_sesion
    from .cart import api_guardar_pedido
    from .api import api_tools_paginated
    limiter.limit("5 per minute; 20 per hour")(iniciar_sesion)
    limiter.limit("30 per minute")(api_guardar_pedido)
    limiter.limit("120 per minute")(api_tools_paginated)
