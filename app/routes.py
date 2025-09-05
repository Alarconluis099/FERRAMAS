"""Archivo legacy reducido.

Se mantiene sólo para evitar ImportError en código antiguo que haga
`from app import routes` durante transición. Todas las rutas reales
residen ahora en el paquete `app.routes` (directorio) y su blueprint
principal `bp`.
"""

from flask import Blueprint

bp = Blueprint('legacy_removed', __name__)

@bp.route('/__legacy__')
def legacy_notice():
    return {'detail': 'Rutas movidas. Usar blueprints en paquete app.routes.*'}

# Nota: NO definir más rutas aquí para no duplicar lógica.

def attach_rate_limits():
    """Mantener firma usada en app.__init__, delegando a nueva implementación.
    En el nuevo paquete, attach_rate_limits se importa desde app.routes.rate_limits.
    Aquí simplemente no hace nada (backwards compatibility).
    """
    return None


