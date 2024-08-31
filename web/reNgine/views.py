import os
import mimetypes
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.conf import settings

@login_required
def serve_protected_media(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.isdir(file_path):
        raise Http404("File not found")
    if os.path.exists(file_path):
        content_type, _ = mimetypes.guess_type(file_path)
        response = HttpResponse()
        # response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
        response['Content-Type'] = content_type
        response['X-Accel-Redirect'] = f'/protected_media/{path}'
        return response
    else:
        raise Http404("File not found")

