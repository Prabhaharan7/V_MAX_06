"""
SIF Sentinel AI - Synthetic Seed Data Generator
Smart India Hackathon 2026 (Problem Statement PS 26165 - Oil India Limited)

Generates:
- 8 Oil & Gas sites across Assam, Rajasthan, and Gujarat
- 9 HSE users & site supervisors
- 300 realistic synthetic safety observation reports:
  * ~60% (180) Non-SIF / Low Severity (housekeeping, PPE labeling, minor clutter)
  * ~25% (75) SIF-Potential tied to IOGP Life-Saving Rules (informal field jargon, high-energy precursors)
  * ~15% (45) Ambiguous / Borderline cases populating the review_queue
- Spatio-temporal distribution with Monsoon season spikes (June - Sept)
- Precursor patterns, monthly safety indices, barrier failure logs, and alerts
- 10 Historical Fatality Case Summaries for the Safety Memory feature (case_library)
"""

import asyncio
import os
import random
import sys
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Tuple

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func, delete, text
from app.core.database import Base, engine, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.entities import (
    UserRole,
    ReportType,
    SIFLabel,
    ReportStatus,
    BarrierSeverity,
    PatternTrend,
    Site,
    User,
    Report,
    ReportLSRTag,
    BarrierFailure,
    PrecursorPattern,
    SafetyIndex,
    ReviewQueue,
    ModelFeedbackLog,
    Alert,
    AuditLog,
    CaseLibrary,
)
from app.ml.precursor_detector import detector


# ==============================================================================
# 1. Sites Data (Assam, Rajasthan, Gujarat Oil & Gas Assets)
# ==============================================================================

SITES_DATA = [
    {
        "name": "Duliajan Drilling Rig D-04 (Well NH-48)",
        "location_lat": 27.3587,
        "location_lng": 95.3192,
        "region": "Upper Assam Basin",
        "operation_type": "Drilling",
    },
    {
        "name": "Digboi Heritage Field Wellpad WP-12",
        "location_lat": 27.3912,
        "location_lng": 95.6185,
        "region": "Upper Assam Basin",
        "operation_type": "Production",
    },
    {
        "name": "Moran GGS-03 (Gas Gathering Station)",
        "location_lat": 27.1852,
        "location_lng": 94.9284,
        "region": "Upper Assam Basin",
        "operation_type": "Production",
    },
    {
        "name": "Naharkatia Trunk Pipeline Manifold Station",
        "location_lat": 27.2845,
        "location_lng": 95.3468,
        "region": "Upper Assam Basin",
        "operation_type": "Pipeline",
    },
    {
        "name": "Barmer Heavy Oil Cluster Pad B-07",
        "location_lat": 25.7532,
        "location_lng": 71.3965,
        "region": "Rajasthan Onshore",
        "operation_type": "Workover",
    },
    {
        "name": "Jaisalmer Gas Processing Terminal",
        "location_lat": 26.9157,
        "location_lng": 70.9083,
        "region": "Rajasthan Onshore",
        "operation_type": "Refining",
    },
    {
        "name": "Mehsana Workover Rig MW-19",
        "location_lat": 23.5880,
        "location_lng": 72.3693,
        "region": "Gujarat Cambay Basin",
        "operation_type": "Workover",
    },
    {
        "name": "Ankleshwar Tank Farm & Manifold TF-02",
        "location_lat": 21.6264,
        "location_lng": 73.0031,
        "region": "Gujarat Cambay Basin",
        "operation_type": "Tank Cleaning",
    },
]


# ==============================================================================
# 2. Users Data
# ==============================================================================

USERS_DATA = [
    {"name": "Pranab Phukan (Lead HSE)", "email": "pranab.hse@oilindia.in", "role": UserRole.hse_officer, "site_idx": 0, "password": "OilIndia@2026"},
    {"name": "Arun Borah (Rig Supt)", "email": "arun.manager@oilindia.in", "role": UserRole.site_manager, "site_idx": 0, "password": "OilIndia@2026"},
    {"name": "HQ System Admin", "email": "admin@oilindia.in", "role": UserRole.admin, "site_idx": 0, "password": "Admin@2026"},
    {"name": "Ananya Gogoi (Field HSE)", "email": "ananya.gogoi@oilindia.in", "role": UserRole.hse_officer, "site_idx": 1, "password": "OilIndia@2026"},
    {"name": "Diganta Saikia (GGS Supv)", "email": "diganta.saikia@oilindia.in", "role": UserRole.site_manager, "site_idx": 2, "password": "OilIndia@2026"},
    {"name": "Rathore Vikram Singh (HSE)", "email": "vikram.rathore@oilindia.in", "role": UserRole.hse_officer, "site_idx": 4, "password": "OilIndia@2026"},
    {"name": "Hitesh Patel (Workover Lead)", "email": "hitesh.patel@oilindia.in", "role": UserRole.site_manager, "site_idx": 6, "password": "OilIndia@2026"},
    {"name": "Nayan Das (Pipeline HSE)", "email": "nayan.das@oilindia.in", "role": UserRole.hse_officer, "site_idx": 3, "password": "OilIndia@2026"},
    {"name": "Kavita Sharma (Terminal HSE)", "email": "kavita.sharma@oilindia.in", "role": UserRole.hse_officer, "site_idx": 5, "password": "OilIndia@2026"},
    {"name": "Sunil Solanki (Tank Farm Supv)", "email": "sunil.solanki@oilindia.in", "role": UserRole.site_manager, "site_idx": 7, "password": "OilIndia@2026"},
]


# ==============================================================================
# 3. Report Templates & Realistic Indian Oilfield Jargon
# ==============================================================================

# IOGP Life-Saving Rules templates (~25% SIF potential)
SIF_TEMPLATES = [
    # Energy Isolation
    {
        "lsr": "Energy Isolation",
        "barrier": "Isolation Confirmation (LOTO)",
        "activity": "Electrical / Pump Maintenance",
        "title": "LOTO padlock omitted on 415V MCC panel breaker during booster pump seal overhaul",
        "text": "Contractor electrician noticed breaker 4B-12 for booster pump was turned off at the local isolator only, but LOTO hasp & danger tag not applied at main MCC bus. Mechanical crew already started unbolting pump flange with live bus 2 feet away. Stop work called immediately.",
        "phrase": "breaker turned off at local isolator only, LOTO hasp not applied at main MCC bus with crew unbolting flange",
    },
    {
        "lsr": "Energy Isolation",
        "barrier": "Positive Physical Isolation (Spade/Blind)",
        "activity": "Pipeline Maintenance",
        "title": "Spectacle blind not flipped to closed position on 600# fuel gas manifold line",
        "text": "During pig receiver barrel maintenance, isolation valve 12-FG was closed but spectacle blind was left in open position without bleed depressurization check. Trapped pressure hissed violently when technician cracked first bonnet bolt.",
        "phrase": "spectacle blind left in open position without bleed check, trapped pressure hissed when cracking bolt",
    },
    # Hot Work
    {
        "lsr": "Hot Work",
        "barrier": "Continuous Gas Monitoring & Spark Containment",
        "activity": "Facility Modification",
        "title": "Grinding & tack welding within 4m of live skimmer pit without continuous LEL detector",
        "text": "Fabricator started structural tack welding on pipe support adjacent to open effluent skimmer pit. Portable 4-gas monitor was lying inside toolbox rather than continuous sniffing at pit boundary. LEL alarm could have ignited condensate sheen.",
        "phrase": "structural tack welding 4m from open effluent pit without continuous LEL gas monitor active",
    },
    {
        "lsr": "Hot Work",
        "barrier": "Fire Blanket & Drainage Sealing",
        "activity": "Workover",
        "title": "Slag droplets falling onto oily cellar drain during wellhead flange grinding",
        "text": "Welder helper failed to place fire-retardant blanket over open wellhead cellar pit while grinding tubing spool. Red hot metal sparks observed showering onto oily mud accumulation inside cellar.",
        "phrase": "sparks showering onto oily mud accumulation inside wellhead cellar without fire blanket",
    },
    # Confined Space Entry
    {
        "lsr": "Confined Space Entry",
        "barrier": "Atmospheric Testing & Standby Attendant",
        "activity": "Tank Cleaning",
        "title": "Contractor entered mud tank #2 before gas test clearance and attendant missing from manway",
        "text": "During mud tank desanding, 2 contract cleaners climbed inside compartment #2 through top hatch. Gas testing certificate was expired by 3 hours, H2S sensor was not calibrated, and dedicated standby man was away fetching chai.",
        "phrase": "climbed inside mud tank with expired gas test, uncalibrated H2S sensor, and standby attendant absent",
    },
    {
        "lsr": "Confined Space Entry",
        "barrier": "Forced Ventilation & Breathing Apparatus",
        "activity": "Tank Cleaning",
        "title": "Blower duct dislodged from crude storage tank manhole during sludge scraping",
        "text": "Exhauster blower flexible duct slipped off the manway collar of crude tank T-104. Hydrocarbon vapor concentration rapidly spiked inside enclosed bottom. Entrant had removed half-face respirator due to heat.",
        "phrase": "ventilation exhauster duct dislodged, hydrocarbon vapor spiked inside tank with respirator removed",
    },
    # Line of Fire
    {
        "lsr": "Line of Fire",
        "barrier": "Zone Exclusion & Restraining Whipsocks",
        "activity": "Drilling",
        "title": "Roughneck positioned inside rotary tongs snub line bite zone during casing make-up",
        "text": "During 9-5/8 inch casing running on Rig 4, lead roughneck stood directly between drill pipe rotary tongs and derrick leg within the snub line snapback arc. Hydraulic tong operator engaged high torque without confirming clear red zone.",
        "phrase": "stood between rotary tongs and derrick leg within snub line snapback arc during high torque",
    },
    {
        "lsr": "Line of Fire",
        "barrier": "High Pressure Whip Check & Restraint",
        "activity": "Drilling",
        "title": "Chiksan high pressure mud line whip-check cable disconnected at standpipe manifold",
        "text": "Rig floor inspection revealed safety whip-check wire rope had sheared clamp on 5,000 psi Chiksan pumping line. High vibration during circulating kill mud could cause uncontrolled flailing line.",
        "phrase": "safety whip-check wire sheared on 5,000 psi line during circulating kill mud",
    },
    # Working at Height
    {
        "lsr": "Working at Height",
        "barrier": "100% Fall Arrest Hook-up",
        "activity": "Drilling",
        "title": "Derrickman detached harness lanyard while crossing monkey board at 90ft mast",
        "text": "While racking 5-inch drill pipe stands, derrickman unhooked twin-tail lanyard from mast lifeline for 40 seconds to reach stuck stand latch on fingerboard. No secondary inertia reel attached at 90 ft elevation.",
        "phrase": "unhooked lanyard from mast lifeline for 40 seconds at 90 ft monkey board elevation",
    },
    {
        "lsr": "Working at Height",
        "barrier": "Dropped Object Prevention (DROPS) & Toe Boards",
        "activity": "Workover",
        "title": "Unsecured 18-inch pipe wrench left on crown block platform over active rig floor",
        "text": "After crown sheave greasing, mechanic left heavy steel pipe wrench loose on crown beam grating without lanyard tether. Severe rig mast vibration during tripping could have dropped tool directly onto drill floor.",
        "phrase": "heavy steel pipe wrench left on crown block without lanyard tether over active rig floor",
    },
    # Safe Mechanical Lifting
    {
        "lsr": "Safe Mechanical Lifting",
        "barrier": "Certified Rigging & Load Path Clearance",
        "activity": "Lifting / Rig Move",
        "title": "Severe wire rope birdcaging & kink on hydra crane hoist while lifting 10-ton BOP stack",
        "text": "Hydra mobile crane was hoisting BOP ram block assembly. Rig rigger observed outer strands broken and visible birdcaging on main hoist rope. Load was suspended 1.5m above walkway with personnel passing underneath.",
        "phrase": "crane hoist rope broken strands birdcaging with 10-ton load suspended over walkway",
    },
    {
        "lsr": "Safe Mechanical Lifting",
        "barrier": "Tagline Use & Crane Outrigger Stabilization",
        "activity": "Lifting Operations",
        "title": "Crane outrigger sinking into waterlogged monsoon soil during generator skidding",
        "text": "During heavy 600 kVA rig genset placement, crane right rear outrigger timber pad crushed into soft muddy soil. Crane tipped 6 degrees with load swinging uncontrollably toward fuel day tank.",
        "phrase": "crane outrigger sank into waterlogged monsoon soil, crane tipped 6 deg with swinging load",
    },
    # Driving
    {
        "lsr": "Driving",
        "barrier": "Vehicle Safety Systems & Route Risk Compliance",
        "activity": "Vehicle Movement",
        "title": "Crude oil tanker speeding on unpaved bund road with defective spark arrestor",
        "text": "40 KL bowser truck was driving at 45 km/h on narrow single-lane tea garden bund road (limit 20 km/h). Spark arrestor baffle on exhaust was rusted open as truck approached Wellhead #14 gas zone.",
        "phrase": "crude tanker speeding on narrow bund road with rusted-out open spark arrestor near wellhead",
    },
    # Work Authorisation
    {
        "lsr": "Work Authorisation",
        "barrier": "Permit Scope & SIMOPS Validation",
        "activity": "Facility Modification",
        "title": "Cold work permit utilized for high-speed angle grinding inside live separator module",
        "text": "Maintenance crew presented Cold Work Permit (CWP) but was actively operating 9-inch electric angle grinder creating heavy continuous sparks inside Class 1 Div 1 gas separator enclosure without Hot Work Permit authorization.",
        "phrase": "operating electric angle grinder under cold work permit inside Class 1 Div 1 enclosure",
    },
    # Bypassing Safety Controls
    {
        "lsr": "Bypassing Safety Controls",
        "barrier": "Management of Change (MOC) & Interlock Integrity",
        "activity": "Production",
        "title": "High-pressure separator ESD trip switch physically wedged with wooden wedge",
        "text": "During morning rounds at Moran GGS, operator discovered emergency high-pressure dump trip lever PSH-401 wedged open with wooden wedge to prevent nuisance trips during slug flow. Overpressure protection defeated.",
        "phrase": "high pressure emergency dump trip switch wedged open with wooden wedge defeating interlock",
    },
]

# Non-SIF / Low Severity templates (~60%)
NON_SIF_TEMPLATES = [
    {
        "activity": "Housekeeping",
        "title": "Empty water bottles and food wrappers discarded near tool container",
        "text": "Plastic water bottles, tea cups and biscuit wrappers left on gravel beside mechanical tool container. Bin available 10m away. Housekeeping instructed to site helper crew.",
    },
    {
        "activity": "PPE Compliance",
        "title": "Torn cotton gloves used by warehouse helper handling wooden crates",
        "text": "Helper in warehouse material yard observed using worn cloth gloves with exposed fingers while moving wooden pallets. Sent back to store to reissue standard leather work gloves.",
    },
    {
        "activity": "Housekeeping",
        "title": "Uncoiled washdown water hose creating minor tripping hazard on mud lab walkway",
        "text": "1-inch green water hose left looped across walkway entrance of mud testing lab cabin after floor cleaning. Hose rolled up and placed onto hanger rack.",
    },
    {
        "activity": "Facility Inspection",
        "title": "Emergency eyewash station inspection tag overdue by 2 weeks",
        "text": "Weekly inspection sign-off tag on eye wash unit near chemical dosing pump was last dated 14 days ago. Tested station water flow - nozzle clean and pressure normal. Tag updated.",
    },
    {
        "activity": "Storage & Labeling",
        "title": "Secondary diesel drum missing GHS hazard sticker in auxiliary generator shed",
        "text": "200L lube oil drum in secondary storage shed had faded handwritten chalk label instead of printed GHS flammable liquid sticker. Storekeeper notified to apply proper vinyl placard.",
    },
    {
        "activity": "Office & Welfare",
        "title": "Drinking water dispenser cooler drip tray overflowing in bunkhouse mess",
        "text": "Water dispenser tray in drill crew living bunkhouse full with water dripping onto vinyl floor mat. Emptied and dried with mop.",
    },
    {
        "activity": "Housekeeping",
        "title": "Oily cotton waste rag found inside general trash bin instead of red bio-hazard bin",
        "text": "During routine 5S audit, two oily cotton rags from compressor wipe-down were found in yellow general bin. Transferred to hazardous oily waste drum.",
    },
    {
        "activity": "PPE Compliance",
        "title": "Visitor entered perimeter gate wearing non-tinted safety spectacles in bright sun",
        "text": "Third-party courier entered site office compound with standard clear safety glasses complaining of sun glare. Offered tinted UV spectacles.",
    },
    {
        "activity": "Civil Work",
        "title": "Loose gravel scattered on paved pathway near administrative bunkhouse",
        "text": "Small pile of fine gravel washed onto asphalt walkway after light morning drizzle. Swept and cleared to prevent slip hazard.",
    },
    {
        "activity": "Lighting",
        "title": "One fluorescent tube flickering in electrical workshop shed",
        "text": "Overhead tube light #3 flickering in rewinding room. Electrician notified to replace starter and LED tube during daylight break.",
    },
    {
        "activity": "Vehicle Movement",
        "title": "Pickup truck parked facing forward instead of reverse park in marked bay",
        "text": "Contractor Bolero camper vehicle parked nose-in at site parking bay violating reverse-parking safety rule for quick emergency evacuation. Driver briefed and reparked.",
    },
    {
        "activity": "Storage & Labeling",
        "title": "Bentonite mud sacks stacked 12 high exceeding 8 sack stack guideline",
        "text": "Mud chemical storage shed had pallet with bentonite sacks stacked 12 layers high. Stack was stable but exceeded 8-sack site guideline. Restacked into two pallets.",
    }
]

# Ambiguous / Borderline templates (~15%)
AMBIGUOUS_TEMPLATES = [
    {
        "activity": "Production",
        "title": "Faint rotten egg smell noted near test separator manifold during windy afternoon",
        "text": "Field operator reported brief rotten egg / sour odor downwind of test separator header. Handheld detector showed 1-2 ppm H2S intermittently, wind blowing 25 km/h. Flange soap bubble test was inconclusive.",
        "reason": "Potential low-level sour gas leak vs transient atmospheric pocket. Needs barrier verification and sensor calibration check.",
    },
    {
        "activity": "Drilling",
        "title": "Trip tank level indicator sluggish during 10-stand pipe pull",
        "text": "Driller observed trip tank float gauge responded slowly during 5-inch drill pipe tripping. Mud logger calculated 0.8 barrel discrepancy between theoretical and actual fill. Driller paused tripping and circulated bottoms up.",
        "reason": "Borderline well control precursor: mechanical float friction vs initial slow gas influx. High consequence potential requiring SME review.",
    },
    {
        "activity": "Mechanical Lifting",
        "title": "Auxiliary crane hoist made grinding screeching sound during 3-ton pump shift",
        "text": "Crane operator noticed intermittent high-pitched noise from hoist gearbox while lowering 3-ton water injection skid. Crane log showed annual inspection done last month, no visible rope distortion.",
        "reason": "Mechanical integrity concern on hoisting equipment. Evaluate if lifting barrier compromised.",
    },
    {
        "activity": "Electrical Work",
        "title": "UPS battery bank terminal showed white corrosion powder and slight warmth",
        "text": "During weekly substation check, battery cell #18 terminal post had substantial sulfate powder deposit and felt slightly warm to touch. Voltage was within tolerance.",
        "reason": "Potential thermal runaway / arc hazard in battery room vs routine maintenance item.",
    },
    {
        "activity": "Pipeline Maintenance",
        "title": "Pipeline right-of-way ground dampness spotted 20m from crude trunk line",
        "text": "Line walker spotted 3m dark damp soil patch along Moran-Duliajan 14-inch pipeline corridor after rain. Hydrocarbon sniffer probe gave zero reading. Water or minor pinhole seepage unconfirmed.",
        "reason": "Potential buried pipeline pinhole leak vs surface rainwater pooling. Requires soil sample assay.",
    },
    {
        "activity": "Working at Height",
        "title": "Scaffold handrail clamp showed 2mm play when tested by safety officer",
        "text": "Inspection on workover mast second-level scaffold revealed single swivel coupler had slight rotational play when shaken. Remaining 3 clamps rigid.",
        "reason": "Structural scaffold stability query. Borderline working at height precursor.",
    },
    {
        "activity": "Work Authorisation",
        "title": "Hot work permit fire-watcher signature signed in pencil and dated yesterday",
        "text": "During afternoon random audit on wellhead deck repair, PTW document had fire-watcher section signed in pencil with date reflecting yesterday's shift handover. Work was actively in progress with fire extinguisher present.",
        "reason": "Administrative permit integrity flaw vs operational safety control breakdown.",
    }
]


# ==============================================================================
# 4. Historical Fatality Case Summaries (CaseLibrary - Safety Memory)
# ==============================================================================

HISTORICAL_FATALITY_CASES = [
    {
        "title": "Catastrophic Well Kick & Uncontrolled Gas Influx Ignition during Tripping",
        "summary": "During tripping out of 8-1/2 inch hole, crew failed to monitor trip tank displacement accurately. A 25-barrel gas kick entered the wellbore undetected. When the swabbing gas reached the surface, annular BOP was closed too late, gas vented into rig substructure and ignited on non-explosion-proof electrical generator.",
        "incident_year": 2018,
        "operation_type": "Drilling",
        "lsr_category": "Well Control & Blowout Risk",
        "failed_barriers": [
            "Trip tank continuous displacement monitoring bypassed",
            "Delayed soft shut-in protocol on Blowout Preventer (BOP)",
            "Non-certified ignition sources in hazardous Zone 1 substructure"
        ],
        "root_causes": "Inadequate tripping monitoring, poor handovers between driller and mud logger, lack of routine blowout drill practice.",
        "lessons_learned": "Mandatory auto-alarm trip tank sensors, strict shut-in on 5-barrel pit gain, elimination of non-EX rated equipment from 50ft radius."
    },
    {
        "title": "Fatal Fall from Derrick Monkey Board during High-Wind Casing Stabbing",
        "summary": "A derrickman working at 95 feet elevation on the monkeyboard disconnected his inertia reel harness lanyard to reach a jammed casing stand latch during 40 knot sudden wind gusts. Derrickman lost balance and fell to the rig floor.",
        "incident_year": 2017,
        "operation_type": "Drilling",
        "lsr_category": "Working at Height",
        "failed_barriers": [
            "100% dual-lanyard continuous fall protection defeated",
            "Adverse weather work cessation threshold (gale winds) ignored",
            "Absence of secondary self-retracting lifeline (SRL)"
        ],
        "root_causes": "Work pressure to beat weather window, defective latching mechanism requiring manual reach, failure to enforce 100% tie-off policy.",
        "lessons_learned": "Install remote pneumatic fingerboard latches, strict stop-work authority on wind speed > 25 knots at derrick height."
    },
    {
        "title": "Fatal H2S Gas Asphyxiation inside Unventilated Crude Oil Storage Tank",
        "summary": "Two contractor workers entered a 5,000 m3 crude storage tank during turnaround cleaning without mechanical exhauster ventilation and with an uncalibrated portable gas tester. High-concentration H2S pockets released from disturbed bottom sludge caused instantaneous fatal asphyxiation.",
        "incident_year": 2020,
        "operation_type": "Tank Cleaning",
        "lsr_category": "Confined Space Entry",
        "failed_barriers": [
            "Continuous forced air ventilation not established",
            "Atmospheric multi-point gas testing protocol not executed",
            "Standby rescue team and self-contained breathing apparatus (SCBA) absent"
        ],
        "root_causes": "Contractor safety competency deficiency, superficial permit-to-work signoff without physical field verification.",
        "lessons_learned": "Enforce continuous multi-level gas monitoring, mandatory supplied air respirators for all sludge agitations, strict entry barrier gates."
    },
    {
        "title": "Electrocution Fatality during 3.3kV MCC Busbar Maintenance without LOTO",
        "summary": "An electrical technician began tightening connection lugs on a 3.3kV Motor Control Center (MCC) cubicle assuming the upstream breaker was isolated. The main incomer breaker had been left energized by an alternate shift technician without Lockout/Tagout locks or test-before-touch verification.",
        "incident_year": 2021,
        "operation_type": "Electrical Work",
        "lsr_category": "Energy Isolation",
        "failed_barriers": [
            "Lockout/Tagout (LOTO) personal padlocks and hasps omitted",
            "Zero energy verification (test-before-touch) with certified voltage detector omitted",
            "Single-point work authorization without shift-to-shift isolation handover"
        ],
        "root_causes": "Complacency, lack of individual safety padlock enforcement, defective shift isolation logbook.",
        "lessons_learned": "Mandatory positive electrical LOTO verification witnessed by HSE, calibrated live-line voltage proximity tester mandatory before panel entry."
    },
    {
        "title": "High-Pressure Manifold Flange Rupture & Struck-By Fatality during Hydrotesting",
        "summary": "During a 10,000 psi hydrotest on a newly fabricated choke manifold, a temporary blind flange failed catastrophically along a defective weld seam. The high-velocity metal projectile struck an engineer standing 12 meters away inside the test barricade zone.",
        "incident_year": 2022,
        "operation_type": "Pipeline Maintenance",
        "lsr_category": "Line of Fire",
        "failed_barriers": [
            "Barricaded exclusion zone radius inadequate for 10k psi rating",
            "Personnel remained inside line of fire during pressure ramp-up",
            "Uncertified shop-fabricated temporary testing blind flange used"
        ],
        "root_causes": "Substandard hydrostatic test procedure, lack of remote pressure readouts, failure to treat pressure as lethal energy.",
        "lessons_learned": "Mandatory steel blast bunkers or remote cameras for tests > 3,000 psi, strict 30m cleared perimeter, certified OEM blind flanges only."
    },
    {
        "title": "Crane Boom Failure & Crushed by 14-Ton Substructure Module during Lift",
        "summary": "A 50-ton hydraulic mobile crane attempted to lift a 14-ton rig substructure section at an excessive working radius over soft backfilled terrain without load cell calibration. The boom buckled and dropped the load onto two riggers standing beneath.",
        "incident_year": 2019,
        "operation_type": "Safe Mechanical Lifting",
        "lsr_category": "Safe Mechanical Lifting",
        "failed_barriers": [
            "Critical lift plan calculations bypassed for radius and capacity",
            "Crane outrigger ground bearing pressure evaluation omitted",
            "Personnel positioned under suspended load (no tagline guidance)"
        ],
        "root_causes": "Overconfidence in crane capacity, pressure to accelerate rig move schedule, missing crane automatic safe load indicator (RCI).",
        "lessons_learned": "All lifts > 10 tons classified as Critical requiring 3rd-party engineering review, zero tolerance for personnel under suspended load."
    },
    {
        "title": "Vapor Cloud Ignition & Flash Fire during Hot Grinding on Condensate Drain",
        "summary": "Mechanical contractors used an electric angle grinder on a flare header support beam located 3 meters from an atmospheric condensate drain pot. Hot grinding sparks landed on flammable vapors discharging from the vent, causing a localized vapor cloud explosion and severe flash fire.",
        "incident_year": 2016,
        "operation_type": "Production",
        "lsr_category": "Hot Work",
        "failed_barriers": [
            "15-meter hot work clearance zone around hydrocarbon vents violated",
            "Continuous combustible gas (LEL) monitoring not maintained",
            "Fire blankets and spark containment habitat not erected"
        ],
        "root_causes": "Poor hazard identification during PTW walk-around, failure to locate atmospheric hydrocarbon relief points.",
        "lessons_learned": "Mandatory pressurized welding habitats within 15m of hydrocarbon vessels, automated LEL shut-off switches on welding machines."
    },
    {
        "title": "Crude Oil Road Bowser Rollover into Ravine during Monsoon Rainstorm",
        "summary": "A loaded 40,000L crude oil articulated tanker overturned on an unpaved slope along an oilfield access road during torrential monsoon rain. The vehicle rolled down a 15-meter embankment due to road shoulder collapse and brake fade.",
        "incident_year": 2023,
        "operation_type": "Vehicle Movement",
        "lsr_category": "Driving",
        "failed_barriers": [
            "Journey management weather risk mitigation ignored during flash storm",
            "Vehicle rollover protection and speed limiter maintenance neglected",
            "Road structural integrity inspection post-rain neglected"
        ],
        "root_causes": "Inadequate journey management, poor road drainage infrastructure, driving during night red-alert weather warnings.",
        "lessons_learned": "Mandatory GPS geofencing & speed monitoring, suspension of heavy liquid transport during rainfall > 50mm/day."
    },
    {
        "title": "Lethal Stored Hydraulic Energy Release during Iron Roughneck Piston Servicing",
        "summary": "A rig maintenance technician began loosening hydraulic cylinder retaining cap bolts on the iron roughneck without bleeding the high-pressure accumulator circuit (3,000 psi). The trapped oil pressure shot the cylinder rod and end-cap forward with lethal force.",
        "incident_year": 2019,
        "operation_type": "Workover",
        "lsr_category": "Energy Isolation",
        "failed_barriers": [
            "Hydraulic accumulator residual pressure discharge step skipped",
            "Zero pressure gauge confirmation omitted prior to mechanical teardown",
            "Technician positioned in direct line of fire of cylinder piston stroke"
        ],
        "root_causes": "Lack of written OEM step-by-step hydraulic maintenance checklist, assumption that electrical power isolation was sufficient.",
        "lessons_learned": "Isolation procedures must explicitly mandate thermal, pneumatic and hydraulic stored energy bleed-down with double-block confirmation."
    },
    {
        "title": "Sour Gas Influx Explosion following Bypassed Fixed Fire & Gas Detector",
        "summary": "Operators at a gas dehydration terminal jumpered two optical flame detectors and bypassed the acoustic gas leak sensor to prevent recurring nuisance trips. An unignited high-pressure sour gas leak from a compressor seal accumulated inside the compressor building and ignited when a non-EX lighting switch was operated.",
        "incident_year": 2021,
        "operation_type": "Refining",
        "lsr_category": "Bypassing Safety Controls",
        "failed_barriers": [
            "Safety-critical bypass authorized without formal Risk Assessment & MOC",
            "Automatic emergency blowdown (ESD) system inhibited",
            "Area gas detection voting logic compromised"
        ],
        "root_causes": "Production-first operational culture, lack of executive oversight on safety system override registries.",
        "lessons_learned": "Any safety critical bypass requires VP approval and expires in 8 hours, automatic daily escalation of active safety overrides."
    }
]


# ==============================================================================
# 5. Helper Functions & Generator
# ==============================================================================

def generate_random_date_last_year(is_monsoon_biased: bool = False) -> datetime:
    """
    Generates a timestamp in the last 365 days.
    If is_monsoon_biased is True, heavily biases towards Indian monsoon months (June, July, August, September).
    """
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)

    if is_monsoon_biased and random.random() < 0.70:
        # Bias to monsoon season (June 1 - Sept 30)
        # Choose random day in monsoon
        target_year = now.year if now.month >= 10 else now.year - 1
        monsoon_start = datetime(target_year, 6, 1, tzinfo=timezone.utc)
        monsoon_end = datetime(target_year, 9, 30, tzinfo=timezone.utc)
        delta_seconds = int((monsoon_end - monsoon_start).total_seconds())
        random_second = random.randint(0, max(delta_seconds, 1))
        dt = monsoon_start + timedelta(seconds=random_second)
        if dt > now:
            dt = now - timedelta(days=random.randint(1, 30))
        return dt
    else:
        delta_seconds = int((now - one_year_ago).total_seconds())
        random_second = random.randint(0, max(delta_seconds, 1))
        return one_year_ago + timedelta(seconds=random_second)


async def seed_database():
    print("=" * 80)
    print("🛡️  SIF SENTINEL AI - SEEDING DATABASE (SIH 2026 PS 26165)")
    print("=" * 80)

    # 1. Ensure extensions and tables exist
    async with engine.begin() as conn:
        print("[1/7] Ensuring pgvector and uuid extensions...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        except Exception:
            pass
        print("[2/7] Creating database schema tables...")
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_reports_count = (await session.execute(select(func.count(Report.id)))).scalar() or 0
        if existing_reports_count > 50:
            print(f"⚠️ Database already contains {existing_reports_count} reports. Cleaning up before re-seeding...")
            await session.execute(delete(AuditLog))
            await session.execute(delete(Alert))
            await session.execute(delete(ModelFeedbackLog))
            await session.execute(delete(ReviewQueue))
            await session.execute(delete(BarrierFailure))
            await session.execute(delete(ReportLSRTag))
            await session.execute(delete(Report))
            await session.execute(delete(SafetyIndex))
            await session.execute(delete(PrecursorPattern))
            await session.execute(delete(User))
            await session.execute(delete(Site))
            await session.execute(delete(CaseLibrary))
            await session.commit()

        # 2. Insert Sites
        print("[3/7] Inserting 8 Oil & Gas assets (Assam, Rajasthan, Gujarat)...")
        created_sites: List[Site] = []
        for site_info in SITES_DATA:
            site = Site(
                name=site_info["name"],
                location_lat=site_info["location_lat"],
                location_lng=site_info["location_lng"],
                region=site_info["region"],
                operation_type=site_info["operation_type"],
            )
            session.add(site)
            created_sites.append(site)
        await session.commit()
        for s in created_sites:
            await session.refresh(s)
        print(f"  ✓ {len(created_sites)} sites created.")

        # 3. Insert Users
        print("[4/7] Inserting HSE officers, Site Managers, and Admins...")
        created_users: List[User] = []
        for u_info in USERS_DATA:
            site_id = created_sites[u_info["site_idx"]].id
            pwd = u_info.get("password", "OilIndia@2026")
            user = User(
                name=u_info["name"],
                email=u_info["email"],
                password_hash=get_password_hash(pwd),
                role=u_info["role"],
                site_id=site_id,
            )
            session.add(user)
            created_users.append(user)
        await session.commit()
        for u in created_users:
            await session.refresh(u)
        print(f"  ✓ {len(created_users)} users created.")

        # 4. Insert 10 Historical Fatality Cases (Safety Memory)
        print("[5/7] Inserting 10 Historical Fatality Case Summaries into case_library...")
        for case in HISTORICAL_FATALITY_CASES:
            emb = detector.generate_dummy_embedding(f"{case['title']} {case['summary']} {case['lessons_learned']}")
            case_entry = CaseLibrary(
                title=case["title"],
                summary=case["summary"],
                incident_year=case["incident_year"],
                operation_type=case["operation_type"],
                lsr_category=case["lsr_category"],
                failed_barriers=case["failed_barriers"],
                root_causes=case["root_causes"],
                lessons_learned=case["lessons_learned"],
                embedding=emb,
            )
            session.add(case_entry)
        await session.commit()
        print(f"  ✓ 10 historical fatality cases inserted for Safety Memory RAG.")

        # 5. Generate 300 Synthetic Reports
        # Breakdown:
        # ~60% (180) Non-SIF / Low Severity
        # ~25% (75) SIF-Potential
        # ~15% (45) Ambiguous / Borderline
        print("[6/7] Generating 300 synthetic safety reports with realistic field narratives...")

        TOTAL_REPORTS = 300
        SIF_COUNT = 75       # 25%
        AMBIGUOUS_COUNT = 45 # 15%
        NON_SIF_COUNT = 180  # 60%

        report_objects: List[Report] = []
        sif_counter = 0
        ambiguous_counter = 0
        non_sif_counter = 0

        # --- A. Generate 75 SIF Reports ---
        for i in range(SIF_COUNT):
            tpl = random.choice(SIF_TEMPLATES)
            site = random.choice(created_sites)
            user = random.choice(created_users)
            # Monsoon bias for crane, fall, slip, line of fire
            is_monsoon_prone = tpl["lsr"] in ["Working at Height", "Safe Mechanical Lifting", "Driving", "Line of Fire"]
            submitted_at = generate_random_date_last_year(is_monsoon_biased=is_monsoon_prone)

            emb = detector.generate_dummy_embedding(f"{tpl['title']} {tpl['text']}")
            rep_type = random.choice([ReportType.near_miss, ReportType.UC, ReportType.incident])

            rep = Report(
                report_type=rep_type,
                raw_text=f"{tpl['title']}. {tpl['text']}",
                submitted_by=user.id,
                site_id=site.id,
                activity=tpl["activity"],
                submitted_at=submitted_at,
                language="en",
                translated_text=None,
                sif_label=SIFLabel.sif_potential,
                sif_confidence=round(random.uniform(0.78, 0.98), 2),
                status=ReportStatus.reviewed,
                embedding=emb,
            )
            session.add(rep)
            await session.flush()

            # Linked LSR Tag
            lsr_tag = ReportLSRTag(
                report_id=rep.id,
                lsr_rule=tpl["lsr"],
                confidence=rep.sif_confidence,
            )
            session.add(lsr_tag)

            # Linked Barrier Failure
            barrier_fail = BarrierFailure(
                report_id=rep.id,
                barrier_type=tpl["barrier"],
                evidence_phrase=tpl["phrase"],
                severity=BarrierSeverity.high if rep.sif_confidence > 0.88 else BarrierSeverity.medium,
            )
            session.add(barrier_fail)

            # Critical Alert for high confidence
            if rep.sif_confidence >= 0.85:
                alert = Alert(
                    report_id=rep.id,
                    alert_type="In-App & SMS",
                    sent_to="rig.superintendent@oilindia.in, hse.duty@oilindia.in",
                    sent_at=submitted_at + timedelta(minutes=random.randint(2, 10)),
                    acknowledged=random.choice([True, False]),
                )
                session.add(alert)

            sif_counter += 1

        # --- B. Generate 45 Ambiguous Reports (Populate Review Queue) ---
        for i in range(AMBIGUOUS_COUNT):
            tpl = random.choice(AMBIGUOUS_TEMPLATES)
            site = random.choice(created_sites)
            user = random.choice(created_users)
            submitted_at = generate_random_date_last_year(is_monsoon_biased=False)

            emb = detector.generate_dummy_embedding(f"{tpl['title']} {tpl['text']}")
            rep_type = random.choice([ReportType.UC, ReportType.UA, ReportType.near_miss])

            rep = Report(
                report_type=rep_type,
                raw_text=f"{tpl['title']}. {tpl['text']}",
                submitted_by=user.id,
                site_id=site.id,
                activity=tpl["activity"],
                submitted_at=submitted_at,
                language="en",
                translated_text=None,
                sif_label=None, # Ambiguous
                sif_confidence=round(random.uniform(0.48, 0.68), 2),
                status=ReportStatus.pending_review,
                embedding=emb,
            )
            session.add(rep)
            await session.flush()

            # Assign review queue
            assigned_hse = random.choice([u for u in created_users if u.role in [UserRole.hse_officer, UserRole.admin]])
            rq = ReviewQueue(
                report_id=rep.id,
                reason=tpl["reason"],
                assigned_to=assigned_hse.id,
                resolved=False,
                corrected_label=None,
                corrected_lsr=None,
            )
            session.add(rq)
            ambiguous_counter += 1

        # --- C. Generate 180 Non-SIF Reports ---
        for i in range(NON_SIF_COUNT):
            tpl = random.choice(NON_SIF_TEMPLATES)
            site = random.choice(created_sites)
            user = random.choice(created_users)
            # Variations in text to avoid identical rows
            var_id = i + 1
            full_title = f"{tpl['title']} (Location Point #{var_id % 15 + 1})"
            full_text = f"{tpl['text']} Observed during Area Inspection shift #{var_id % 3 + 1}."

            submitted_at = generate_random_date_last_year(is_monsoon_biased=False)
            emb = detector.generate_dummy_embedding(f"{full_title} {full_text}")

            rep = Report(
                report_type=random.choice([ReportType.UC, ReportType.UA]),
                raw_text=f"{full_title}. {full_text}",
                submitted_by=user.id,
                site_id=site.id,
                activity=tpl["activity"],
                submitted_at=submitted_at,
                language="en",
                translated_text=None,
                sif_label=SIFLabel.non_sif,
                sif_confidence=round(random.uniform(0.05, 0.32), 2),
                status=random.choice([ReportStatus.reviewed, ReportStatus.auto_confirmed]),
                embedding=emb,
            )
            session.add(rep)
            non_sif_counter += 1

        await session.commit()
        print(f"  ✓ {TOTAL_REPORTS} reports inserted:")
        print(f"    - SIF-Potential: {sif_counter} ({sif_counter/TOTAL_REPORTS*100:.1f}%)")
        print(f"    - Ambiguous (in review queue): {ambiguous_counter} ({ambiguous_counter/TOTAL_REPORTS*100:.1f}%)")
        print(f"    - Non-SIF / Low-Severity: {non_sif_counter} ({non_sif_counter/TOTAL_REPORTS*100:.1f}%)")

        # 6. Generate Precursor Patterns & Safety Indices
        print("[7/7] Computing aggregated precursor patterns and monthly safety indices...")
        
        # Precursor Patterns
        PATTERNS = [
            ("Drilling & Tripping", "Duliajan Rig D-04", "Snub Line & Tong Red Zone", 12, PatternTrend.rising),
            ("Pump Overhaul", "Moran GGS-03", "415V MCC LOTO Padlock", 8, PatternTrend.rising),
            ("Sludge Desanding", "Ankleshwar Tank Farm", "Atmospheric Testing Prior to Entry", 14, PatternTrend.stable),
            ("Casing Stabbing", "Mehsana Workover Rig MW-19", "100% Fall Arrest Lanyard Hook", 7, PatternTrend.falling),
            ("Heavy Equipment Placement", "Barmer Pad B-07", "Crane Outrigger Soil Compaction", 11, PatternTrend.rising),
            ("Separator Piping Modification", "Jaisalmer Terminal", "Class 1 Div 1 Hot Work Enclosure", 6, PatternTrend.falling),
        ]
        for act, loc, bar, count, trend in PATTERNS:
            pp = PrecursorPattern(
                activity=act,
                location=loc,
                barrier_type=bar,
                occurrence_count=count,
                last_seen=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 15)),
                trend=trend,
            )
            session.add(pp)

        # Monthly Safety Indices for each site over last 6 months
        for site in created_sites:
            today = date.today()
            for m in range(6):
                period_date = (today.replace(day=1) - timedelta(days=m * 30)).replace(day=1)
                sif_density = round(random.uniform(0.12, 0.45), 2)
                recurrence = round(random.uniform(1.2, 3.8), 2)
                sii = round(max(0.0, 100.0 - (sif_density * 80.0 + recurrence * 5.0)), 1)

                si = SafetyIndex(
                    site_id=site.id,
                    period=period_date,
                    sif_density=sif_density,
                    barrier_recurrence_score=recurrence,
                    sii_score=sii,
                )
                session.add(si)

        await session.commit()
        print("  ✓ Precursor patterns and safety indices created.")

        # 7. Execute automated 90-day rolling pattern mining aggregation
        print("[+] Running automated 90-day pattern mining aggregation...")
        from app.services.pattern_mining import run_pattern_mining
        mined_patterns = await run_pattern_mining(session)
        print(f"  ✓ Mined & upserted {len(mined_patterns)} spatio-temporal precursor patterns.")

    print("=" * 80)
    print("✅ DATABASE SEEDING COMPLETE FOR SIF SENTINEL AI")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(seed_database())
