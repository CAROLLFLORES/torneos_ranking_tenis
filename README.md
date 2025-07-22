# Configuración del entorno local para el proyecto Django

Este documento explica cómo preparar y ejecutar el proyecto Django localmente desde cero.

---

## Pasos para levantar el proyecto

### 1. Clonar el repositorio

```bash
git clone https://github.com/CAROLLFLORES/torneos_ranking_tenis.git
cd torneos_ranking_tenis/AppDjango
```

---

### 2. Crear y activar un entorno virtual (recomendado)

Crear entorno virtual:

```bash
python -m venv venv
```

Activar entorno virtual (en cd .\AppDjango\):

- En Windows:

```bash
venv\Scripts\activate
```

- En macOS/Linux:

```bash
source venv/bin/activate
```

---

### 3. Instalar dependencias necesarias

> Nota: Las dependencias del proyecto están listadas en el archivo `requirements.txt` que se encuentra en la raíz del proyecto.

Para instalar todas las dependencias de una sola vez, ejecutá:

```bash
pip install -r ../requirements.txt
```

---

### 4. Aplicar migraciones a la base de datos

```bash
python manage.py migrate
```

---

### 5. Levantar el servidor de desarrollo

```bash
python manage.py runserver
```

Abrir en el navegador:

```
http://127.0.0.1:8000/
```

---

## Notas adicionales

- El entorno virtual aísla las dependencias del proyecto del sistema global.
- La base de datos usada es SQLite, incluida por defecto con Python.
- Si se agregan nuevas dependencias, recordá actualizar el archivo `requirements.txt` con:

```bash
pip freeze > ../requirements.txt
```

---

¡Listo! Ahora podés trabajar y desarrollar localmente en el proyecto.
