# Aplicación Web Convertidor XML

Esta aplicación web, desarrollada en Python, ofrece funcionalidades para procesar y convertir archivos XML. Esto incluye la capacidad de extraer datos XML desde documentos PDF. La aplicación se basa en Flask y utiliza bibliotecas como Pandas, BeautifulSoup y PyPDF2 para realizar estas tareas.

## Instalación y Configuración

Para instalar y configurar la aplicación en tu entorno local, sigue estos pasos:

1.  **Instalar las Dependencias:**

    Asegúrate de tener Python instalado y luego ejecuta el siguiente comando para instalar las bibliotecas necesarias:

    ```bash
    pip install flask pandas beautifulsoup4 lxml PyPDF2
    ```

2.  **Estructura del Proyecto:**

    Organiza tus archivos y directorios de la siguiente manera:

    ```
    /mi_proyecto/
    ├── app.py
    └── templates/
        ├── index.html
        ├── process.html
        ├── result.html
        └── text_result.html
    ```

    * `app.py`:   Este es el archivo principal de Python que contiene el código de la aplicación web Flask.
    * `templates/`:   Este directorio almacena las plantillas HTML que definen la interfaz de usuario de la aplicación.

## Ejecutar la Aplicación

Una vez que hayas configurado todo, puedes ejecutar la aplicación web:

1.  **Ejecutar el Script:**

    Abre una terminal o línea de comandos, navega hasta el directorio `/mi_proyecto/` y ejecuta el siguiente comando:

    ```bash
    python app.py
    ```

2.  **Acceder a la Aplicación:**

    Después de ejecutar el script, abre tu navegador web y visita la siguiente dirección:

    ```
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
    ```

    La aplicación web Convertidor XML debería estar funcionando en tu navegador.