# 🔬 Indian Path-Lab — Django LMS v2.0

Full-stack lab management system with **proper workflow** matching your existing software.

## 🚀 Quick Start (5 steps)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
# Open: http://127.0.0.1:8000
```

## 🔑 Demo Credentials
| User | Password | Role |
|------|----------|------|
| `admin` | `Admin@1234` | Full admin |
| `staff` | `Staff@1234` | Lab staff |
| `doctor` | `Doctor@1234` | View reports |
| Patients | Self-register | Own reports only |

## 📋 Workflow (matches your existing software)

1. **New Booking** → Select patient → Select tests (with prices) → Enter payment → Submit
2. **Booking Detail** opens → Shows all tests with "Enter Results" button per test
3. **Enter Results** → Fill in values per parameter → Auto-flags High/Low/Normal → Save or Finalize
4. **Reports**:
   - **PDF (with letterhead)** → Full A4 with official Indian Path-Lab header — for sending to patients
   - **Direct Print** → No letterhead — for printing on your pre-printed letterhead paper
   - **Bill PDF** → With letterhead — invoice for patient
   - **Bill Print** → No letterhead — for pre-printed paper

## 🖨 Print Logic
- **PDF button** = full letterhead (patient copy, WhatsApp share)
- **Print button** = NO letterhead (for printing on your pre-printed stationery from Image 1)

## 🔒 Role Permissions
| Feature | Admin | Staff | Doctor | Patient |
|---------|-------|-------|--------|---------|
| New Booking | ✅ | ✅ | ❌ | ❌ |
| Enter Results | ✅ | ✅ | ❌ | ❌ |
| View All Reports | ✅ | ✅ | ✅ | ❌ |
| View Own Reports | ❌ | ❌ | ❌ | ✅ |
| Add Doctor | ✅ | ✅ | ❌ | ❌ |
| Delete Anything | ✅ | ❌ | ❌ | ❌ |
| Test Master Edit | ✅ | ❌ | ❌ | ❌ |

## 📁 Structure
```
pathlab2/
├── core/           # Django config
├── lab/
│   ├── models.py          # All models
│   ├── views.py           # All views
│   ├── urls.py            # All URLs
│   ├── admin.py           # Django admin
│   ├── signals.py         # Auto UserProfile
│   ├── context_processors.py
│   ├── migrations/        # Pre-built migration
│   ├── management/commands/seed_data.py
│   └── templates/lab/
│       ├── base.html              # Dark sidebar layout
│       ├── login.html
│       ├── register.html
│       ├── dashboard.html
│       ├── booking_new.html       # Select patient + tests
│       ├── booking_detail.html    # Tests + bill + status
│       ├── report_entry.html      # Enter readings
│       ├── report_view.html       # View on screen
│       ├── report_pdf.html        # A4 print (with/without header)
│       ├── bill_pdf.html          # Bill (with/without header)
│       ├── patients.html
│       ├── doctors.html
│       ├── tests.html
│       ├── test_params.html       # Edit reference ranges
│       ├── rate_list.html
│       ├── reports_list.html
│       └── my_reports.html        # Patient portal
├── manage.py
└── requirements.txt
```
