from datetime import datetime, timedelta
import importlib
import json
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

import planner

# Streamlit reruns this script while keeping imported modules in memory. Reload
# planner so a changed build_plan signature cannot remain stale in a live server.
planner = importlib.reload(planner)
MACHINES = planner.MACHINES
build_plan = planner.build_plan
plan_metrics = planner.plan_metrics

st.set_page_config(page_title="SmartFlow AI", page_icon="⚙️", layout="wide")
OPERATIONS = sorted({operation for operations in MACHINES.values() for operation in operations})
OP_EN = {"Torna": "Turning", "Freze": "Milling", "Delik": "Drilling", "Montaj": "Assembly", "Paketleme": "Packaging"}
MACHINE_EN = {
    "Lathe-01": "CNC Lathe 01",
    "Machining-Center-01": "CNC Machining Center 01",
    "Assembly-Kitting-01": "Vehicle Assembly & Kitting Line",
}
MACHINE_TR = {
    "Lathe-01": "CNC Torna 01",
    "Machining-Center-01": "CNC İşleme Merkezi 01",
    "Assembly-Kitting-01": "Araç Montaj ve Set Hazırlama Hattı",
}


def machine_label(machine, language=None):
    language = language or st.session_state.get("language", "English")
    return (MACHINE_EN if language == "English" else MACHINE_TR)[machine]


AUTO_ASSIGN = "__AUTO_ASSIGN__"


def capable_machines(operation):
    return [machine for machine, operations in MACHINES.items() if operation in operations]


def assignment_label(value, language=None):
    language = language or st.session_state.get("language", "English")
    if value == AUTO_ASSIGN:
        return (EN if language == "English" else TR)["auto_machine"]
    return machine_label(value, language)
PROCESS_COL = "S" + chr(252) + "re (saat)"
SETUP_COL = "Haz" + chr(305) + "rl" + chr(305) + "k (saat)"
PRIORITY_COL = chr(214) + "ncelik"
FIELD_EN = {"Component": "Part / component", "Job": "Job ID", "Operasyon": "Operation", "Assigned machine": "Machine assignment", PROCESS_COL: "Processing time (h)", SETUP_COL: "Setup time (h)", PRIORITY_COL: "Priority", "Due at": "Due date & time", "Material ready at": "Material ready date & time"}
JOBS_FILE = Path(__file__).with_name("jobs.json")
timeline_navigation = components.declare_component(
    "timeline_navigation",
    path=str(Path(__file__).with_name("timeline_navigation")),
)
JOB_COLUMNS = ["Job", "Component", "Operasyon", "Assigned machine", PROCESS_COL, SETUP_COL, PRIORITY_COL, "Due at", "Material ready at"]
TIMELINE_START_SUFFIX = " ba" + chr(351) + "lang" + chr(305) + chr(231)
SETUP_START_COL = SETUP_COL.split(" (", 1)[0] + TIMELINE_START_SUFFIX
PROCESS_START_COL = chr(304) + chr(351) + "lem" + TIMELINE_START_SUFFIX
FINISH_COL = "Biti" + chr(351)
SETUP_DURATION_COL = SETUP_COL.split(" (", 1)[0]

EN = {
    "demo_note": "Demo uses simulated data. No real factory, sensor, or ERP connection is present.",
    "new_job": "Add a job", "job_id": "Job ID", "operation": "Operation", "processing": "Processing (h)",
    "setup": "Setup time (h)", "priority": "Priority", "machine": "Machine", "auto_machine": "Automatic assignment", "machine_incompatible": "This machine cannot perform the selected operation.", "due": "Due date", "due_time": "Due time", "material": "Material ready date", "material_time": "Material ready time",
    "add": "Add job to plan", "duplicate": "This Job ID already exists.", "blank_job_id": "Job ID cannot be empty.", "reset": "Reset demo data",
    "manage_jobs": "Edit or delete a job", "save_changes": "Save changes", "delete_job": "Delete selected job", "storage_error": "Saved jobs could not be read; demo jobs were loaded.", "no_jobs": "No jobs in the plan. Add a job from the sidebar or reset the demo data.",
    "total_processing": "Total processing time", "utilization": "Machine utilization", "idle": "Total idle time",
    "last_finish": "Last job finishes", "compare": "Plan comparison", "jobs": "Jobs", "advice": "Recommendations",
    "view": "View", "side_by_side": "Side-by-side comparison", "optimized_view": "Priority plan", "baseline_view": "Baseline plan",
    "baseline": "Baseline", "plan": "plan", "setup_stage": "Setup", "processing_stage": "Processing",
    "production_time": "Production time", "duration": "Duration (h)", "usage_summary": "Machine utilization summary", "timeline_navigation_help": "Drag the chart to pan. Use the left/right arrow keys or A / D for keyboard navigation.",
    "baseline_processing": "Baseline processing (h)", "baseline_setup": "Baseline setup (h)",
    "optimized_processing": "Priority plan processing (h)", "optimized_setup": "Priority plan setup (h)",
    "time_note": "Planning starts {start}. Due and material-ready fields use local date and time. Machine capabilities: ",
    "what_changed": "What changed in this plan?", "no_change": "The heuristic kept the baseline schedule for this set of jobs.",
    "optimized_note": "The priority schedule uses a rule-based heuristic that prioritizes higher priority and earlier due dates. KPI differences use each plan's own finish-time horizon. Delivery lateness and changeover cost are not optimized separately.",
    "footer": "3 simulated machines · capability-based assignment · material constraint · setup and processing shown separately",
    "earlier": "earlier", "assigned": "was assigned to", "instead": "instead of", "capacity": "because it had the earliest estimated completion among capable machines.",
    "hours": "h", "shift_earlier": "starts setup {shift:.1f} h earlier (priority {priority}/5, due in {due:.0f} h).", "shift_later": "starts setup {shift:.1f} h later (priority {priority}/5, due in {due:.0f} h).",
    "shift_earlier_tr": "{shift:.1f} saat daha erken hazırlanıyor (öncelik {priority}/5, teslim hedefi {due:.0f} saat).", "shift_later_tr": "{shift:.1f} saat daha geç hazırlanıyor (öncelik {priority}/5, teslim hedefi {due:.0f} saat).",
    "horizon_help": "Each plan uses its own finish time as the measurement horizon.",
    "util_help": "(Processing + setup) / this plan's finish-time horizon / number of machines.",
    "component": "Part / component name", "blank_component": "Enter a part or component name.", "date_order_error": "Material ready date/time must be at or before the due date/time.",
    "language": "Language / Dil",
}
TR = {
    "demo_note": "Demo simüle edilmiş veriler kullanır. Gerçek fabrika, sensör veya ERP bağlantısı yoktur.",
    "new_job": "Yeni Job", "job_id": "Job ID", "operation": "Operasyon", "processing": "İşlem (saat)",
    "setup": "Hazırlık (saat)", "priority": "Öncelik", "due": "Teslim tarihi", "due_time": "Teslim saati", "material": "Malzeme haz\u0131r tarihi", "material_time": "Malzeme haz\u0131r saati",
    "add": "Job'u plana ekle", "duplicate": "Bu Job ID zaten var.", "blank_job_id": "Job ID boş olamaz.", "reset": "Örnek veriye dön",
    "manage_jobs": "Job düzenle veya sil", "save_changes": "Değişiklikleri kaydet", "delete_job": "Seçili Job'u sil", "storage_error": "Kayıtlı Job'lar okunamadı; örnek veriler yüklendi.", "no_jobs": "Planda Job yok. Sidebar'dan Job ekleyebilir veya örnek verileri yükleyebilirsin.",
    "total_processing": "Toplam işlem süresi", "utilization": "Makine kullanım oranı", "idle": "Toplam boşta kalma",
    "last_finish": "Son Job'un bitişi", "compare": "Plan karşılaştırması", "jobs": "Job listesi", "advice": "Plan önerileri",
    "view": "Görünüm", "side_by_side": "Yan yana karşılaştır", "optimized_view": "Öncelik planı", "baseline_view": "Başlangıç planı",
    "baseline": "Başlangıç", "plan": "planı", "setup_stage": "Hazırlık", "processing_stage": "İşlem",
    "production_time": "Üretim zamanı", "duration": "Süre (sa)", "usage_summary": "Makine kullanım özeti",
    "baseline_processing": "Başlangıç işlem (sa)", "baseline_setup": "Başlangıç hazırlık (sa)",
    "optimized_processing": "Öncelik planı işlem (sa)", "optimized_setup": "Öncelik planı hazırlık (sa)",
    "time_note": "Plan başlangıcı {start}. Teslim ve malzeme hazır alanları yerel tarih ve saati kullanır. Makine yetenekleri: ",
    "what_changed": "Bu planda ne değişti?", "no_change": "Bu Job kümesinde sezgisel yöntem başlangıç planını korudu.",
    "optimized_note": "Öncelik planı, yüksek öncelik ve erken teslim hedefini önceleyen kural tabanlı sezgisel yöntem kullanır. KPI farkları her planın kendi bitiş ufkuna göre hesaplanır. Teslim gecikmesi ve hazırlık geçiş maliyeti ayrıca optimize edilmez.",
    "footer": "3 simüle makine · yetenek bazlı atama · malzeme kısıtı · hazırlık ve işlem ayrı gösterilir",
    "instead": "yerine", "capacity": "uygun makineler arasındaki en erken tahmini bitişi sağladığı için seçildi.",
    "hours": "sa", "shift_earlier_tr": "{shift:.1f} saat daha erken hazırlanıyor (öncelik {priority}/5, teslim hedefi {due:.0f} saat).", "shift_later_tr": "{shift:.1f} saat daha geç hazırlanıyor (öncelik {priority}/5, teslim hedefi {due:.0f} saat).",
    "horizon_help": "Her plan kendi bitiş zamanını ölçüm ufku olarak kullanır.",
    "util_help": "(İşlem + hazırlık) / bu planın bitiş ufku / makine sayısı.",
    "component": "Par\u00e7a / bile\u015fen ad\u0131", "blank_component": "Bir par\u00e7a veya bile\u015fen ad\u0131 girin.", "date_order_error": "Malzemenin haz\u0131r olma tarihi ve saati teslim tarih ve saatini ge\u00e7emez.",
    "language": "Dil / Language",
}

TR["machine"] = "Makine"
TR["setup"] = "Hazirlik suresi (saat)"
TR["auto_machine"] = "Otomatik atama"
TR["machine_incompatible"] = "Makine secilen operasyonu yapamaz."
TR["timeline_navigation_help"] = "Zaman cizelgesini fareyle surukle; sol/sag oklar veya A/D ile kaydir."


def t(key):
    return EN.get(key, key) if st.session_state.get("language", "English") == "English" else TR.get(key, key)


PREVIOUS_DEMO_COMPONENTS = {
    "JOB-1001": "Titanium front upright", "JOB-1002": "Front wing endplate",
    "JOB-1003": "Halo safety-cell mounting bracket", "JOB-1004": "Carbon-fibre monocoque tub",
    "JOB-1005": "Rear wheel hub", "JOB-1006": "Carbon-fibre brake duct kit",
    "JOB-1007": "F1 gearbox casing", "JOB-1008": "Front wing DRS assembly",
    "JOB-1009": "Rear suspension wishbone", "JOB-1010": "Titanium wheel nut",
    "JOB-1011": "Pit-stop wheel-gun kit", "JOB-1012": "Steering rack housing",
}
DEMO_COMPONENTS = {
    "JOB-1001": "Engine crankshaft",
    "JOB-1002": "Cylinder head",
    "JOB-1003": "Chassis mounting bracket",
    "JOB-1004": "Vehicle chassis assembly",
    "JOB-1005": "Brake disc",
    "JOB-1006": "Suspension fastener kit",
    "JOB-1007": "Transmission housing",
    "JOB-1008": "Steering column assembly",
    "JOB-1009": "Subframe mounting bracket",
    "JOB-1010": "Wheel hub",
    "JOB-1011": "Dashboard wiring harness kit",
    "JOB-1012": "Engine block",
}


def fallback_component(operation):
    names = {"Torna": "Turned component", "Freze": "Milled component", "Delik": "Drilled component", "Montaj": "Assembly", "Paketleme": "Packed component kit"}
    return names.get(operation, "Vehicle component")


def example_jobs():
    data = [
        ("JOB-1001", DEMO_COMPONENTS["JOB-1001"], "Torna", 5, 1, 5, 8, 0),
        ("JOB-1002", DEMO_COMPONENTS["JOB-1002"], "Freze", 4, .7, 4, 14, 0),
        ("JOB-1003", DEMO_COMPONENTS["JOB-1003"], "Delik", 3, .5, 3, 10, 1),
        ("JOB-1004", DEMO_COMPONENTS["JOB-1004"], "Montaj", 6, 1.2, 5, 18, 0),
        ("JOB-1005", DEMO_COMPONENTS["JOB-1005"], "Torna", 2.5, .6, 2, 7, 3),
        ("JOB-1006", DEMO_COMPONENTS["JOB-1006"], "Paketleme", 2, .4, 3, 20, 0),
        ("JOB-1007", DEMO_COMPONENTS["JOB-1007"], "Freze", 5.5, 1, 5, 16, 2),
        ("JOB-1008", DEMO_COMPONENTS["JOB-1008"], "Montaj", 3.5, .8, 4, 12, 0),
        ("JOB-1009", DEMO_COMPONENTS["JOB-1009"], "Delik", 4, .5, 4, 22, 4),
        ("JOB-1010", DEMO_COMPONENTS["JOB-1010"], "Torna", 3, .6, 3, 13, 0),
        ("JOB-1011", DEMO_COMPONENTS["JOB-1011"], "Paketleme", 2.5, .4, 2, 11, 0),
        ("JOB-1012", DEMO_COMPONENTS["JOB-1012"], "Freze", 3, .6, 3, 9, 0),
    ]
    anchor = datetime.now().replace(minute=0, second=0, microsecond=0)
    rows = []
    for job_id, component, operation, process, setup, priority, due_in_hours, ready_in_hours in data:
        rows.append({
            "Job": job_id, "Component": component, "Operasyon": operation, "Assigned machine": "",
            PROCESS_COL: process, SETUP_COL: setup, PRIORITY_COL: priority,
            "Due at": (anchor + timedelta(hours=due_in_hours)).isoformat(timespec="minutes"),
            "Material ready at": (anchor + timedelta(hours=ready_in_hours)).isoformat(timespec="minutes"),
        })
    return pd.DataFrame(rows, columns=JOB_COLUMNS)


def demo_jobs_variant(variant):
    """Return one of three quick demo workloads for the main table and plan."""
    jobs = example_jobs()
    factors = {"short": 0.5, "medium": 1.0, "long": 2.0}
    factor = factors[variant]
    jobs[PROCESS_COL] = (jobs[PROCESS_COL].astype(float) * factor).round(2)
    jobs[SETUP_COL] = (jobs[SETUP_COL].astype(float) * factor).round(2)
    return jobs


def parse_job_datetime(value):
    parsed = pd.to_datetime(value, errors="raise")
    return parsed.to_pydatetime() if hasattr(parsed, "to_pydatetime") else parsed


def as_local_iso(day, clock):
    return datetime.combine(day, clock.replace(second=0, microsecond=0)).isoformat(timespec="minutes")


def migrate_legacy_schedule_dates(jobs):
    jobs = jobs.copy()
    legacy_due, legacy_ready = "Teslim (saat)", "Malzeme (saat)"
    needs_migration = "Due at" not in jobs.columns or "Material ready at" not in jobs.columns
    if not needs_migration:
        return jobs, False
    anchor = datetime.now().replace(minute=0, second=0, microsecond=0)
    for target, legacy, default_hours in (("Due at", legacy_due, 24), ("Material ready at", legacy_ready, 0)):
        if target not in jobs.columns:
            if legacy in jobs.columns:
                offsets = pd.to_numeric(jobs[legacy], errors="coerce")
                if offsets.isna().any():
                    raise ValueError("Legacy schedule offsets must be numeric")
            else:
                offsets = pd.Series(default_hours, index=jobs.index)
            jobs[target] = [
                (anchor + timedelta(hours=float(hours))).isoformat(timespec="minutes")
                for hours in offsets
            ]
    jobs = jobs.drop(columns=[legacy_due, legacy_ready], errors="ignore")
    return jobs, True


def canonical_job_id(value):
    if value is None or pd.isna(value):
        return ""
    value = str(value).strip()
    match = re.fullmatch(r"JOB-(\d+)", value, flags=re.IGNORECASE)
    if match:
        return f"JOB-{match.group(1)}"
    if value.upper().startswith("İŞ-"):
        return f"JOB-{value[3:]}"
    return value


def normalize_jobs(jobs):
    jobs = jobs.copy()
    if "Job" not in jobs.columns and "İş" in jobs.columns:
        jobs = jobs.rename(columns={"İş": "Job"})
    if "Job" in jobs.columns:
        jobs["Job"] = jobs["Job"].map(canonical_job_id)
        seen = set()
        number = 1001
        for index, job_id in jobs["Job"].items():
            if not job_id or job_id.casefold() in seen:
                while f"job-{number}" in seen:
                    number += 1
                job_id = f"JOB-{number}"
                jobs.at[index, "Job"] = job_id
                number += 1
            seen.add(job_id.casefold())
    return jobs


def load_jobs():
    if not JOBS_FILE.exists():
        return example_jobs()
    try:
        records = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("Job storage must contain a list")
        if not records:
            return pd.DataFrame(columns=JOB_COLUMNS)
        jobs = normalize_jobs(pd.DataFrame(records))
        migrated = "Component" not in jobs.columns
        if "Assigned machine" not in jobs.columns:
            jobs["Assigned machine"] = ""
            migrated = True
        if migrated and "Component" not in jobs.columns:
            jobs["Component"] = jobs.apply(
                lambda row: DEMO_COMPONENTS.get(str(row["Job"]), fallback_component(row["Operasyon"])),
                axis=1,
            )
        for job_id, previous_name in PREVIOUS_DEMO_COMPONENTS.items():
            mask = jobs["Job"].astype(str).eq(job_id) & jobs["Component"].astype(str).eq(previous_name)
            if mask.any():
                jobs.loc[mask, "Component"] = DEMO_COMPONENTS[job_id]
                migrated = True
        jobs, dates_migrated = migrate_legacy_schedule_dates(jobs)
        migrated = migrated or dates_migrated
        if not set(JOB_COLUMNS).issubset(jobs.columns):
            raise ValueError("Job storage has missing fields")
        jobs = jobs[JOB_COLUMNS]
        build_plan(jobs)
        return save_jobs(jobs) if migrated else jobs
    except (OSError, TypeError, ValueError, OverflowError):
        st.warning(t("storage_error"))
        return example_jobs()


def save_jobs(jobs):
    normalized = normalize_jobs(jobs)
    temp_file = JOBS_FILE.with_suffix(".tmp")
    temp_file.write_text(normalized.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    temp_file.replace(JOBS_FILE)
    return normalized


def next_job_id(jobs):
    existing = {canonical_job_id(value).casefold() for value in jobs["Job"]}
    number = 1001
    while f"job-{number}" in existing:
        number += 1
    return f"JOB-{number}"


if "language" not in st.session_state:
    st.session_state.language = "English"
theme_colors = {
    "background": "#f3f4f8",
    "surface": "#ffffff",
    "surface_alt": "#e9ebf2",
    "text": "#20222a",
    "border": "#d8dbe5",
    "purple": "#5865f2",
}
st.markdown(f"""
<style>
:root{{--sf-bg:{theme_colors['background']};--sf-surface:{theme_colors['surface']};--sf-surface-alt:{theme_colors['surface_alt']};--sf-text:{theme_colors['text']};--sf-border:{theme_colors['border']};--sf-purple:{theme_colors['purple']};color-scheme:light}}
.stApp,header[data-testid="stHeader"],[data-testid="stAppViewContainer"]{{background:var(--sf-bg)!important;color:var(--sf-text)}}
.stApp p,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp [data-testid="stMarkdownContainer"]{{color:var(--sf-text)}}
.stApp [data-testid="stCaptionContainer"]{{color:color-mix(in srgb,var(--sf-text) 72%,transparent)}}
.block-container{{padding-top:1.3rem;padding-bottom:2.5rem;max-width:1500px}}
[data-testid="stSidebar"]{{background:var(--sf-surface)!important;border-right:1px solid var(--sf-border)}}
.hero{{position:relative;overflow:hidden;padding:30px 34px;border:1px solid var(--sf-border);border-radius:18px;background:radial-gradient(ellipse at 88% 20%,color-mix(in srgb,var(--sf-purple) 16%,transparent),transparent 34%),linear-gradient(112deg,var(--sf-surface),var(--sf-surface-alt) 72%);margin-bottom:16px;box-shadow:0 12px 36px color-mix(in srgb,var(--sf-text) 8%,transparent)}}
.hero:after{{content:"";position:absolute;right:-30px;bottom:-82px;width:280px;height:180px;border-radius:50%;background:color-mix(in srgb,#c8102e 45%,transparent);filter:blur(95px);opacity:.2;pointer-events:none}}
.eyebrow{{color:var(--sf-purple);font-size:11px;letter-spacing:2px;font-weight:800;text-transform:uppercase}}
.hero h1{{font-size:34px;margin:8px 0;color:var(--sf-text);letter-spacing:-.8px}}
.hero p,.muted{{color:color-mix(in srgb,var(--sf-text) 72%,transparent)}}
[data-testid="stMetric"]{{background:var(--sf-surface)!important;color:var(--sf-text);border:1px solid var(--sf-border);padding:14px 16px;border-radius:14px;box-shadow:0 6px 18px color-mix(in srgb,var(--sf-text) 6%,transparent)}}
[data-testid="stMetricLabel"]{{color:color-mix(in srgb,var(--sf-text) 72%,transparent)}}
.stTabs [data-baseweb="tab-list"]{{gap:8px;border-bottom:1px solid var(--sf-border)}}
.stTabs [data-baseweb="tab"]{{color:var(--sf-text);padding:10px 15px}}
.stTabs [aria-selected="true"]{{color:var(--sf-text)!important;border-bottom-color:#c8102e!important}}
.stApp button{{appearance:none;-webkit-appearance:none;border:1px solid var(--sf-border)!important;border-radius:10px;background-color:var(--sf-surface)!important;color:var(--sf-text)!important;box-shadow:none!important}}
.stButton button,.stFormSubmitButton button{{font-weight:650;transition:all .15s ease}}
.stFormSubmitButton button{{background:#c8102e!important;color:#fff!important;border-color:#c8102e!important}}
.stApp [data-testid="stForm"] [data-testid="InputInstructions"]{{display:none!important}}
.stApp button:hover{{border-color:var(--sf-purple)!important}}
.stApp button:focus-visible,.stApp input:focus-visible,.stApp textarea:focus-visible,[data-baseweb="select"]>div:focus-within,[data-baseweb="input"]>div:focus-within,[data-baseweb="textarea"]>div:focus-within{{outline:2px solid var(--sf-purple)!important;outline-offset:2px;box-shadow:0 0 0 2px color-mix(in srgb,var(--sf-purple) 28%,transparent)!important}}
.stApp select,.stApp input,.stApp textarea{{color-scheme:light}}
.stApp [data-testid="stSelectbox"] [data-baseweb="select"] *, .stApp [data-testid="stNumberInput"] [data-baseweb="input"] *, .stApp [data-testid="stNumberInput"] button{{border-color:var(--sf-border)!important}}
.stApp [data-testid="stNumberInput"] button{{background-color:var(--sf-surface-alt)!important;color:var(--sf-text)!important;box-shadow:none!important}}
.stApp input[type="number"]{{appearance:textfield;-moz-appearance:textfield}}
.stApp input[type="number"]::-webkit-inner-spin-button,.stApp input[type="number"]::-webkit-outer-spin-button{{-webkit-appearance:none;margin:0}}
.stPlotlyChart [class*="plotly"] text{{fill:var(--sf-text)!important}}
[data-testid="stDataFrame"]{{border:1px solid var(--sf-border);border-radius:12px;overflow:hidden}}
.stPlotlyChart .modebar-container,.stPlotlyChart .modebar,.stPlotlyChart .modebar-group{{background:transparent!important;border:0!important;border-radius:0!important;box-shadow:none!important}}
.stPlotlyChart .modebar-container{{top:4px!important;right:8px!important;z-index:20}}
.stPlotlyChart .modebar-group{{padding:0!important;margin:0 2px!important}}
.stPlotlyChart .modebar-btn{{display:inline-flex!important;align-items:center;justify-content:center;width:30px!important;height:30px!important;margin:0 1px!important;padding:5px!important;border:0!important;border-radius:5px!important;background:transparent!important;box-shadow:none!important}}
.stPlotlyChart .modebar-btn:hover{{background:var(--sf-surface-alt)!important;border-radius:5px!important}}
.stPlotlyChart .modebar-btn svg,.stPlotlyChart .modebar-btn svg path,.stPlotlyChart .modebar-btn svg rect,.stPlotlyChart .modebar-btn svg line{{fill:var(--sf-text)!important;stroke:var(--sf-text)!important}}
.stPlotlyChart .modebar-btn:focus-visible{{outline:2px solid var(--sf-purple)!important;outline-offset:1px;border-radius:5px!important}}
.stPlotlyChart .modebar--hover>:not(.watermark){{opacity:1!important}}
.stApp input:not([type="checkbox"]):not([type="radio"]),.stApp textarea{{appearance:none;-webkit-appearance:none;background:transparent!important;color:var(--sf-text)!important;border:0!important;box-shadow:none!important}}
.stApp select,.stApp [data-baseweb="select"]>div,.stApp [data-baseweb="input"]>div,.stApp [data-baseweb="textarea"]>div{{appearance:none;-webkit-appearance:none;background:var(--sf-surface-alt)!important;color:var(--sf-text)!important;border:1px solid var(--sf-border)!important;box-shadow:none!important}}
hr{{border-color:var(--sf-border)}}
</style>
""", unsafe_allow_html=True)
hero = ('SMARTFLOW AI · SMART MANUFACTURING PLANNING', 'Smoother production. Less waiting.', 'Assign jobs by machine capability and production constraints, then compare schedules.') if st.session_state.language == "English" else ('SMARTFLOW AI · AKILLI ÜRETİM PLANLAMA', 'Daha akıcı üretim. Daha az bekleme.', "Job'ları makine yetenekleri ve üretim kısıtlarına göre sırala, planları karşılaştır.")
st.markdown(f'<div class="hero"><div class="eyebrow">{hero[0]}</div><h1>{hero[1]}</h1><p>{hero[2]}</p></div>', unsafe_allow_html=True)
st.caption(t("demo_note"))

if "jobs" not in st.session_state:
    st.session_state.jobs = load_jobs()
else:
    previous_jobs = st.session_state.jobs
    st.session_state.jobs = normalize_jobs(previous_jobs)
    if "Assigned machine" not in st.session_state.jobs.columns:
        st.session_state.jobs["Assigned machine"] = ""
    if "Component" not in st.session_state.jobs.columns:
        st.session_state.jobs["Component"] = st.session_state.jobs.apply(
            lambda row: DEMO_COMPONENTS.get(str(row["Job"]), fallback_component(row["Operasyon"])),
            axis=1,
        )
    for job_id, previous_name in PREVIOUS_DEMO_COMPONENTS.items():
        mask = st.session_state.jobs["Job"].astype(str).eq(job_id) & st.session_state.jobs["Component"].astype(str).eq(previous_name)
        st.session_state.jobs.loc[mask, "Component"] = DEMO_COMPONENTS[job_id]
    st.session_state.jobs, _ = migrate_legacy_schedule_dates(st.session_state.jobs)
    if not previous_jobs.equals(st.session_state.jobs):
        st.session_state.jobs = save_jobs(st.session_state.jobs)

with st.sidebar:
    language = st.selectbox(t("language"), ["English", "Türkçe"], index=0 if st.session_state.language == "English" else 1, key="language")
    st.markdown(f"### ➕ {t('new_job')}")
    op = st.selectbox(t("operation"), OPERATIONS, format_func=lambda value: OP_EN[value] if language == "English" else value, key="new_operation")
    with st.form("new_job", clear_on_submit=True):
        name = st.text_input(t("job_id"), next_job_id(st.session_state.jobs))
        component = st.text_input(t("component"), placeholder="e.g. Engine crankshaft")
        machine_key = "new_assigned_machine"
        machine_options = [AUTO_ASSIGN, *capable_machines(op)]
        if st.session_state.get(machine_key) not in machine_options:
            st.session_state[machine_key] = AUTO_ASSIGN
        assigned_machine = st.selectbox(t("machine"), machine_options, format_func=lambda value: assignment_label(value, language), key=machine_key)
        c1, c2 = st.columns(2)
        duration = c1.number_input(t("processing"), .5, 48., 2., .5)
        setup = c2.number_input(t("setup"), 0., 12., .5, .1, key="new_setup_time")
        c3, c4 = st.columns(2)
        priority = c3.slider(t("priority"), 1, 5, 3)
        form_now = datetime.now().replace(second=0, microsecond=0)
        due_default = form_now + timedelta(hours=24)
        due_date_col, due_time_col = st.columns(2)
        due_date = due_date_col.date_input(t("due"), value=due_default.date(), key="new_due_date")
        due_time = due_time_col.time_input(t("due_time"), value=due_default.time(), key="new_due_time")
        material_date_col, material_time_col = st.columns(2)
        material_date = material_date_col.date_input(t("material"), value=form_now.date(), key="new_material_date")
        material_time = material_time_col.time_input(t("material_time"), value=form_now.time(), key="new_material_time")
        if st.form_submit_button(t("add"), width="stretch", type="primary"):
            job_id = canonical_job_id(name)
            existing_ids = st.session_state.jobs["Job"].astype(str).str.casefold()
            if not job_id:
                st.error(t("blank_job_id"))
            elif not component.strip():
                st.error(t("blank_component"))
            elif datetime.combine(material_date, material_time) > datetime.combine(due_date, due_time):
                st.error(t("date_order_error"))
            elif job_id.casefold() in set(existing_ids):
                st.error(t("duplicate"))
            else:
                new_row = {"Job": job_id, "Component": component.strip(), "Operasyon": op, "Assigned machine": "" if assigned_machine == AUTO_ASSIGN else assigned_machine, PROCESS_COL: duration, SETUP_COL: setup, PRIORITY_COL: priority, "Due at": as_local_iso(due_date, due_time), "Material ready at": as_local_iso(material_date, material_time)}
                st.session_state.jobs = pd.concat([st.session_state.jobs, pd.DataFrame([new_row])], ignore_index=True)
                st.session_state.jobs = save_jobs(st.session_state.jobs)
                st.rerun()

    with st.expander(t("manage_jobs")):
        current_jobs = st.session_state.jobs
        if "_selected_job_override" in st.session_state:
            st.session_state.selected_job = st.session_state.pop("_selected_job_override")
        if current_jobs.empty:
            st.info(t("no_jobs"))
        else:
            if st.session_state.get("selected_job") not in set(current_jobs["Job"]):
                st.session_state.selected_job = current_jobs.iloc[0]["Job"]
            selected_job = st.selectbox(
                t("job_id"), current_jobs["Job"].tolist(), key="selected_job",
                format_func=lambda job_id: f"{current_jobs.loc[current_jobs['Job'] == job_id, 'Component'].iloc[0]} | {job_id}",
            )
            selected_row = current_jobs.loc[current_jobs["Job"] == selected_job].iloc[0]
            due_default = parse_job_datetime(selected_row["Due at"])
            material_default = parse_job_datetime(selected_row["Material ready at"])
            saved_machine = selected_row["Assigned machine"]
            saved_machine = "" if pd.isna(saved_machine) else str(saved_machine).strip()
            edit_machine_key = f"edit_machine_{selected_job}"
            edit_assignment_signature = (str(selected_job), str(selected_row["Operasyon"]), saved_machine)
            if st.session_state.get("_edit_assignment_signature") != edit_assignment_signature:
                st.session_state[edit_machine_key] = saved_machine if saved_machine in capable_machines(selected_row["Operasyon"]) else AUTO_ASSIGN
                st.session_state["_edit_assignment_signature"] = edit_assignment_signature
            edit_datetime_signature = (str(selected_job), str(selected_row["Due at"]), str(selected_row["Material ready at"]))
            if st.session_state.get("_edit_datetime_signature") != edit_datetime_signature:
                st.session_state[f"edit_due_date_{selected_job}"] = due_default.date()
                st.session_state[f"edit_due_time_{selected_job}"] = due_default.time()
                st.session_state[f"edit_material_date_{selected_job}"] = material_default.date()
                st.session_state[f"edit_material_time_{selected_job}"] = material_default.time()
                st.session_state["_edit_datetime_signature"] = edit_datetime_signature
            edited_op = st.selectbox(t("operation"), OPERATIONS, index=OPERATIONS.index(selected_row["Operasyon"]), format_func=lambda value: OP_EN[value] if language == "English" else value, key=f"edit_op_{selected_job}")
            with st.form(f"edit_job_{selected_job}"):
                edited_id = st.text_input(t("job_id"), selected_job, key=f"edit_id_{selected_job}")
                edited_component = st.text_input(t("component"), str(selected_row["Component"]), key=f"edit_component_{selected_job}")
                edit_machine_options = [AUTO_ASSIGN, *capable_machines(edited_op)]
                if st.session_state.get(edit_machine_key) not in edit_machine_options:
                    st.session_state[edit_machine_key] = AUTO_ASSIGN
                edited_machine = st.selectbox(t("machine"), edit_machine_options, format_func=lambda value: assignment_label(value, language), key=edit_machine_key)
                edit_c1, edit_c2 = st.columns(2)
                edited_duration = edit_c1.number_input(t("processing"), .5, 48., float(selected_row["Süre (saat)"]), .5, key=f"edit_duration_{selected_job}")
                edited_setup = edit_c2.number_input(t("setup"), 0., 12., float(selected_row["Hazırlık (saat)"]), .1, key=f"edit_setup_{selected_job}")
                edit_c3, edit_c4 = st.columns(2)
                edited_priority = edit_c3.slider(t("priority"), 1, 5, int(selected_row["Öncelik"]), key=f"edit_priority_{selected_job}")
                edited_due_date_col, edited_due_time_col = st.columns(2)
                edited_due_date = edited_due_date_col.date_input(t("due"), value=due_default.date(), key=f"edit_due_date_{selected_job}")
                edited_due_time = edited_due_time_col.time_input(t("due_time"), value=due_default.time(), key=f"edit_due_time_{selected_job}")
                edited_material_date_col, edited_material_time_col = st.columns(2)
                edited_material_date = edited_material_date_col.date_input(t("material"), value=material_default.date(), key=f"edit_material_date_{selected_job}")
                edited_material_time = edited_material_time_col.time_input(t("material_time"), value=material_default.time(), key=f"edit_material_time_{selected_job}")
                save_edit = st.form_submit_button(t("save_changes"), width="stretch")
            if save_edit:
                edited_id = canonical_job_id(edited_id)
                other_ids = current_jobs.loc[current_jobs["Job"] != selected_job, "Job"].astype(str).str.casefold()
                if not edited_id:
                    st.error(t("blank_job_id"))
                elif not edited_component.strip():
                    st.error(t("blank_component"))
                elif edited_id.casefold() in set(other_ids):
                    st.error(t("duplicate"))
                elif edited_machine != AUTO_ASSIGN and edited_machine not in capable_machines(edited_op):
                    st.error(t("machine_incompatible"))
                elif datetime.combine(edited_material_date, edited_material_time) > datetime.combine(edited_due_date, edited_due_time):
                    st.error(t("date_order_error"))
                else:
                    updated_jobs = current_jobs.copy()
                    row_index = updated_jobs.index[updated_jobs["Job"] == selected_job][0]
                    updated_jobs.loc[row_index, JOB_COLUMNS] = [edited_id, edited_component.strip(), edited_op, "" if edited_machine == AUTO_ASSIGN else edited_machine, edited_duration, edited_setup, edited_priority, as_local_iso(edited_due_date, edited_due_time), as_local_iso(edited_material_date, edited_material_time)]
                    st.session_state.jobs = save_jobs(updated_jobs)
                    st.session_state._selected_job_override = edited_id
                    st.rerun()
            if st.button(t("delete_job"), key=f"delete_{selected_job}", width="stretch"):
                updated_jobs = current_jobs.loc[current_jobs["Job"] != selected_job].reset_index(drop=True)
                st.session_state.jobs = save_jobs(updated_jobs)
                st.session_state._selected_job_override = updated_jobs.iloc[0]["Job"] if not updated_jobs.empty else None
                st.rerun()

    if st.button(t("reset"), width="stretch"):
        st.session_state.jobs = save_jobs(example_jobs())
        st.session_state._selected_job_override = "JOB-1001"
        st.rerun()
    st.caption("Demo veri seti / Demo datasets")
    demo_short, demo_medium, demo_long = st.columns(3)
    demo_buttons = [
        (demo_short, "short", "1 · Kısa", "1 · Short"),
        (demo_medium, "medium", "2 · Orta", "2 · Medium"),
        (demo_long, "long", "3 · Uzun", "3 · Long"),
    ]
    for column, variant, turkish_label, english_label in demo_buttons:
        if column.button(turkish_label if language == "Türkçe" else english_label, key=f"demo_jobs_{variant}", width="stretch"):
            st.session_state.jobs = save_jobs(demo_jobs_variant(variant))
            st.session_state._selected_job_override = "JOB-1001"
            st.session_state._timeline_pan_steps = 0
            st.rerun()

jobs = st.session_state.jobs.copy()
planning_start = datetime.now().replace(minute=0, second=0, microsecond=0)
original_baseline = build_plan(jobs, optimized=False, base_time=planning_start)
original_optimized = build_plan(jobs, optimized=True, base_time=planning_start)
ai_baseline = ai_optimized = outcomes = None
ai_error = None
try:
    from ai_planning import jobs_with_ai_durations, compare_schedule_outcomes

    ai_jobs = jobs_with_ai_durations(jobs)
    ai_baseline = build_plan(ai_jobs, optimized=False, base_time=planning_start)
    ai_optimized = build_plan(ai_jobs, optimized=True, base_time=planning_start)
    outcomes = compare_schedule_outcomes(original_optimized, ai_optimized, planning_start)
except (ImportError, ValueError, OverflowError) as error:
    ai_error = str(error)

if ai_error or jobs.empty:
    st.session_state.use_ai_durations = False
use_ai = st.toggle(
    "AI süreleriyle planla" if language == "Türkçe" else "Plan with AI durations",
    key="use_ai_durations", disabled=bool(ai_error) or jobs.empty,
    help=("Simülasyon verileriyle eğitilmiş modelin işlem sürelerini kullanır. Hazırlık süreleri ve kayıtlı veriler korunur."
          if language == "Türkçe" else
          "Uses processing times from a simulation-trained model. Setup times and stored job data are preserved."),
    on_change=lambda: st.session_state.update(_timeline_pan_steps=0),
)
if ai_error:
    st.warning(("AI planı kullanılamıyor; girilen sürelerle devam ediliyor: " if language == "Türkçe" else
                "AI planning is unavailable; using original estimates: ") + ai_error)

duration_source = ("AI süreleri" if use_ai else "Girilen süreler") if language == "Türkçe" else ("AI estimates" if use_ai else "Original estimates")
st.caption(
    f"Aktif süre kaynağı: {duration_source}. Her iki Gantt grafiği ve özet göstergeler bu kaynağı kullanır. AI modeli simülasyon verileriyle eğitilmiştir."
    if language == "Türkçe" else
    f"Active duration source: {duration_source}. Both Gantt charts and the summary metrics use this source. The AI model is trained on synthetic data."
)
baseline = ai_baseline if use_ai else original_baseline
optimized = ai_optimized if use_ai else original_optimized
schedule_revision = f"{use_ai}-{pd.util.hash_pandas_object(jobs, index=False).sum()}"
base_horizon = float(baseline["Bitiş (saat)"].max()) if len(baseline) else 0.0
optimized_horizon = float(optimized["Bitiş (saat)"].max()) if len(optimized) else 0.0
base_kpi = plan_metrics(baseline, base_horizon, len(MACHINES))
opt_kpi = plan_metrics(optimized, optimized_horizon, len(MACHINES))


def delta(new, old, suffix=""):
    value = new - old
    arrow = "↓" if value < 0 else "↑" if value > 0 else "="
    return f"{arrow} {abs(value):.1f}{suffix} {('vs. baseline' if st.session_state.language == 'English' else 'başlangıç planına göre')}"


k1, k2, k3, k4 = st.columns(4)
k1.metric(t("total_processing"), f"{opt_kpi['processing_hours']:.1f} {t('hours')}")
k2.metric(t("utilization"), f"{opt_kpi['utilization_pct']:.1f}%", delta(opt_kpi['utilization_pct'], base_kpi['utilization_pct'], "%"), help=t("util_help"))
k3.metric(t("idle"), f"{opt_kpi['idle_hours']:.1f} {t('hours')}", delta(opt_kpi['idle_hours'], base_kpi['idle_hours'], f" {t('hours')}"), help=t("horizon_help"))
finish = planning_start + timedelta(hours=opt_kpi["makespan_hours"])
k4.metric(t("last_finish"), finish.strftime("%d %b %H:%M") if len(optimized) else "—", delta(opt_kpi['makespan_hours'], base_kpi['makespan_hours'], f" {t('hours')}"))

if "_timeline_pan_steps" not in st.session_state:
    st.session_state._timeline_pan_steps = 0
navigation_event = timeline_navigation(key="timeline-keyboard-navigation", default=None, height=0)
if isinstance(navigation_event, dict):
    event_sequence = int(navigation_event.get("sequence", 0))
    if event_sequence > st.session_state.get("_timeline_last_sequence", 0):
        direction = -1 if navigation_event.get("key") in ("ArrowLeft", "a", "A") else 1
        st.session_state._timeline_pan_steps += direction
        st.session_state._timeline_last_sequence = event_sequence

tab_plan, tab_jobs, tab_advice, tab_ai = st.tabs([f"📊 {t('compare')}", f"🧾 {t('jobs')}", f"💡 {t('advice')}", "🤖 AI Tahmini" if language == "Türkçe" else "🤖 AI Estimates"])
with tab_ai:
    try:
        from ai_panel import render_ai_panel
    except ImportError:
        st.error("AI bağımlılıkları eksik / Missing AI dependencies: python -m pip install -r requirements.txt")
    else:
        render_ai_panel(jobs, language, use_ai=use_ai, outcomes=outcomes)
with tab_plan:
    st.caption(
        f"{len(jobs)} iş · Toplam işlem: {base_kpi['processing_hours']:.1f} saat · Demo değiştirmek için sol paneldeki 1 / 2 / 3 butonlarını kullan."
        if language == "Türkçe" else
        f"{len(jobs)} jobs · Total processing: {base_kpi['processing_hours']:.1f} h · Use the sidebar's 1 / 2 / 3 buttons to switch demos."
    )
    if outcomes is not None:
        from plan_impact import render_impact_summary, render_delivery_table
        render_impact_summary(outcomes, use_ai, language)
    views = [t("side_by_side"), t("optimized_view"), t("baseline_view")]
    view = st.radio(t("view"), views, horizontal=True, label_visibility="collapsed")
    plans = [(t("baseline_view"), baseline), (t("optimized_view"), optimized)] if view == t("side_by_side") else [(t("optimized_view"), optimized)] if view == t("optimized_view") else [(t("baseline_view"), baseline)]
    st.caption(t("timeline_navigation_help"))
    schedule_starts = []
    schedule_finishes = []
    # Keep the same time axis when toggling durations so bar lengths are comparable.
    range_plans = [original_baseline, original_optimized]
    if ai_error is None:
        range_plans.extend([ai_baseline, ai_optimized])
    for current_plan in range_plans:
        if not current_plan.empty:
            starts = current_plan[SETUP_START_COL].where(current_plan[SETUP_DURATION_COL] > 0, current_plan[PROCESS_START_COL])
            schedule_starts.extend(starts.tolist())
            schedule_finishes.extend(current_plan[FINISH_COL].tolist())
    timeline_start = min(schedule_starts, default=planning_start)
    timeline_end = max(schedule_finishes, default=planning_start + timedelta(hours=1))
    timeline_span = max(timeline_end - timeline_start, timedelta(hours=1))
    timeline_offset = timeline_span * (0.12 * st.session_state._timeline_pan_steps)
    timeline_range = [timeline_start + timeline_offset, timeline_end + timeline_offset]
    st.caption(("Zaman ekseni iki süre senaryosu için ortak tutulur. Gösterilen süreler: " if language == "Türkçe" else
                "The time axis is shared across both duration scenarios. Displayed durations: ") + duration_source)
    columns = st.columns(len(plans))
    for chart_index, (column, (title, plan)) in enumerate(zip(columns, plans)):
        with column:
            st.markdown(f"**{title} · {duration_source}**")
            segments = []
            for row in plan.to_dict("records"):
                if row["Hazırlık"] > 0:
                    segments.append({"Job": row["Job"], "Component": row["Component"], "Machine": machine_label(row["Makine"], language), "Phase": t("setup_stage"), "Start": row["Hazırlık başlangıç"], "Finish": row["İşlem başlangıç"], "Duration (h)": row["Hazırlık"]})
                segments.append({"Job": row["Job"], "Component": row["Component"], "Machine": machine_label(row["Makine"], language), "Phase": t("processing_stage"), "Start": row["İşlem başlangıç"], "Finish": row["Bitiş"], "Duration (h)": row["İşlem"]})
            if not segments:
                st.info(t("no_jobs"))
                continue
            chart = pd.DataFrame(segments)
            fig = px.timeline(chart, x_start="Start", x_end="Finish", y="Machine", color="Phase", text="Job", color_discrete_map={t("setup_stage"): "#f0a64a", t("processing_stage"): "#5865f2"}, hover_data={"Component": True, "Duration (h)": ":.1f", "Start": False, "Finish": False})
            machine_order = [machine_label(m, language) for m in MACHINES]
            fig.update_yaxes(autorange="reversed", title=None, categoryorder="array", categoryarray=machine_order)
            fig.update_xaxes(title=t("production_time"), tickformat="%d %b<br>%H:%M", gridcolor="rgba(128,128,128,0.25)", range=timeline_range)
            fig.update_layout(height=400, margin=dict(l=5, r=5, t=48, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title=None, bargap=.28, dragmode="pan", uirevision=f"schedule-{view}-{chart_index}-{st.session_state._timeline_pan_steps}-{schedule_revision}")
            fig.update_traces(textposition="inside", insidetextanchor="middle")
            chart_config = {"displayModeBar": True, "displaylogo": False, "responsive": True, "scrollZoom": True, "modeBarButtons": [["zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]]}
            st.plotly_chart(fig, width="stretch", key=f"gantt-{chart_index}", config=chart_config)

    if outcomes is not None:
        render_delivery_table(outcomes, use_ai, language)

    def machine_hours(plan, column):
        if plan.empty:
            return [0.0] * len(MACHINES)
        return plan.groupby("Makine")[column].sum().reindex(MACHINES, fill_value=0).values

    usage = pd.DataFrame({"Machine": [machine_label(m, language) for m in MACHINES], t("baseline_processing"): machine_hours(baseline, "İşlem"), t("baseline_setup"): machine_hours(baseline, "Hazırlık"), t("optimized_processing"): machine_hours(optimized, "İşlem"), t("optimized_setup"): machine_hours(optimized, "Hazırlık")})
    st.markdown(f"#### {t('usage_summary')}")
    st.dataframe(usage, hide_index=True, width="stretch")

with tab_jobs:
    capabilities = " · ".join(f"{machine_label(m, language)}: {', '.join(OP_EN[o] if language == 'English' else o for o in ops)}" for m, ops in MACHINES.items())
    st.caption(t("time_note").format(start=planning_start.strftime("%d %b %Y %H:%M")) + capabilities)
    if jobs.empty:
        st.info(t("no_jobs"))
    else:
        display_jobs = jobs.rename(columns=FIELD_EN if language == "English" else {"Component": "Par\u00e7a / bile\u015fen ad\u0131"}).copy()
        if language == "English":
            display_jobs["Operation"] = display_jobs["Operation"].map(OP_EN)
            date_columns = ["Due date & time", "Material ready date & time"]
        else:
            display_jobs = display_jobs.rename(columns={"Assigned machine": "Makine atamasi", "Due at": "Teslim tarihi / saati", "Material ready at": "Malzeme haz\\u0131r tarihi / saati"})
            date_columns = ["Teslim tarihi / saati", "Malzeme haz\\u0131r tarihi / saati"]
        for date_column in date_columns:
            display_jobs[date_column] = pd.to_datetime(display_jobs[date_column]).dt.strftime("%Y-%m-%d %H:%M")
        machine_column = "Machine assignment" if language == "English" else "Makine atamasi"
        display_jobs[machine_column] = display_jobs[machine_column].map(
            lambda value: assignment_label(value if isinstance(value, str) and value else AUTO_ASSIGN, language)
        )
        st.dataframe(display_jobs, hide_index=True, width="stretch", column_config={"Processing time (h)" if language == "English" else "Süre (saat)": st.column_config.NumberColumn(format="%.1f h" if language == "English" else "%.1f sa"), "Priority" if language == "English" else "Öncelik": st.column_config.ProgressColumn(min_value=1, max_value=5)})

with tab_advice:
    st.markdown(f"#### {t('what_changed')}")
    if jobs.empty:
        st.info(t("no_jobs"))
    else:
        changes = baseline.merge(optimized, on="Job", suffixes=("_eski", "_yeni"))
        assigned = changes[changes["Makine_eski"] != changes["Makine_yeni"]]
        moved = changes[(changes["Makine_eski"] == changes["Makine_yeni"]) & (changes["Hazırlık başlangıç_eski"] != changes["Hazırlık başlangıç_yeni"])]
        for _, row in assigned.iterrows():
            operation = OP_EN[row["Operasyon_eski"]] if language == "English" else row["Operasyon_eski"]
            old_machine = machine_label(row["Makine_eski"], language)
            new_machine = machine_label(row["Makine_yeni"], language)
            if language == "English":
                st.info(f"**{row['Job']}** ({operation}) assigned to **{new_machine}** instead of **{old_machine}** because it had the earliest estimated completion among capable machines.")
            else:
                st.info(f"**{row['Job']}** ({operation}): {old_machine} yerine **{new_machine}**, uygun makineler arasındaki en erken tahmini bitişi sağladığı için seçildi.")
        for _, row in moved.head(8).iterrows():
            shift = (row["Hazırlık başlangıç_eski"] - row["Hazırlık başlangıç_yeni"]).total_seconds() / 3600
            if language == "English":
                message = "shift_earlier" if shift > 0 else "shift_later"
                st.info(f"**{row['Job']}** {t(message).format(shift=abs(shift), priority=row['Öncelik_eski'], due=row['Teslim (saat)_eski'])}")
            else:
                message = "shift_earlier_tr" if shift > 0 else "shift_later_tr"
                st.info(f"**{row['Job']}** {t(message).format(shift=abs(shift), priority=row['Öncelik_eski'], due=row['Teslim (saat)_eski'])}")
        if not len(assigned) and not len(moved):
            st.success(t("no_change"))
    st.caption(t("optimized_note"))

st.markdown(f'<p class="muted">🟢 {t("footer")}</p>', unsafe_allow_html=True)
