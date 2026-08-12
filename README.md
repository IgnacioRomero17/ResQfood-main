ResQFood 

ResQFood es una plataforma web para reducir el desperdicio de alimentos, conectando comercios con consumidores para ofrecer productos y packs con descuento antes de que sean descartados.

🚀 ### Funcionalidades
```
Registro y autenticación de usuarios.
Marketplace de comercios y packs.
Búsqueda, filtros y ordenamiento.
Carrito de compras y gestión de pedidos.
Sistema de reservas y retiro.
Gestión de stock.
Integración con Mercado Pago y webhooks.
API REST.
Tests automatizados.


## 🛠️ Tech Stack & Tecnologías Utilizadas

- **Backend:** Python | Django | Django REST Framework 
- **Frontend:** HTML, CSS, JavaScript, Django Templates.
- **Base de Datos:** SQLite
- **Integraciones & Pagos:** Mercado Pago API
- **Despliegue & Contenedores:** Docker, Render

## 📁 Estructura del Proyecto

```text
ResQFood/
├── accounts/          # Usuarios y autenticación
├── api/               # Módulos y endpoints API REST
├── core/              # Funcionalidades principales y vistas base
├── marketplace/       # Comercios, packs, carrito y pedidos
├── packs/             # Gestión de paquetes/ofertas
├── payments/          # Pasarela de pagos y webhooks (Mercado Pago)
├── usuarios/          # Perfiles de usuario
├── resqfood/          # Configuración principal de Django (settings, urls)
├── templates/         # Plantillas HTML (Frontend)
├── static/            # Recursos estáticos (CSS, JS, Imágenes)
├── manage.py          # Script de gestión de Django
└── requirements.txt   # Dependencias del proyecto
```
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
