ResQFood 

ResQFood es una plataforma web para reducir el desperdicio de alimentos, conectando comercios con consumidores para ofrecer productos y packs con descuento antes de que sean descartados.

🚀 Funcionalidades
Registro y autenticación de usuarios.
Marketplace de comercios y packs.
Búsqueda, filtros y ordenamiento.
Carrito de compras y gestión de pedidos.
Sistema de reservas y retiro.
Gestión de stock.
Integración con Mercado Pago y webhooks.
API REST.
Tests automatizados.
🛠️ Tecnologías
Backend: Python, Django, Django REST Framework.
Frontend: HTML, CSS, JavaScript, Django Templates.
Base de datos: SQLite.
Pagos: Mercado Pago.
Deployment: Docker / Render.
Control de versiones: Git / GitHub.
📁 Estructura
'''
ResQFood/
├── accounts/       # Usuarios
├── api/            # API REST
├── core/           # Funcionalidades principales
├── marketplace/    # Comercios, packs, carrito y pedidos
├── packs/          # Gestión de packs
├── payments/       # Pagos
├── usuarios/       # Funcionalidades de usuarios
├── resqfood/       # Configuración Django
├── templates/      # Frontend
├── static/         # Recursos estáticos
├── manage.py
└── requirements.txt
'''
⚙️ Instalación
git clone <URL_DEL_REPOSITORIO>
cd ResQFood

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

La aplicación estará disponible en http://127.0.0.1:8000/.

Las credenciales y variables sensibles se gestionan mediante .env y no se incluyen en el repositorio.
