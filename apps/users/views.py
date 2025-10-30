from django.http import HttpResponse

def users_index(request):
    return HttpResponse("Módulo Usuarios OK")
