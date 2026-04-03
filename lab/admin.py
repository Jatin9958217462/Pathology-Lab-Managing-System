from django.contrib import admin
from .models import UserProfile, Patient, Doctor, Test, TestParameter, Booking, Report, ReportResult

@admin.register(UserProfile)
class UPAdmin(admin.ModelAdmin):
    list_display = ['user','role','phone']
    list_filter  = ['role']

@admin.register(Patient)
class PtAdmin(admin.ModelAdmin):
    list_display = ['patient_id','full_name','age','gender','mobile','priority']
    search_fields= ['first_name','last_name','mobile','patient_id']
    readonly_fields=['patient_id']

    def full_name(self,obj): return obj.full_name

@admin.register(Doctor)
class DocAdmin(admin.ModelAdmin):
    list_display=['doc_id','name','qualification','mobile']
    search_fields=['name','mobile']

class ParamInline(admin.TabularInline):
    model=TestParameter;extra=0

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display=['name','category','price','sample','active']
    list_filter =['category','active']
    list_editable=['price','active']
    inlines=[ParamInline]

class ReportInline(admin.TabularInline):
    model=Report;extra=0;readonly_fields=['report_id']

@admin.register(Booking)
class BkAdmin(admin.ModelAdmin):
    list_display=['receipt_id','patient','total','payment_mode','status','booking_date']
    list_filter =['status','payment_mode']
    readonly_fields=['receipt_id']
    filter_horizontal=['tests']
    inlines=[ReportInline]

class ResultInline(admin.TabularInline):
    model=ReportResult;extra=0

@admin.register(Report)
class RptAdmin(admin.ModelAdmin):
    list_display=['report_id','booking','test','is_finalized','report_date']
    list_filter =['is_finalized']
    readonly_fields=['report_id']
    inlines=[ResultInline]

from .models import LabSettings, TestNote

@admin.register(LabSettings)
class LabSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Lab Identity', {'fields': ['lab_name','tagline','unit_text','email','phone','address']}),
        ('Logo & Letterhead', {'fields': ['logo_image','letterhead_image']}),
        ('Signatures', {'fields': ['signature_ansari','signature_saleem','signature_kumar','signature_maurya']}),
        ('PDF Footer', {'fields': ['pdf_footer_text','pdf_footer_image','show_timing_bar','timing_text','facilities_text']}),
    ]
    def has_add_permission(self, request):
        return not LabSettings.objects.exists()

@admin.register(TestNote)
class TestNoteAdmin(admin.ModelAdmin):
    list_display = ['test','updated_at']
    search_fields = ['test__name']
