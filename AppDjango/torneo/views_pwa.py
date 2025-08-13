# torneo/views_pwa.py
from django.http import FileResponse, HttpResponseNotFound
from django.contrib.staticfiles import finders

def _serve(rel_path, content_type):
    path = finders.find(rel_path)  # busca en /static o en STATIC_ROOT
    if path:
        return FileResponse(open(path, "rb"), content_type=content_type)
    return HttpResponseNotFound()

def manifest(request):
    return _serve("pwa/manifest.json", "application/manifest+json")

def service_worker(request):
    # Debe estar EXACTAMENTE en /service-worker.js para alcance global
    return _serve("pwa/service-worker.js", "application/javascript")
