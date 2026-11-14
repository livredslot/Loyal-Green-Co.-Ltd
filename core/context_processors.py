from .models import CompanyProfile


def company(request):
    """Makes the company profile available in every template as {{ company }}."""
    if not request.user.is_authenticated:
        return {}
    return {"company": CompanyProfile.load()}
