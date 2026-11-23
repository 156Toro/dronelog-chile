from django.conf import settings


def version(request):
    return {"VERSION_DRONELOG": settings.VERSION}
