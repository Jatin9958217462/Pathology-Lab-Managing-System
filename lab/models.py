from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime


class UserProfile(models.Model):
    ROLES = [('admin','Administrator'),('staff','Lab Staff'),('doctor','Doctor'),('patient','Patient')]
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role   = models.CharField(max_length=20, choices=ROLES, default='patient')
    phone  = models.CharField(max_length=20, blank=True)

    def __str__(self): return f"{self.user.username} ({self.role})"
    def is_admin(self):  return self.role == 'admin'
    def is_staff_member(self): return self.role in ('admin','staff')
    def is_doctor_access(self): return self.role in ('admin','staff','doctor')


class Doctor(models.Model):
    doc_id        = models.CharField(max_length=20, unique=True, editable=False)
    name          = models.CharField(max_length=150)
    qualification = models.CharField(max_length=100, blank=True)
    specialization= models.CharField(max_length=100, blank=True)
    mobile        = models.CharField(max_length=20)
    email         = models.EmailField(blank=True)
    hospital      = models.CharField(max_length=200, blank=True)
    address       = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.doc_id:
            last = Doctor.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.doc_id = f"DOC-{n:03d}"
        super().save(*args, **kwargs)

    def __str__(self): return self.name


class Test(models.Model):
    CATEGORIES = [
        ('Haematology','Haematology'),('Biochemistry','Biochemistry'),
        ('Serology','Serology'),('Clinical Pathology','Clinical Pathology'),
        ('Histopathology','Histopathology'),('Hormones','Hormones'),
    ]
    SAMPLES = [
        ('Blood (EDTA)','Blood (EDTA)'),('Blood (Plain)','Blood (Plain)'),
        ('Urine','Urine'),('Stool','Stool'),('Swab','Swab'),
        ('Sputum','Sputum'),('Semen','Semen'),('Tissue','Tissue'),
        ('Sodium Citrate','Sodium Citrate'),('Heparin','Heparin'),('Floride','Floride'),
    ]
    name     = models.CharField(max_length=200)
    full_name = models.CharField(max_length=300, blank=True, help_text='Optional full name (e.g. "Complete Blood Count" for CBC). If set, this shows on reports instead of short name.')
    category = models.CharField(max_length=50, choices=CATEGORIES, default='Haematology')
    price    = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    sample   = models.CharField(max_length=30, choices=SAMPLES, default='Blood (Plain)')
    tat      = models.CharField(max_length=50, blank=True)
    active   = models.BooleanField(default=True)

    class Meta: ordering = ['category','name']
    def __str__(self): return f"{self.name} (₹{self.price})"

    @property
    def display_name(self):
        """Returns full_name if set, else name"""
        return self.full_name.strip() if self.full_name and self.full_name.strip() else self.name


class TestParameter(models.Model):
    """Defines reference parameters for each test (e.g. Hemoglobin: 11.5–16 g/dl)"""
    test        = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='parameters')
    param_name  = models.CharField(max_length=200)
    unit        = models.CharField(max_length=50, blank=True)
    lower_limit = models.FloatField(null=True, blank=True)
    upper_limit = models.FloatField(null=True, blank=True)
    is_text     = models.BooleanField(default=False)   # text result (e.g. Positive/Negative)
    sort_order  = models.PositiveIntegerField(default=0)
    test_method = models.CharField(max_length=200, blank=True)

    class Meta: ordering = ['sort_order']
    def __str__(self): return f"{self.test.name} — {self.param_name}"

    @property
    def normal_range(self):
        if self.is_text: return "—"
        if self.lower_limit is not None and self.upper_limit is not None:
            return f"{self.lower_limit} - {self.upper_limit}"
        return "—"


class Patient(models.Model):
    HONORIFICS = [
        ('Mr.','Mr.'),('Mrs.','Mrs.'),('Ms.','Ms.'),('Miss','Miss'),
        ('Dr.','Dr.'),('Prof.','Prof.'),('Master','Master'),('Baby','Baby'),
        ('M/s','M/s'),
    ]
    AGE_UNITS = [('Years','Years'),('Months','Months'),('Days','Days')]
    GENDERS = [('Male','Male'),('Female','Female'),('Child (M)','Child (M)'),('Child (F)','Child (F)'),('Other','Other')]
    PRIORITIES = [('Normal','Normal'),('Urgent','Urgent'),('Emergency','Emergency')]
    BLOODS = [('','Unknown'),('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
              ('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]

    patient_id  = models.CharField(max_length=20, unique=True, editable=False)
    honorific   = models.CharField(max_length=10, choices=[('Mr.','Mr.'),('Mrs.','Mrs.'),('Ms.','Ms.'),('Miss','Miss'),('Dr.','Dr.'),('Prof.','Prof.'),('Master','Master'),('Baby','Baby'),('M/s','M/s')], default='Mr.')
    age_unit    = models.CharField(max_length=10, choices=[('Years','Years'),('Months','Months'),('Days','Days')], default='Years')
    user        = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_profile')
    first_name  = models.CharField(max_length=100)
    last_name   = models.CharField(max_length=100, blank=True)
    age         = models.PositiveIntegerField()
    gender      = models.CharField(max_length=20, choices=GENDERS, default='Male')
    mobile      = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    address     = models.TextField(blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOODS, blank=True)
    referring_doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    priority    = models.CharField(max_length=20, choices=PRIORITIES, default='Normal')
    photo       = models.ImageField(upload_to='photos/', null=True, blank=True)
    custom_display_id = models.CharField(max_length=50, blank=True, help_text='Custom ID on reports')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-registered_at']

    def save(self, *args, **kwargs):
        if not self.patient_id:
            last = Patient.objects.order_by('id').last()
            n = (last.id if last else 0) + 1
            self.patient_id = f"IPL-{n:04d}"
        super().save(*args, **kwargs)

    @property
    def full_name(self): return f"{self.first_name} {self.last_name}".strip()
    @property
    def salutation(self):
        return self.honorific
    def __str__(self): return f"{self.full_name} ({self.patient_id})"


class Booking(models.Model):
    """One booking = one visit. Can have multiple tests."""
    STATUS = [('pending','Pending'),('sample_collected','Sample Collected'),('processing','Processing'),('ready','Ready'),('delivered','Delivered')]
    PAYMENT_MODES = [('Cash','Cash'),('UPI/GPay','UPI/GPay'),('Card','Card'),('Cheque','Cheque'),('Credit','Credit')]

    receipt_id   = models.CharField(max_length=30, unique=True, editable=False)
    patient      = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bookings')
    ref_doctor   = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    tests        = models.ManyToManyField(Test, blank=True)
    booking_date = models.DateField(default=datetime.date.today)
    sample_date  = models.DateField(default=datetime.date.today)
    status       = models.CharField(max_length=20, choices=STATUS, default='sample_collected')

    # Billing
    subtotal     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    referral_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    due          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='Cash')

    created_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bookings_created')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.receipt_id:
            today = datetime.date.today()
            last = Booking.objects.filter(booking_date__year=today.year).order_by('id').last()
            n = (last.id if last else 0) + 1
            self.receipt_id = f"RCP-{today.year}-{n:04d}"
        super().save(*args, **kwargs)

    def recalculate(self):
        self.subtotal = sum(t.price for t in self.tests.all())
        disc = self.subtotal * self.discount_pct / 100
        self.discount_amt = disc
        self.total = self.subtotal - disc
        self.due = self.total - self.paid
        self.save()

    def __str__(self): return f"{self.receipt_id} — {self.patient.full_name}"


class Report(models.Model):
    """One report per test per booking."""
    report_id   = models.CharField(max_length=30, unique=True, editable=False)
    booking     = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reports')
    test        = models.ForeignKey(Test, on_delete=models.CASCADE)
    report_date = models.DateField(default=datetime.date.today)
    remarks     = models.TextField(blank=True)
    sample_drawn_date    = models.DateField(null=True, blank=True)
    sample_received_date = models.DateField(null=True, blank=True)
    result_reported_date = models.DateField(null=True, blank=True)
    custom_report_no     = models.CharField(max_length=50, blank=True)
    is_finalized= models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.report_id:
            today = datetime.date.today()
            last = Report.objects.filter(report_date__year=today.year).order_by('id').last()
            n = (last.id if last else 0) + 1
            self.report_id = f"RPT-{today.year}-{n:04d}"
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.report_id} — {self.test.name}"


class ReportResult(models.Model):
    FLAGS = [('normal','Normal'),('high','High ↑'),('low','Low ↓'),('text','Text'),('critical','Critical')]

    report      = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='results')
    parameter   = models.ForeignKey(TestParameter, on_delete=models.CASCADE, null=True, blank=True)
    param_name  = models.CharField(max_length=200)   # denormalized for display
    value       = models.CharField(max_length=200, blank=True)
    unit        = models.CharField(max_length=50, blank=True)
    lower_limit = models.FloatField(null=True, blank=True)
    upper_limit = models.FloatField(null=True, blank=True)
    flag        = models.CharField(max_length=10, choices=FLAGS, default='normal')
    sort_order  = models.PositiveIntegerField(default=0)

    class Meta: ordering = ['sort_order']

    @property
    def normal_range(self):
        if self.lower_limit is not None and self.upper_limit is not None:
            return f"{self.lower_limit} - {self.upper_limit}"
        return "—"

    def compute_flag(self):
        if not self.value: return 'normal'
        try:
            v = float(self.value)
            if self.lower_limit is not None and v < self.lower_limit: return 'low'
            if self.upper_limit is not None and v > self.upper_limit: return 'high'
            return 'normal'
        except ValueError:
            return 'text'


class LabSettings(models.Model):
    """Singleton model — one record stores all lab branding/customization."""
    lab_name        = models.CharField(max_length=200, default='Indian Path-Lab')
    tagline         = models.CharField(max_length=200, default='AN ISO 9001:2015 CERTIFIED LAB')
    unit_text       = models.CharField(max_length=200, default='A UNIT OF PMEGP GOVT. OF INDIA')
    email           = models.EmailField(default='indianpathlab@gmail.com')
    phone           = models.CharField(max_length=100, default='9213303786, 9971404170')
    address         = models.TextField(default='C-451, Gali No. 5, Old Mustafabad,\n(Lovely Public School Market)\nNear Tirpal Factory, DELHI-110094')
    # Logo & Signature uploads
    logo_image      = models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Upload lab logo (shown in PDF header)')
    letterhead_image= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Full letterhead image (replaces entire header in PDF if set)')
    signature_ansari= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Dr. M. Ahmad Ansari signature image')
    signature_saleem= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Dr. M. Saleem signature image')
    signature_kumar = models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='N. Kumar signature image')
    signature_maurya= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Dr. V.P. Maurya signature image')
    # Signer names & designations (editable)
    signer1_name    = models.CharField(max_length=100, default='Dr. M. SALEEM')
    signer1_qual    = models.CharField(max_length=200, default='(MD)\n(LabIncharge)')
    signer2_name    = models.CharField(max_length=100, default='N.KUMAR')
    signer2_qual    = models.CharField(max_length=200, default='(MLT)\n(Sr.Lab Tech.)')
    signer3_name    = models.CharField(max_length=100, default='Dr. V.P.MAURYA')
    signer3_qual    = models.CharField(max_length=200, default='MBBS(AM),B.Sc. MLT\n(Sr.Lab Tech.)')
    signer4_name    = models.CharField(max_length=100, default='Dr. M. AHMAD ANSARI')
    signer4_qual    = models.CharField(max_length=200, default='Consultant Biochemistry\nPhD.( AIIMS)')
    # Footer image upload
    footer_image    = models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Footer letterhead image (shown at bottom of PDF)')
    # PDF footer/header customization
    pdf_footer_text = models.TextField(blank=True,
                                       default='Note : Above Mentioned Finding Are Professional Opinion and Not a Final Diagnosis All Laboratory Test & Other Investigation Results are to be Corelate Clinical Pathology. Discrepancies if any Necessitate Review Repeat of the Test Contact, Laboratory Immediately This Report is for the perusal for physician/Doctors only.\nNot Valid for Medico Legal Purpose (Court Cases)')
    pdf_footer_image= models.ImageField(upload_to='branding/', null=True, blank=True,
                                        help_text='Optional footer image/stamp')
    # ── Print / PDF Margin Settings (top, right, bottom, left in mm) ──
    # Single report
    print_single_margin_top    = models.PositiveIntegerField(default=100, help_text='Single Print - Top margin (px)')
    print_single_margin_bottom = models.PositiveIntegerField(default=96,  help_text='Single Print - Bottom margin (px)')
    print_single_margin_left   = models.PositiveIntegerField(default=0,   help_text='Single Print - Left margin (px)')
    print_single_margin_right  = models.PositiveIntegerField(default=0,   help_text='Single Print - Right margin (px)')
    pdf_single_margin_top      = models.PositiveIntegerField(default=0,   help_text='Single PDF - Top margin (px)')
    pdf_single_margin_bottom   = models.PositiveIntegerField(default=0,   help_text='Single PDF - Bottom margin (px)')
    pdf_single_margin_left     = models.PositiveIntegerField(default=0,   help_text='Single PDF - Left margin (px)')
    pdf_single_margin_right    = models.PositiveIntegerField(default=0,   help_text='Single PDF - Right margin (px)')
    # Bulk report
    print_bulk_margin_top      = models.PositiveIntegerField(default=100, help_text='Bulk Print - Top margin (px)')
    print_bulk_margin_bottom   = models.PositiveIntegerField(default=96,  help_text='Bulk Print - Bottom margin (px)')
    print_bulk_margin_left     = models.PositiveIntegerField(default=0,   help_text='Bulk Print - Left margin (px)')
    print_bulk_margin_right    = models.PositiveIntegerField(default=0,   help_text='Bulk Print - Right margin (px)')
    pdf_bulk_margin_top        = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Top margin (px)')
    pdf_bulk_margin_bottom     = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Bottom margin (px)')
    pdf_bulk_margin_left       = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Left margin (px)')
    pdf_bulk_margin_right      = models.PositiveIntegerField(default=0,   help_text='Bulk PDF - Right margin (px)')
    # Bill
    print_bill_margin_top      = models.PositiveIntegerField(default=100, help_text='Bill Print - Top margin (px)')
    print_bill_margin_bottom   = models.PositiveIntegerField(default=96,  help_text='Bill Print - Bottom margin (px)')
    print_bill_margin_left     = models.PositiveIntegerField(default=0,   help_text='Bill Print - Left margin (px)')
    print_bill_margin_right    = models.PositiveIntegerField(default=0,   help_text='Bill Print - Right margin (px)')
    pdf_bill_margin_top        = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Top margin (px)')
    pdf_bill_margin_bottom     = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Bottom margin (px)')
    pdf_bill_margin_left       = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Left margin (px)')
    pdf_bill_margin_right      = models.PositiveIntegerField(default=0,   help_text='Bill PDF - Right margin (px)')

    show_timing_bar = models.BooleanField(default=True, help_text='Show timing bar in PDF')
    timing_text     = models.CharField(max_length=200, default='Timing : 9 A.M. to 9 P.M. (Sunday Evening Closed)')
    facilities_text = models.TextField(default='Facilities : X-Ray, E.C.G., Examination of Blood, Urine, Stool, Sputum, Semen & All Spl. Test')
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lab Settings'
        verbose_name_plural = 'Lab Settings'

    def __str__(self): return 'Lab Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TestNote(models.Model):
    """Per-test custom notes that appear at the bottom of the report."""
    test      = models.OneToOneField(Test, on_delete=models.CASCADE, related_name='note')
    note_text = models.TextField(help_text='Note printed at bottom of this test report (e.g. cell morphology note for CBC)')
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self): return f"Note: {self.test.name}"
