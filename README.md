# WebFerramas

Aplicación Flask para catálogo y carrito de ferretería.

## Configuración rápida

1. Crear entorno virtual
2. Instalar dependencias: `pip install -r requirements.txt`
3. Copiar `.env.example` a `.env` y ajustar credenciales
4. Ejecutar app: `python run.py`

Repositorio:

	✦ https://github.com/LucasOG7/WebFerramas


1. Lenguajes utilizados:
	✦ Python
	✦ HTML
	✦ CSS
	✦ JavaScript

2. Tecnologias:
	✦ MySQL
	✦ Xampp
	✦ PHPadmin

3. Arquitectura:
	✦ Capas, Cliente / Servidor

4. Framework:
	✦ Flask
	✦ Node.js
	✦ Bootstrap


** PASOS DE IMPLEMENTACIÓN **

1. Configuración del entorno de desarrollo:
	✦ Instalar flask
	✦ Instalar flaskmysqldb
	✦ Instalar node_modules (npm install)


2. Configuración de base de datos:
	✦ Instalar Xampp
	✦ Activar apache & mysql
	✦ Una vez dentro de phpadmin importar base de datos proporcionada
	✦ Inserción de datos si es necesario para tests o visualización
	

3. Desarrollo de Front-End:
	✦ Creamos vistas, headers y componentes según requerimientos y necesidades
	✦ Importamos librerias según requerimientos y necesidades
	✦ Configuramos rutas & base de datos para obtención y extracción de datos
	✦ Utilizamos HTML & Bootstrap

4. Desarrollo de Back-End:
	✦ Configuramos servidor utilizando flask con sus dependencias
	✦ Creamos endpoints en las rutas para extraer datos desde la base de datos
	✦ Aplicar lógica de negocio necesaria para su funcionamiento

5. Integracion API
	✦ Ejecutar llamadas a la API mediante rutas conectadas para obtener y enviar datos


6. Pruebas Unitarias
	✦ Realizamos pruebas de integración para saber el estado de cada componente
	✦ Utilizamos python y desde la consola ejecutamos pytest
	✦ A continuación nos despliega un resumen de las pruebas y mediante su resultado
	  podemos realizar su monitorización

7. Sostenimiento de la web
	✦ Realizamos monitoreo en tiempo real de la aplicacion en ejecución
	✦ Aplicamos ajustes/actualizaciones según requerimientos, tests y necesidades
	✦ Desplegar semanalmente informe de errores de la web para su posterior
	  tratamiento

## Nueva organización y mejoras recientes

Se añadieron migraciones automáticas ligeras en `app/__init__.py` para:
* Columna `role` en `users`.
* Columnas `token`, `status`, `created_at` en `transacciones`.
* Columna `total_items_final` (snapshot) en `pedidos` + backfill.

Se preservan los ítems del pedido después del pago para mantener historial.

Helper nuevo: `get_user_discount()` centraliza obtención de descuentos.

La vista Admin ahora muestra estados y totales coherentes aunque se hayan modificado items luego del pago.

## Ejecución rápida

```powershell
# Crear entorno
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Variables (opcional)
set APP_ENV=dev
set MYSQL_USER=root
set MYSQL_PASSWORD=tu_pass
set MYSQL_DB=ferramas
set MYSQL_HOST=localhost

# Ejecutar
python run.py
```

## Empaquetar (ZIP) para distribución

En PowerShell desde la carpeta que contiene `WebFerramas/`:

```powershell
Compress-Archive -Path WebFerramas -DestinationPath WebFerramas.zip -Force
```

Para excluir la caché y entornos virtuales:

```powershell
$items = Get-ChildItem WebFerramas -Recurse | Where-Object { $_.FullName -notmatch '__pycache__' -and $_.FullName -notmatch '\\.venv' }
$items | Compress-Archive -DestinationPath WebFerramas_clean.zip -Force
```

## Próximos pasos sugeridos

1. Dividir `app/routes.py` en módulos (auth, carrito, admin, api) para reducir tamaño (>700 líneas).
2. Añadir pruebas para flujo de compra simulado (mock transbank).
3. Implementar capa de servicio para lógica de pedidos (stock, finalize).
4. Añadir Dockerfile y compose (MySQL + app) para despliegue consistente.
5. Cache ligera (por ejemplo, totales y productos populares) usando un dict en memoria o Redis opcional.

## Variables de entorno clave

| Nombre | Descripción | Default |
|--------|-------------|---------|
| APP_ENV | dev / prod / test | dev |
| RETURN_URL_TBK | URL de retorno Webpay | http://localhost:5000/tbk/commit |
| MYSQL_* | Credenciales BD | ver `config.py` |
| SECRET_KEY | Clave Flask | change-me |

## Tests

Ejecutar:

```powershell
pytest -q
```

Actualmente cubre endpoints básicos de herramientas. Ampliar para carrito y pagos (mock) recomendado.

