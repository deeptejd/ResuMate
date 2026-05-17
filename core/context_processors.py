from . import ollama as ol


def ollama_status(request):
    return {
        'ollama_status': ol.check_connection()
    }