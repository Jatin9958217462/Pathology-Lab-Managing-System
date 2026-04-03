from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('',            views.home,          name='home'),
    path('login/',      views.login_view,    name='login'),
    path('logout/',     views.logout_view,   name='logout'),
    path('register/',   views.register_view, name='register'),

    # Dashboard
    path('dashboard/',  views.dashboard,     name='dashboard'),

    # Patients
    path('patients/',                views.patients_list,    name='patients'),
    path('patients/add/',            views.patient_add,      name='patient_add'),
    path('patients/<int:pk>/edit/',  views.patient_edit,     name='patient_edit'),
    path('patients/<int:pk>/delete/',views.patient_delete,   name='patient_delete'),

    # Bookings
    path('booking/new/',                    views.booking_new,        name='booking_new'),
    path('booking/new/<int:pt_pk>/',        views.booking_new,        name='booking_new_pt'),
    path('booking/<int:pk>/',               views.booking_detail,     name='booking_detail'),
    path('booking/<int:pk>/update-status/', views.booking_status,     name='booking_status'),
    path('booking/<int:pk>/bill-pdf/',      views.bill_pdf,           name='bill_pdf'),
    path('booking/<int:pk>/bill-print/',    views.bill_print,         name='bill_print'),

    # Reports
    path('report/<int:report_pk>/entry/',    views.report_entry,         name='report_entry'),
    path('report/<int:report_pk>/view/',     views.report_view,          name='report_view'),
    path('report/<int:report_pk>/pdf/',             views.report_pdf,            name='report_pdf'),
    path('report/<int:report_pk>/print/',           views.report_print_direct,   name='report_print'),
    path('report/<int:report_pk>/print-margins/',   views.report_print_margins,  name='report_print_margins'),
    path('report/<int:report_pk>/pdf-zero/',        views.report_pdf_zero,       name='report_pdf_zero'),
    path('report/<int:report_pk>/finalize/', views.report_finalize,      name='report_finalize'),
    path('result/<int:result_pk>/edit/',     views.result_inline_edit,    name='result_inline_edit'),
    path('report/<int:report_pk>/delete/',   views.report_delete,        name='report_delete'),

    # All reports
    path('reports/',          views.reports_list,   name='reports'),

    # Bulk print/PDF (multiple reports at once)
    path('reports/bulk-pdf/',   views.bulk_report_pdf,   name='bulk_report_pdf'),
    path('reports/bulk-print/', views.bulk_report_print, name='bulk_report_print'),

    # Doctors
    path('doctors/',               views.doctors_list,  name='doctors'),
    path('doctors/add/',           views.doctor_add,    name='doctor_add'),
    path('doctors/<int:pk>/delete/', views.doctor_delete, name='doctor_delete'),

    # Test Master + Rate List + Notes
    path('tests/',                  views.tests_list,      name='tests'),
    path('tests/add/',              views.test_add,        name='test_add'),
    path('tests/<int:pk>/delete/',  views.test_delete,     name='test_delete'),
    path('tests/<int:pk>/params/',  views.test_params,     name='test_params'),
    path('tests/<int:pk>/note/',    views.test_note_save,  name='test_note_save'),
    path('rate-list/',              views.rate_list,       name='rate_list'),

    # Lab Settings / Branding
    path('settings/',        views.lab_settings,      name='lab_settings'),
    path('settings/save/',   views.lab_settings_save, name='lab_settings_save'),

    # Search
    path('search/',          views.advanced_search,   name='advanced_search'),

    # Patient portal
    path('my-reports/',      views.my_reports,        name='my_reports'),

    # AJAX
    path('api/patient/<int:pk>/',        views.api_patient,      name='api_patient'),
    path('api/booking-tests/<int:pk>/',  views.api_booking_tests,name='api_booking_tests'),

    # Chatbot
    path('chatbot/', views.chatbot, name='chatbot'),
]
# already imported above — just need to add this before the closing bracket
