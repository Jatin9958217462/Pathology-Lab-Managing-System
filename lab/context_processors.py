def lab_context(request):
    role = 'anonymous'
    if request.user.is_authenticated:
        try:
            role = request.user.profile.role
        except Exception:
            role = 'patient'
    try:
        from .models import LabSettings
        lab = LabSettings.get()
    except Exception:
        lab = None
    lab_name = lab.lab_name if lab else 'Indian Path-Lab'
    lab_phone = lab.phone if lab else '9213303786, 9971404170'
    return {'user_role': role, 'LAB_NAME': lab_name, 'LAB_PHONE': lab_phone, 'LAB': lab}
