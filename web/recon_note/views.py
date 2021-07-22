from django.shortcuts import render

def list_note(request):
    context = {}
    context['recon_note_active'] = 'true'
    return render(request, 'note/index.html', context)
