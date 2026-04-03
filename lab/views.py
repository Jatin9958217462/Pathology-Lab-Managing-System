from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum
from functools import wraps
from decimal import Decimal
import json, datetime

from .models import UserProfile, Patient, Doctor, Test, TestParameter, Booking, Report, ReportResult


# ─── Decorators ──────────────────────────────────────────────────────────────

def role_required(*roles):
    def dec(fn):
        @wraps(fn)
        def inner(request, *a, **kw):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                if request.user.profile.role not in roles and not request.user.is_superuser:
                    messages.error(request, "Access denied.")
                    return redirect('dashboard')
            except UserProfile.DoesNotExist:
                return redirect('login')
            return fn(request, *a, **kw)
        return inner
    return dec

admin_only   = role_required('admin')
staff_access = role_required('admin', 'staff')
doc_access   = role_required('admin', 'staff', 'doctor')

def get_role(request):
    try:    return request.user.profile.role
    except: return 'patient'


# ─── Auth ─────────────────────────────────────────────────────────────────────

def home(request):
    return redirect('dashboard' if request.user.is_authenticated else 'login')

def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        u = authenticate(request, username=request.POST.get('username',''),
                         password=request.POST.get('password',''))
        if u:
            login(request, u); return redirect(request.GET.get('next','dashboard'))
        messages.error(request, "Invalid username or password.")
    return render(request, 'lab/login.html')

def logout_view(request):
    logout(request); return redirect('login')

def register_view(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method == 'POST':
        uname = request.POST.get('username','').strip()
        pw    = request.POST.get('password','').strip()
        pw2   = request.POST.get('password2','').strip()
        if User.objects.filter(username=uname).exists():
            messages.error(request, "Username already taken.")
        elif pw != pw2:
            messages.error(request, "Passwords do not match.")
        elif len(pw) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        else:
            u = User.objects.create_user(uname, request.POST.get('email',''), pw,
                first_name=request.POST.get('first_name',''),
                last_name=request.POST.get('last_name',''))
            UserProfile.objects.get_or_create(user=u, defaults={'role':'patient'})
            login(request, u)
            return redirect('dashboard')
    return render(request, 'lab/register.html')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    role = get_role(request)
    if role == 'patient': return redirect('my_reports')
    today = datetime.date.today()
    ctx = {
        'role': role,
        'today': today,
        'total_patients': Patient.objects.count(),
        'total_reports':  Report.objects.count(),
        'total_doctors':  Doctor.objects.count(),
        'today_bookings': Booking.objects.filter(booking_date=today).count(),
        'revenue_today':  Booking.objects.filter(booking_date=today).aggregate(r=Sum('total'))['r'] or 0,
        'revenue_all':    Booking.objects.aggregate(r=Sum('total'))['r'] or 0,
        'recent_bookings':Booking.objects.select_related('patient','ref_doctor').order_by('-created_at')[:8],
        'pending_reports':Report.objects.filter(is_finalized=False).select_related('booking__patient','test')[:8],
    }
    return render(request, 'lab/dashboard.html', ctx)


# ─── Patients ─────────────────────────────────────────────────────────────────

@login_required
@doc_access
def patients_list(request):
    q = request.GET.get('q','')
    qs = Patient.objects.select_related('referring_doctor').all()
    if q:
        qs = qs.filter(Q(first_name__icontains=q)|Q(last_name__icontains=q)|
                       Q(mobile__icontains=q)|Q(patient_id__icontains=q))
    return render(request, 'lab/patients.html', {
        'patients': qs, 'q': q, 'role': get_role(request),
        'doctors': Doctor.objects.all(),
    })

@login_required
@staff_access
def patient_add(request):
    if request.method == 'POST':
        fn = request.POST.get('first_name','').strip()
        ln = request.POST.get('last_name','').strip()
        age= request.POST.get('age','0').strip()
        mob= request.POST.get('mobile','').strip()
        if not fn or not age:
            messages.error(request, "First name and age are required.")
            return redirect('patients')
        doc_id = request.POST.get('ref_doctor','')
        doc = Doctor.objects.filter(pk=doc_id).first() if doc_id else None
        pt = Patient(first_name=fn, last_name=ln, age=int(age), mobile=mob,
            honorific=request.POST.get('honorific','Mr.'),
            age_unit=request.POST.get('age_unit','Years'),
            gender=request.POST.get('gender','Male'),
            email=request.POST.get('email',''),
            address=request.POST.get('address',''),
            blood_group=request.POST.get('blood_group',''),
            priority=request.POST.get('priority','Normal'),
            referring_doctor=doc)
        if request.FILES.get('photo'): pt.photo = request.FILES['photo']
        pt.save()
        messages.success(request, f"Patient registered: {pt.full_name} — ID: {pt.patient_id}")
        return redirect('patients')
    return redirect('patients')

@login_required
@staff_access
def patient_edit(request, pk):
    pt = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        pt.honorific  = request.POST.get('honorific', pt.honorific)
        pt.first_name = request.POST.get('first_name', pt.first_name)
        pt.last_name  = request.POST.get('last_name',  pt.last_name)
        pt.age        = request.POST.get('age', pt.age)
        pt.gender     = request.POST.get('gender', pt.gender)
        pt.age_unit   = request.POST.get('age_unit', pt.age_unit)
        pt.mobile     = request.POST.get('mobile', pt.mobile)
        pt.email      = request.POST.get('email', pt.email)
        pt.address    = request.POST.get('address', pt.address)
        pt.blood_group= request.POST.get('blood_group', pt.blood_group)
        pt.priority   = request.POST.get('priority', pt.priority)
        doc_id = request.POST.get('ref_doctor','')
        pt.referring_doctor = Doctor.objects.filter(pk=doc_id).first() if doc_id else None
        if request.FILES.get('photo'): pt.photo = request.FILES['photo']
        pt.save()
        messages.success(request, "Patient updated.")
    return redirect('patients')

@login_required
@admin_only
def patient_delete(request, pk):
    get_object_or_404(Patient, pk=pk).delete()
    messages.success(request, "Patient deleted.")
    return redirect('patients')


# ─── Booking ──────────────────────────────────────────────────────────────────

@login_required
@staff_access
def booking_new(request, pt_pk=None):
    """New booking / patient visit — select patient + tests + billing."""
    patients = Patient.objects.all().order_by('-registered_at')
    doctors  = Doctor.objects.all()
    tests    = Test.objects.filter(active=True).order_by('category','name')

    selected_pt = None
    if pt_pk:
        selected_pt = get_object_or_404(Patient, pk=pt_pk)

    if request.method == 'POST':
        pt_id    = request.POST.get('patient_id','')
        test_ids = request.POST.getlist('test_ids')
        if not pt_id:
            messages.error(request, "Please select a patient.")
            return redirect('booking_new')
        patient  = get_object_or_404(Patient, pk=pt_id)
        sel_tests= Test.objects.filter(pk__in=test_ids, active=True)
        if not sel_tests.exists():
            messages.error(request, "Please select at least one test.")
            return redirect('booking_new')

        doc_id = request.POST.get('ref_doctor','')
        doc = Doctor.objects.filter(pk=doc_id).first() if doc_id else patient.referring_doctor

        booking = Booking.objects.create(
            patient=patient, ref_doctor=doc,
            booking_date=request.POST.get('booking_date') or datetime.date.today(),
            sample_date=request.POST.get('sample_date') or datetime.date.today(),
            status='sample_collected',
            discount_pct=Decimal(request.POST.get('discount_pct','0') or '0'),
            referral_pct=Decimal(request.POST.get('referral_pct','0') or '0'),
            paid=Decimal(request.POST.get('paid','0') or '0'),
            payment_mode=request.POST.get('payment_mode','Cash'),
            created_by=request.user,
        )
        booking.tests.set(sel_tests)
        booking.recalculate()

        # Auto-create one Report per test
        for t in sel_tests:
            rpt = Report.objects.create(booking=booking, test=t, report_date=booking.sample_date)
            # Pre-populate results from TestParameters
            for i, param in enumerate(t.parameters.all()):
                ReportResult.objects.create(
                    report=rpt, parameter=param,
                    param_name=param.param_name, unit=param.unit,
                    lower_limit=param.lower_limit, upper_limit=param.upper_limit,
                    sort_order=i,
                )

        messages.success(request, f"Booking created: {booking.receipt_id} — {patient.full_name}")
        return redirect('booking_detail', pk=booking.pk)

    return render(request, 'lab/booking_new.html', {
        'patients': patients, 'doctors': doctors, 'tests': tests,
        'selected_pt': selected_pt, 'role': get_role(request),
        'today': datetime.date.today().isoformat(),
    })

@login_required
@doc_access
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related('patient','ref_doctor').prefetch_related('tests','reports__results','reports__test'),
        pk=pk)
    return render(request, 'lab/booking_detail.html', {
        'booking': booking, 'reports': booking.reports.all(), 'role': get_role(request),
    })

@login_required
@staff_access
def booking_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        booking.status = request.POST.get('status', booking.status)
        booking.save()
        messages.success(request, "Status updated.")
    return redirect('booking_detail', pk=pk)

@login_required
@doc_access
def bill_pdf(request, pk):
    """Bill with letterhead — PDF only."""
    from .models import LabSettings
    booking = get_object_or_404(Booking.objects.select_related('patient','ref_doctor').prefetch_related('tests'), pk=pk)
    lab = LabSettings.get()
    return render(request, 'lab/bill_pdf.html', {'booking': booking, 'letterhead': True, 'lab': lab})

@login_required
@doc_access
def bill_print(request, pk):
    """Bill Print - uses bill print margins from Lab Settings."""""
    from .models import LabSettings
    booking = get_object_or_404(Booking.objects.select_related('patient','ref_doctor').prefetch_related('tests'), pk=pk)
    lab = LabSettings.get()
    return render(request, 'lab/bill_pdf.html', {'booking': booking, 'letterhead': False, 'lab': lab})


# ─── Report Entry ─────────────────────────────────────────────────────────────

@login_required
@staff_access
def report_entry(request, report_pk):
    """Enter / edit readings for one test report."""
    report  = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    results = report.results.all()

    if request.method == 'POST':
        for res in results:
            val = request.POST.get(f'val_{res.pk}', '').strip()
            res.value = val
            res.flag  = res.compute_flag()
            res.save()
        report.remarks = request.POST.get('remarks','')
        report.custom_report_no = request.POST.get('custom_report_no','').strip()
        # Custom dates
        for field in ['sample_drawn_date','sample_received_date','result_reported_date']:
            val = request.POST.get(field,'').strip()
            setattr(report, field, val if val else None)
        # Save custom_display_id to patient
        cdi = request.POST.get('custom_display_id','').strip()
        if cdi:
            report.booking.patient.custom_display_id = cdi
            report.booking.patient.save(update_fields=['custom_display_id'])
        action = request.POST.get('action','save')
        if action == 'finalize':
            report.is_finalized = True
        report.save()
        messages.success(request, f"Report {report.report_id} saved.")
        return redirect('booking_detail', pk=report.booking.pk)

    return render(request, 'lab/report_entry.html', {
        'report': report, 'results': results, 'role': get_role(request),
        'booking': report.booking,
    })

@login_required
def report_view(request, report_pk):
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    role = get_role(request)
    # Patient can only see their own
    if role == 'patient':
        try:
            if report.booking.patient != request.user.patient_profile:
                messages.error(request, "Access denied."); return redirect('my_reports')
        except Patient.DoesNotExist:
            return redirect('my_reports')
    return render(request, 'lab/report_view.html', {
        'report': report, 'results': report.results.all(), 'role': role,
    })

@login_required
def report_pdf(request, report_pk):
    """Report WITH letterhead (for PDF/download)."""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    role = get_role(request)
    if role == 'patient':
        try:
            if report.booking.patient != request.user.patient_profile:
                return HttpResponse("Access denied", status=403)
        except Patient.DoesNotExist:
            return HttpResponse("Access denied", status=403)
    from .models import LabSettings
    lab = LabSettings.get()
    return render(request, 'lab/report_pdf.html', {'report': report, 'results': report.results.all(), 'letterhead': True, 'lab': lab})

@login_required
@doc_access
def report_print_direct(request, report_pk):
    """Direct Print - uses print margins from Lab Settings, NO letterhead."""""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    from .models import LabSettings
    lab = LabSettings.get()
    return render(request, 'lab/report_print.html', {'report': report, 'results': report.results.all(), 'letterhead': False, 'lab': lab})

@login_required
@doc_access
def report_print_margins(request, report_pk):
    """Print WITH letterhead - uses print margins from Lab Settings."""""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    from .models import LabSettings
    lab = LabSettings.get()
    return render(request, 'lab/report_print.html', {'report': report, 'results': report.results.all(), 'letterhead': True, 'lab': lab})

@login_required
@doc_access
def report_pdf_zero(request, report_pk):
    """PDF — zero top/bottom margins (full bleed for digital/WhatsApp sharing)."""
    report = get_object_or_404(Report.objects.select_related('booking__patient','booking__ref_doctor','booking','test').prefetch_related('results'), pk=report_pk)
    from .models import LabSettings
    lab = LabSettings.get()
    return render(request, 'lab/report_pdf.html', {'report': report, 'results': report.results.all(), 'letterhead': True, 'lab': lab})

@login_required
@staff_access
def report_finalize(request, report_pk):
    report = get_object_or_404(Report, pk=report_pk)
    report.is_finalized = True
    report.save()
    messages.success(request, f"Report {report.report_id} finalized.")
    return redirect('booking_detail', pk=report.booking.pk)

@login_required
@staff_access
def result_inline_edit(request, result_pk):
    """AJAX: Edit a single ReportResult param_name, unit, lower_limit, upper_limit inline."""
    from .models import ReportResult
    from django.http import JsonResponse
    result = get_object_or_404(ReportResult, pk=result_pk)
    if request.method == 'POST':
        result.param_name  = request.POST.get('param_name', result.param_name).strip() or result.param_name
        result.unit        = request.POST.get('unit', result.unit).strip()
        lo = request.POST.get('lower_limit', '').strip()
        hi = request.POST.get('upper_limit', '').strip()
        result.lower_limit = float(lo) if lo else None
        result.upper_limit = float(hi) if hi else None
        result.flag = result.compute_flag()
        result.save()
        return JsonResponse({'ok': True, 'flag': result.flag,
                             'param_name': result.param_name,
                             'unit': result.unit,
                             'lower_limit': result.lower_limit,
                             'upper_limit': result.upper_limit})
    return JsonResponse({'ok': False}, status=400)

@login_required
@admin_only
def report_delete(request, report_pk):
    report = get_object_or_404(Report, pk=report_pk)
    bk_pk = report.booking.pk
    report.delete()
    messages.success(request, "Report deleted.")
    return redirect('booking_detail', pk=bk_pk)

@login_required
@doc_access
def reports_list(request):
    q = request.GET.get('q','')
    qs = Report.objects.select_related('booking__patient','test').order_by('-created_at')
    if q:
        qs = qs.filter(Q(report_id__icontains=q)|Q(booking__patient__first_name__icontains=q)|
                       Q(booking__patient__last_name__icontains=q)|Q(test__name__icontains=q))
    return render(request, 'lab/reports_list.html', {'reports': qs, 'q': q, 'role': get_role(request)})


# ─── Doctors ──────────────────────────────────────────────────────────────────

@login_required
@doc_access
def doctors_list(request):
    return render(request, 'lab/doctors.html', {'doctors': Doctor.objects.all(), 'role': get_role(request)})

@login_required
@staff_access
def doctor_add(request):
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        mob  = request.POST.get('mobile','').strip()
        if not name or not mob:
            messages.error(request, "Name and mobile required."); return redirect('doctors')
        Doctor.objects.create(name=name, qualification=request.POST.get('qualification',''),
            specialization=request.POST.get('specialization',''), mobile=mob,
            email=request.POST.get('email',''), hospital=request.POST.get('hospital',''),
            address=request.POST.get('address',''))
        messages.success(request, f"Dr. {name} added.")
    return redirect('doctors')

@login_required
@admin_only
def doctor_delete(request, pk):
    get_object_or_404(Doctor, pk=pk).delete()
    messages.success(request, "Doctor removed.")
    return redirect('doctors')


# ─── Tests ────────────────────────────────────────────────────────────────────

@login_required
def tests_list(request):
    q = request.GET.get('q','').strip()
    tests = Test.objects.filter(active=True).prefetch_related('parameters')
    if q:
        tests = tests.filter(Q(name__icontains=q) | Q(full_name__icontains=q))
    by_cat = {}
    for t in tests.order_by('category','name'):
        by_cat.setdefault(t.category, []).append(t)
    return render(request, 'lab/tests.html', {'by_cat': by_cat, 'role': get_role(request), 'user_role': get_role(request), 'q': q})

@login_required
@admin_only
def test_add(request):
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        price= request.POST.get('price','0')
        if not name: messages.error(request, "Test name required."); return redirect('tests')
        Test.objects.create(name=name, category=request.POST.get('category','Haematology'),
            price=Decimal(price or '0'), sample=request.POST.get('sample','Blood (Plain)'),
            tat=request.POST.get('tat',''))
        messages.success(request, f"Test '{name}' added.")
    return redirect('tests')

@login_required
@admin_only
def test_delete(request, pk):
    t = get_object_or_404(Test, pk=pk); t.active = False; t.save()
    messages.success(request, "Test removed.")
    return redirect('tests')

@login_required
@admin_only
def test_params(request, pk):
    """Manage reference parameters for a test."""
    test   = get_object_or_404(Test, pk=pk)
    params = test.parameters.all()
    if request.method == 'POST':
        action = request.POST.get('action','')
        if action == 'add':
            TestParameter.objects.create(
                test=test,
                param_name=request.POST.get('param_name','').strip(),
                unit=request.POST.get('unit','').strip(),
                lower_limit=request.POST.get('lower_limit') or None,
                upper_limit=request.POST.get('upper_limit') or None,
                is_text=bool(request.POST.get('is_text','')),
                test_method=request.POST.get('test_method','').strip(),
                sort_order=params.count(),
            )
            messages.success(request, "Parameter added.")
        elif action == 'delete':
            TestParameter.objects.filter(pk=request.POST.get('param_pk'), test=test).delete()
            messages.success(request, "Parameter deleted.")
        elif action == 'edit_param':
            # Inline param editing — does NOT touch existing ReportResult records (denormalized)
            param = TestParameter.objects.filter(pk=request.POST.get('param_pk'), test=test).first()
            if param:
                param.param_name  = request.POST.get('param_name', param.param_name).strip() or param.param_name
                param.unit        = request.POST.get('unit', '').strip()
                lower = request.POST.get('lower_limit','').strip()
                upper = request.POST.get('upper_limit','').strip()
                param.lower_limit = float(lower) if lower else None
                param.upper_limit = float(upper) if upper else None
                param.is_text     = bool(request.POST.get('is_text',''))
                param.save()
                messages.success(request, "Parameter updated.")
        elif action == 'edit_test':
            # Edit test short name and full display name
            new_name = request.POST.get('test_name','').strip()
            full_name = request.POST.get('test_full_name','').strip()
            if new_name:
                test.name = new_name
            test.full_name = full_name
            test.save()
            messages.success(request, "Test name updated.")
        return redirect('test_params', pk=pk)
    return render(request, 'lab/test_params.html', {'test': test, 'params': params, 'role': get_role(request), 'user_role': get_role(request)})

@login_required
def rate_list(request):
    q = request.GET.get('q','').strip()
    tests = Test.objects.filter(active=True).order_by('category','name')
    if q:
        tests = tests.filter(name__icontains=q)
    by_cat = {}
    for t in tests:
        by_cat.setdefault(t.category, []).append(t)
    return render(request, 'lab/rate_list.html', {'by_cat': by_cat, 'q': q})


# ─── Patient Portal ───────────────────────────────────────────────────────────

@login_required
def my_reports(request):
    try:
        pt = request.user.patient_profile
        reports = Report.objects.filter(booking__patient=pt, is_finalized=True).select_related('test','booking')
        return render(request, 'lab/my_reports.html', {'patient': pt, 'reports': reports, 'role': 'patient'})
    except Patient.DoesNotExist:
        return render(request, 'lab/my_reports.html', {'patient': None, 'reports': [], 'role': 'patient'})


# ─── AJAX ─────────────────────────────────────────────────────────────────────

@login_required
def api_patient(request, pk):
    pt = get_object_or_404(Patient, pk=pk)
    return JsonResponse({
        'id': pt.pk, 'patient_id': pt.patient_id, 'name': pt.full_name,
        'salutation': pt.salutation, 'honorific': pt.honorific,
        'age': pt.age, 'age_unit': pt.age_unit, 'gender': pt.gender,
        'mobile': pt.mobile, 'address': pt.address,
        'ref_doctor_id': pt.referring_doctor.pk if pt.referring_doctor else '',
        'ref_doctor_name': pt.referring_doctor.name if pt.referring_doctor else '',
    })

@login_required
def api_booking_tests(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    tests = [{'id': t.pk, 'name': t.name, 'price': str(t.price)} for t in booking.tests.all()]
    return JsonResponse({'tests': tests, 'total': str(booking.total)})


# ─── Lab Settings ────────────────────────────────────────────────────────────

@login_required
@admin_only
def lab_settings(request):
    from .models import LabSettings
    settings = LabSettings.get()
    sig_fields = [
        ('signature_ansari', 'Dr. M. Ahmad Ansari'),
        ('signature_saleem', 'Dr. M. Saleem'),
        ('signature_kumar',  'N. Kumar'),
        ('signature_maurya', 'Dr. V.P. Maurya'),
    ]
    return render(request, 'lab/lab_settings.html', {
        'settings': settings, 'role': get_role(request), 'sig_fields': sig_fields
    })

@login_required
@admin_only
def lab_settings_save(request):
    from .models import LabSettings
    if request.method == 'POST':
        s = LabSettings.get()
        s.lab_name  = request.POST.get('lab_name', s.lab_name)
        s.tagline   = request.POST.get('tagline', s.tagline)
        s.unit_text = request.POST.get('unit_text', s.unit_text)
        s.email     = request.POST.get('email', s.email)
        s.phone     = request.POST.get('phone', s.phone)
        s.address   = request.POST.get('address', s.address)
        s.pdf_footer_text   = request.POST.get('pdf_footer_text', s.pdf_footer_text)
        s.show_timing_bar   = bool(request.POST.get('show_timing_bar'))
        s.timing_text       = request.POST.get('timing_text', s.timing_text)
        s.facilities_text   = request.POST.get('facilities_text', s.facilities_text)
        # Margin settings
        def _int(key, default):
            try: return max(0, min(500, int(request.POST.get(key, default))))
            except: return default
        s.print_single_margin_top    = _int('print_single_margin_top',    s.print_single_margin_top)
        s.print_single_margin_bottom = _int('print_single_margin_bottom', s.print_single_margin_bottom)
        s.print_single_margin_left   = _int('print_single_margin_left',   s.print_single_margin_left)
        s.print_single_margin_right  = _int('print_single_margin_right',  s.print_single_margin_right)
        s.pdf_single_margin_top      = _int('pdf_single_margin_top',      s.pdf_single_margin_top)
        s.pdf_single_margin_bottom   = _int('pdf_single_margin_bottom',   s.pdf_single_margin_bottom)
        s.pdf_single_margin_left     = _int('pdf_single_margin_left',     s.pdf_single_margin_left)
        s.pdf_single_margin_right    = _int('pdf_single_margin_right',    s.pdf_single_margin_right)
        s.print_bulk_margin_top      = _int('print_bulk_margin_top',      s.print_bulk_margin_top)
        s.print_bulk_margin_bottom   = _int('print_bulk_margin_bottom',   s.print_bulk_margin_bottom)
        s.print_bulk_margin_left     = _int('print_bulk_margin_left',     s.print_bulk_margin_left)
        s.print_bulk_margin_right    = _int('print_bulk_margin_right',    s.print_bulk_margin_right)
        s.pdf_bulk_margin_top        = _int('pdf_bulk_margin_top',        s.pdf_bulk_margin_top)
        s.pdf_bulk_margin_bottom     = _int('pdf_bulk_margin_bottom',     s.pdf_bulk_margin_bottom)
        s.pdf_bulk_margin_left       = _int('pdf_bulk_margin_left',       s.pdf_bulk_margin_left)
        s.pdf_bulk_margin_right      = _int('pdf_bulk_margin_right',      s.pdf_bulk_margin_right)
        s.print_bill_margin_top      = _int('print_bill_margin_top',      s.print_bill_margin_top)
        s.print_bill_margin_bottom   = _int('print_bill_margin_bottom',   s.print_bill_margin_bottom)
        s.print_bill_margin_left     = _int('print_bill_margin_left',     s.print_bill_margin_left)
        s.print_bill_margin_right    = _int('print_bill_margin_right',    s.print_bill_margin_right)
        s.pdf_bill_margin_top        = _int('pdf_bill_margin_top',        s.pdf_bill_margin_top)
        s.pdf_bill_margin_bottom     = _int('pdf_bill_margin_bottom',     s.pdf_bill_margin_bottom)
        s.pdf_bill_margin_left       = _int('pdf_bill_margin_left',       s.pdf_bill_margin_left)
        s.pdf_bill_margin_right      = _int('pdf_bill_margin_right',      s.pdf_bill_margin_right)
        # Signer names & qualifications
        for i in range(1, 5):
            s.__dict__[f'signer{i}_name'] = request.POST.get(f'signer{i}_name', getattr(s, f'signer{i}_name'))
            s.__dict__[f'signer{i}_qual'] = request.POST.get(f'signer{i}_qual', getattr(s, f'signer{i}_qual'))
        # Handle image uploads
        for field in ['logo_image','letterhead_image','pdf_footer_image','footer_image',
                      'signature_ansari','signature_saleem','signature_kumar','signature_maurya']:
            if request.FILES.get(field):
                setattr(s, field, request.FILES[field])
            elif request.POST.get(f'clear_{field}'):
                setattr(s, field, None)
        s.save()
        messages.success(request, "Lab settings saved successfully.")
    return redirect('lab_settings')


# ─── Test Note Save ───────────────────────────────────────────────────────────

@login_required
@admin_only
def test_note_save(request, pk):
    from .models import TestNote
    test = get_object_or_404(Test, pk=pk)
    if request.method == 'POST':
        note_text = request.POST.get('note_text', '').strip()
        if note_text:
            TestNote.objects.update_or_create(test=test, defaults={'note_text': note_text})
            messages.success(request, f"Note saved for {test.name}.")
        else:
            TestNote.objects.filter(test=test).delete()
            messages.success(request, "Note removed.")
    return redirect('test_params', pk=pk)


# ─── Bulk Report PDF/Print ────────────────────────────────────────────────────

@login_required
def bulk_report_pdf(request):
    """Generate PDF with letterhead for multiple reports."""
    from .models import LabSettings
    ids = request.GET.getlist('ids')
    if not ids:
        messages.error(request, "No reports selected.")
        return redirect('reports')
    reports_qs = Report.objects.filter(pk__in=ids).select_related(
        'booking__patient','booking__ref_doctor','booking','test'
    ).prefetch_related('results')
    # Role check for patients
    role = get_role(request)
    if role == 'patient':
        try:
            pt = request.user.patient_profile
            reports_qs = reports_qs.filter(booking__patient=pt, is_finalized=True)
        except Exception:
            return HttpResponse("Access denied", status=403)
    lab = LabSettings.get()
    return render(request, 'lab/bulk_report_pdf.html', {
        'reports': reports_qs, 'lab': lab, 'letterhead': True
    })

@login_required
@doc_access
def bulk_report_print(request):
    """Bulk Print - uses bulk print margins from Lab Settings."""""
    from .models import LabSettings
    ids = request.GET.getlist('ids')
    if not ids:
        messages.error(request, "No reports selected.")
        return redirect('reports')
    reports_qs = Report.objects.filter(pk__in=ids).select_related(
        'booking__patient','booking__ref_doctor','booking','test'
    ).prefetch_related('results')
    lab = LabSettings.get()
    return render(request, 'lab/bulk_report_print.html', {
        'reports': reports_qs, 'lab': lab, 'letterhead': False
    })


# ─── Advanced Search ─────────────────────────────────────────────────────────

@login_required
@doc_access
def advanced_search(request):
    q         = request.GET.get('q', '').strip()
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    search_in = request.GET.get('search_in', 'all')

    patients = Patient.objects.none()
    reports  = Report.objects.none()
    bookings = Booking.objects.none()

    if q or date_from or date_to:
        # Patient search
        pt_qs = Patient.objects.all()
        if q:
            pt_qs = pt_qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(mobile__icontains=q)     | Q(patient_id__icontains=q) |
                Q(custom_display_id__icontains=q)
            )
        if date_from:
            pt_qs = pt_qs.filter(registered_at__date__gte=date_from)
        if date_to:
            pt_qs = pt_qs.filter(registered_at__date__lte=date_to)
        patients = pt_qs[:50]

        # Report search
        rpt_qs = Report.objects.select_related('booking__patient','test').all()
        if q:
            rpt_qs = rpt_qs.filter(
                Q(report_id__icontains=q) |
                Q(booking__patient__first_name__icontains=q) |
                Q(booking__patient__last_name__icontains=q)  |
                Q(booking__patient__mobile__icontains=q)     |
                Q(test__name__icontains=q)
            )
        if date_from:
            rpt_qs = rpt_qs.filter(report_date__gte=date_from)
        if date_to:
            rpt_qs = rpt_qs.filter(report_date__lte=date_to)
        reports = rpt_qs[:50]

    # Test search
    tests = []
    if q:
        from .models import Test
        tests = list(Test.objects.filter(active=True, name__icontains=q).order_by('category','name')[:30])

    return render(request, 'lab/advanced_search.html', {
        'patients': patients, 'reports': reports, 'tests': tests,
        'q': q, 'date_from': date_from, 'date_to': date_to,
        'role': get_role(request),
    })


# ─── Chatbot ──────────────────────────────────────────────────────────────────

@login_required
def chatbot(request):
    return render(request, 'lab/chatbot.html')
