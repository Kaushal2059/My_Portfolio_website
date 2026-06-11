from django.conf import settings

def social_links(request):
    return {
        'LINKEDIN_URL': settings.LINKEDIN_URL,
        'FACEBOOK_URL': settings.FACEBOOK_URL,
        'INSTAGRAM_URL': settings.INSTAGRAM_URL,
        'Email': settings.EMAIL,
        'Github': settings.GITHUB_URL
    }