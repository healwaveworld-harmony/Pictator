import io
import requests
import streamlit as st
import json
import time
import re
from PIL import Image, ImageDraw, ImageFont
from huggingface_hub import InferenceClient

# --------------------------------------
# 🔧 PAGE CONFIG & API
# --------------------------------------
st.set_page_config(page_title="Pictator Pro – Brake Design Suite", page_icon="🏎️", layout="wide")

OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", "")
SERP_API_KEY = st.secrets.get("SERP_API_KEY", "")
HF_TOKEN = st.secrets.get("HF_TOKEN", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- CEO TRUSTED DOMAIN LIST (2026 Master List) ---
TRUSTED_DOMAINS = [
    "https://za.pinterest.com/search/pins/?q=seat%20covers", "brembo.com", "wilwood.com", "stoptech.com", "alcon.co.uk",
    "ferodo.com", "bosch.com", "zf.com", "trwaftermarket.com",
    "ap-racing.com", "mclaren.com", "pinterest.com",
    "amazon.in", "sa.made-in-china.com", "pinterest.com/search/pins/?q=seat%20covers", "pinterest.com", "carwale.com"
]

st.title("🛞 Pictator Pro – CNC Brake Design Engineering Suite")
st.caption("Strategic Parallel RCA | Disc Brake & Drum Brake Design | AI Concept + Market Intelligence")

# --------------------------------------
# 🔐 AUTHENTICATION
# --------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

with st.sidebar:
    st.title("🔐 Access Panel")
    if not st.session_state.authenticated:
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if user == "Harmony" and pwd == "Harmony/Pictator123":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Credentials")
    else:
        st.success("🟢 Logged in as Harmony")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

if not st.session_state.authenticated:
    st.warning("🔐 Please login to continue")
    st.stop()

# --------------------------------------
# ⚡ FLASHMIND ENGINE (OPENROUTER)
# --------------------------------------
ANALYSIS_MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "qwen/qwen3-coder:free",
    "mistralai/mistral-7b-instruct:free"
]

def generate_engineering_fallback_analysis(context_summary):
    """Structured technical & market analysis when external LLM endpoints are rate-limited."""
    return f"""**1. Design & Geometric Assessment**
- **Configuration:** {context_summary.get('summary_title', 'Automotive Component Concept')}
- **Material & Thermal Behavior:** {context_summary.get('material', 'Cast Iron')} provides high thermal mass, damping capacity, and wear stability under repeated cyclic braking/operating loads.
- **Surface & Manufacturing Finish:** {context_summary.get('finish', 'Machined')} finish supports tight runout tolerances, uniform friction/mating contact, and corrosion protection on non-swept surfaces.

**2. Dimensional & Packaging Review**
- **Specified Parameters:** {context_summary.get('dimensions_note', 'Standard OEM packaging envelope')}
- **Machining & Tolerance Notes:** Ensure concentricity between center hub bore, pitch circle diameter (PCD), and outer friction/mating faces; maintain fillet radii at hat-to-disc transitions to mitigate thermal stress concentration.

**3. 2026 Industry & Market Alignment**
- **OEM+ & Aftermarket Direction:** Increasing adoption of precision CNC-machined faces, weight-optimized hat sections, and directional thermal dissipation geometries for improved fade resistance and NVH control.
- **Validation Recommendation:** Verify wheel spoke/caliper radial clearance, minimum discard thickness, and dynamic balancing prior to CNC toolpath release."""

def call_openrouter(prompt, context_summary=None):
    if OPENROUTER_API_KEY:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pictator-pro.streamlit.app",
            "X-Title": "Pictator Pro Engineering Suite"
        }
        for model in ANALYSIS_MODELS:
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a senior automotive design and CNC manufacturing engineer. "
                                    "Provide a concise, structured technical and 2026 market trend analysis "
                                    "covering geometry, thermal management, material/finish, and manufacturability."
                                )
                            },
                            {"role": "user", "content": prompt}
                        ]
                    },
                    timeout=20
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"].strip()
                    if content:
                        return content
            except Exception:
                continue

    return generate_engineering_fallback_analysis(context_summary or {})

# --------------------------------------
# 📐 TECHNICAL DIMENSION OVERLAY ENGINE
# --------------------------------------
def extract_dimension_callouts(text_blob):
    """Extracts explicit engineering dimensions (Ø, R, mm, PCD, angles, thickness) from user prompts."""
    if not text_blob:
        return []

    callouts = []
    seen = set()

    # Match lines or phrases containing engineering dimensions
    patterns = [
        r"(?:Outer\s+Rotor\s+Radius|Outer\s+Diameter|Center\s+Hub\s+Bore\s+Radius|Hat\s+Outer\s+Radius|Inner\s+Friction\s+Track\s+Radius|Total\s+Axial\s+Height|Wheel\s+Stud\s+Holes|Chamfer|Fillet)[^;\n]*",
        r"(?:Ø\s*\d+(?:\.\d+)?\s*mm(?:\s*PCD)?|R\s*\d+(?:\.\d+)?\s*mm|\d+(?:\.\d+)?\s*mm\s*(?:disc\s*thickness|top\s*face\s*thickness|thickness|height|radius|diameter|×\s*\d+°))",
    ]

    for line in text_blob.splitlines():
        clean_line = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
        if not clean_line:
            continue
        if re.search(r"(Ø\s*\d+|R\s*\d+|\d+(?:\.\d+)?\s*mm|PCD|\d+\s*°)", clean_line, re.IGNORECASE):
            # Keep concise callout labels
            short_label = clean_line.split(":")[0] + (": " + clean_line.split(":", 1)[1].strip() if ":" in clean_line else "")
            if len(short_label) > 68:
                matches = re.findall(r"(Ø\s*\d+(?:\.\d+)?\s*mm(?:\s*PCD)?|R\s*\d+(?:\.\d+)?\s*mm|\d+(?:\.\d+)?\s*mm(?:\s*×\s*\d+°)?)", clean_line)
                if matches:
                    prefix = clean_line.split(":")[0][:26] if ":" in clean_line else "DIM"
                    short_label = f"{prefix}: {' / '.join(dict.fromkeys(matches))}"
                else:
                    short_label = short_label[:65] + "..."
            if short_label.lower() not in seen:
                seen.add(short_label.lower())
                callouts.append(short_label)

    if not callouts:
        raw_matches = re.findall(r"(Ø\s*\d+(?:\.\d+)?\s*mm|R\s*\d+(?:\.\d+)?\s*mm|\d+(?:\.\d+)?\s*mm)", text_blob)
        for m in dict.fromkeys(raw_matches):
            callouts.append(f"SPEC: {m}")

    return callouts[:8]


def apply_dimension_annotations(pil_img, prompt_text, part_label="COMPONENT"):
    """Draws crisp CAD-style dimension callouts, centerlines, and leader lines onto 2D/3D renders."""
    img = pil_img.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", max(14, w // 64))
        font_dim = ImageFont.truetype("DejaVuSans-Bold.ttf", max(13, w // 72))
        font_small = ImageFont.truetype("DejaVuSans.ttf", max(11, w // 85))
    except Exception:
        font_title = ImageFont.load_default()
        font_dim = ImageFont.load_default()
        font_small = ImageFont.load_default()

    callouts = extract_dimension_callouts(prompt_text)

    # Extract key Ø / R values if present for direct radial/diameter leader lines
    dia_matches = re.findall(r"(Ø\s*\d+(?:\.\d+)?\s*mm)", prompt_text)
    rad_matches = re.findall(r"(R\s*\d+(?:\.\d+)?\s*mm)", prompt_text)
    thick_matches = re.findall(r"(\d+(?:\.\d+)?\s*mm\s*(?:disc\s*thickness|thickness|height))", prompt_text, re.IGNORECASE)

    line_color = (0, 210, 255, 235)      # Technical Cyan
    accent_color = (255, 195, 0, 240)    # Engineering Amber
    box_bg = (12, 18, 28, 210)           # Dark CAD HUD panel
    box_border = (0, 210, 255, 220)
    text_white = (245, 248, 255, 255)

    cx, cy = int(w * 0.50), int(h * 0.50)

    # 1. Subtle CAD Crosshair Centerlines
    dash_len = 14
    for x in range(int(w * 0.18), int(w * 0.82), dash_len * 2):
        draw.line([(x, cy), (min(x + dash_len, int(w * 0.82)), cy)], fill=(0, 210, 255, 110), width=1)
    for y in range(int(h * 0.14), int(h * 0.86), dash_len * 2):
        draw.line([(cx, y), (cx, min(y + dash_len, int(h * 0.86)))], fill=(0, 210, 255, 110), width=1)

    # 2. Top-Left Engineering Header Tag
    header_text = f"CAD / DIMENSIONAL VIEW — {part_label.upper()} (UNITS: mm)"
    hb = draw.textbbox((0, 0), header_text, font=font_title)
    draw.rectangle([16, 14, 32 + (hb[2] - hb[0]), 26 + (hb[3] - hb[1])], fill=box_bg, outline=box_border, width=2)
    draw.text((24, 20), header_text, fill=accent_color, font=font_title)

    # 3. Direct Leader-Line Callouts pointing onto the 2D/3D part geometry
    anchor_specs = []
    if dia_matches:
        anchor_specs.append((f"OUTER: {dia_matches[0]}", (int(w * 0.68), int(h * 0.24)), (int(w * 0.76), int(h * 0.13))))
    if len(dia_matches) > 1:
        anchor_specs.append((f"HAT / PCD: {dia_matches[1]}", (int(w * 0.58), int(h * 0.36)), (int(w * 0.76), int(h * 0.26))))
    if len(dia_matches) > 2:
        anchor_specs.append((f"BORE: {dia_matches[-1]}", (int(w * 0.50), int(h * 0.48)), (int(w * 0.76), int(h * 0.39))))
    if rad_matches:
        anchor_specs.append((f"FILLET / RAD: {rad_matches[0]}", (int(w * 0.42), int(h * 0.38)), (int(w * 0.04), int(h * 0.22))))
    if thick_matches:
        anchor_specs.append((f"SECTION: {thick_matches[0].upper()}", (int(w * 0.31), int(h * 0.56)), (int(w * 0.04), int(h * 0.35))))

    for label, pt_target, pt_label in anchor_specs:
        tx, ty = pt_target
        lx, ly = pt_label
        elbow_x = lx + 140 if lx < cx else lx - 15
        # Target dot + leader line
        draw.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=accent_color, outline=(0, 0, 0, 255))
        draw.line([(tx, ty), (elbow_x, ly + 12), (lx, ly + 12)], fill=line_color, width=2)
        tb = draw.textbbox((0, 0), label, font=font_dim)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        draw.rectangle([lx - 6, ly - 4, lx + tw + 10, ly + th + 8], fill=box_bg, outline=line_color, width=2)
        draw.text((lx + 2, ly + 1), label, fill=text_white, font=font_dim)

    # 4. Bottom-Left Full Dimension Specification Table (if dimensions were provided)
    if callouts:
        line_h = max(18, h // 42)
        panel_w = min(int(w * 0.56), 540)
        panel_h = 34 + len(callouts) * line_h
        x0, y0 = 16, h - panel_h - 16
        draw.rectangle([x0, y0, x0 + panel_w, y0 + panel_h], fill=box_bg, outline=box_border, width=2)
        draw.text((x0 + 10, y0 + 7), "SPECIFIED DIMENSIONS & TOLERANCE NOTES (mm)", fill=accent_color, font=font_small)
        draw.line([(x0 + 8, y0 + 24), (x0 + panel_w - 8, y0 + 24)], fill=box_border, width=1)
        for idx, item in enumerate(callouts):
            draw.text((x0 + 10, y0 + 28 + idx * line_h), f"• {item}", fill=text_white, font=font_small)

    combined = Image.alpha_composite(img, overlay).convert("RGB")
    return combined

# --------------------------------------
# 🛠️ IMAGE & MARKET ENGINES
# --------------------------------------
def generate_ai_image(prompt, model_config):
    """GENERATE: Pure AI Design Concept"""
    try:
        if isinstance(model_config, str):
            model_id = model_config
            provider = "huggingface"
        else:
            model_id = model_config.get("id")
            provider = model_config.get("provider", "huggingface")

        if provider == "google-imagen":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:predict?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1}
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                import base64
                data = response.json()
                img_b64 = data["predictions"][0]["bytesBase64Encoded"]
                img_bytes = base64.b64decode(img_b64)
                return Image.open(io.BytesIO(img_bytes))
            else:
                st.error(f"Gemini Generation Failed: HTTP {response.status_code}")
                return None
        else:
            client = InferenceClient(model=model_id, token=HF_TOKEN)
            return client.text_to_image(prompt, width=1024, height=768)
    except Exception as e:
        st.error(f"Generation Failed: {e}")
        return None

# ==========================================
# 🌐 PATCH 1: DATA ACQUISITION ENGINE
# ==========================================
def fetch_market_references(query):
    try:
        # 1. Broaden Pinterest query to ensure it always returns high-quality aesthetic anchors
        pin_params = {
            "engine": "google_images",
            "q": "automotive disc brake caliper rotor drum brake design site:pinterest.com",
            "api_key": SERP_API_KEY,
            "num": 20
        }
        try:
            pin_r = requests.get("https://serpapi.com/search", params=pin_params, timeout=10)
            pin_results = pin_r.json().get("images_results", [])
        except:
            pin_results = []
        
        # 2. Main vehicle market query
        params = {
            "engine": "google_images", 
            "q": f"{query} automotive disc brake rotor caliper drum brake", 
            "api_key": SERP_API_KEY, 
            "num": 40
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=10)
        results = r.json().get("images_results", [])
        
        pinterest_refs = []
        trusted_refs = []
        used_images = set()

        # Extract 3 unique Pinterest design inspirations
        for i in pin_results:
            img_url = i.get("original")
            if img_url and img_url not in used_images:
                if len(pinterest_refs) < 3:
                    pinterest_refs.append({
                        "img": img_url, 
                        "link": i.get("link", "https://za.pinterest.com/search/pins/?q=seat%20covers"), 
                        "src": "Pinterest"
                    })
                    used_images.add(img_url)

        # Process general trusted domains for the factory specifications row
        for i in results:
            source_name = i.get("source", "").strip()
            link = i.get("link", "").lower()
            img_url = i.get("original")
            
            if not img_url or img_url in used_images:
                continue
                
            is_pinterest = "pinterest" in link or "pinterest" in source_name.lower()
            
            if is_pinterest:
                if len(pinterest_refs) < 3:
                    pinterest_refs.append({
                        "img": img_url, 
                        "link": i["link"], 
                        "src": "Pinterest"
                    })
                    used_images.add(img_url)
            else:
                is_trusted = any(td in link for td in TRUSTED_DOMAINS)
                if is_trusted and len(trusted_refs) < 3:
                    trusted_refs.append({
                        "img": img_url, 
                        "link": i["link"], 
                        "src": source_name
                    })
                    used_images.add(img_url)
            
            if len(pinterest_refs) >= 3 and len(trusted_refs) >= 3:
                break
        
        # Absolute fallback fill if thresholds are still missing entries
        if len(pinterest_refs) < 3 or len(trusted_refs) < 3:
            for i in results:
                img_url = i.get("original")
                source_name = i.get("source", "").strip()
                link = i.get("link", "").lower()
                
                if not img_url or img_url in used_images:
                    continue
                    
                is_pinterest = "pinterest" in link or "pinterest" in source_name.lower()
                if is_pinterest and len(pinterest_refs) < 3:
                    pinterest_refs.append({
                        "img": img_url,
                        "link": i["link"],
                        "src": "Pinterest"
                    })
                    used_images.add(img_url)
                elif not is_pinterest and len(trusted_refs) < 3:
                    trusted_refs.append({
                        "img": img_url,
                        "link": i["link"],
                        "src": source_name
                    })
                    used_images.add(img_url)
                    
                if len(pinterest_refs) >= 3 and len(trusted_refs) >= 3: 
                    break
                
        return pinterest_refs + trusted_refs
    except Exception as e:
        st.sidebar.error(f"Search Fallback Engaged: {e}")
        return []

                           
# --------------------------------------
# 🎯 UI: SMART BRAKE DESIGN CONFIGURATOR
# --------------------------------------
MODEL_OPTIONS = {
    "⚡ FLUX.1 Schnell": {"id": "black-forest-labs/FLUX.1-schnell", "provider": "huggingface"},
    "🔥 FLUX.1 Dev": {"id": "black-forest-labs/FLUX.1-dev", "provider": "huggingface"},
}
selected_model = st.sidebar.selectbox("Choose AI Model", list(MODEL_OPTIONS.keys()))
show_dimension_overlay = st.sidebar.checkbox("📐 Mark Dimensions on Generated Image (2D/3D)", value=True)

# ==========================================
# 🧩 PART SELECTION
# Brake controls remain unchanged; non-brake
# components use dedicated prompt-based controls.
# ==========================================
PART_OPTIONS = [
    "Brake Components",
    "Cylinder Block",
    "Cylinder Head",
    "Crank Case",
    "Other Automotive Component",
    "Custom Component",
]
selected_part_category = st.sidebar.selectbox(
    "🧩 Part Selection",
    PART_OPTIONS,
    index=0,
)

if selected_part_category == "Brake Components":
    selected_part_focus = "Brake"
else:
    selected_part_focus = st.sidebar.text_input(
        "Component / Part Name",
        value="" if selected_part_category != "Other Automotive Component" else "",
        placeholder="e.g. gearbox housing, transmission case, suspension housing",
    )

if selected_part_category == "Brake Components":

        a, b, c = st.columns(3)
        with a:
            vehicle = st.selectbox("Vehicle", ["Maruti Wagon R", "Maruti Grand Vitara", "Custom Vehicle"])
            brake_type = st.selectbox("Brake Type", [
                "Disc Brake", "Drum Brake", "Front Disc + Rear Drum",
                "Front & Rear Disc", "Custom / Prompt Based"
            ])
            axle = st.selectbox("Axle", ["Front", "Rear", "Front & Rear", "Custom"])
        with b:
            rotor = st.selectbox("Rotor / Drum Design", [
                "Solid Rotor", "Vented Rotor", "Cross-Drilled Rotor",
                "Slotted Rotor", "Drilled + Slotted Rotor",
                "OEM Drum", "Performance Drum", "Custom / Prompt Based"
            ])
            caliper = st.selectbox("Caliper / Hardware", [
                "OEM Single-Piston", "Floating Caliper", "Fixed Multi-Piston",
                "Performance 4-Piston", "Performance 6-Piston",
                "Drum Shoe Assembly", "Custom / Prompt Based"
            ])
            material = st.selectbox("Material", [
                "Cast Iron", "High-Carbon Cast Iron", "Forged Aluminium",
                "Steel", "Aluminium + Steel", "Composite / Custom"
            ])
        with c:
            finish = st.selectbox("Finish", [
                "OEM Satin", "Brushed Metal", "Machined", "Gloss",
                "Matte", "Anodized", "Powder Coated", "Custom"
            ])
            lighting = st.selectbox("Photography / Visualization", [
                "Studio Product Photography", "Blueprint / CAD Presentation",
                "Cinematic Showroom", "Wheel-On Vehicle Photography",
                "Exploded Engineering View", "Custom"
            ])

        design_prompt = st.text_area(
            "✍️ Design Prompt / Idea",
            placeholder="Describe the brake design you want: rotor geometry, caliper style, color, finish, wheel visibility, cooling concept, branding, etc.",
            height=130
        )
        custom_instruction = st.text_area(
            "Additional Engineering Instructions",
            placeholder="Add dimensions, ventilation direction, slot pattern, mounting concept, thermal features, wheel clearance, or visual requirements.",
            height=100
        )

# ==========================================
# 🛠️ PART-SPECIFIC DESIGN CONTROLS
# ==========================================
if selected_part_category == "Brake Components":
    st.markdown("### 🛠️ Brake Design Enhancements")
    p1, p2 = st.columns(2)
    with p1:
        component_focus = st.selectbox("Design Focus", [
            "Full Brake Assembly",
            "Brake Disc / Rotor Only",
            "Brake Drum Only",
            "Steering Knuckle Only",
            "Brake Plate / Pressure Plate Only",
            "Rotor + Caliper",
            "Drum + Backing Plate",
            "Custom-Prompt Based"
        ])
        details = st.multiselect("Component Details", [
            "Ventilation Channels",
            "Cross-Drilled Holes",
            "Directional Slots",
            "Curved Vanes",
            "Floating Two-Piece Rotor",
            "Machined Hat",
            "Cooling Fins",
            "Brake Shoe Detail",
            "Backing Plate Detail",
            "Pressure Plate Detail",
            "Casting / Machining Detail",
            "Custom-Prompt Based"
        ], default=["Ventilation Channels"])
    with p2:
        features = st.multiselect("Engineering / Visual Features", [
            "Lightweight Design", "High Thermal Capacity", "Performance Appearance",
            "OEM+ Appearance", "Low-Dust Visual Concept",
            "Corrosion-Resistant Finish", "Wheel Clearance Focus",
            "Premium Machined Details", "Custom-Prompt Based"
        ], default=["OEM+ Appearance"])

else:
    st.markdown(f"### 🧩 {selected_part_category} Design")
    np1, np2 = st.columns(2)
    with np1:
        non_brake_prompt = st.text_area(
            "✍️ Component Design Prompt / Idea",
            placeholder=(
                "Describe exactly what should be designed: geometry, casting features, "
                "mounting points, ribs, bosses, cavities, interfaces, dimensions, "
                "manufacturing intent, or application."
            ),
            height=150,
        )
        non_brake_engineering = st.text_area(
            "⚙️ Engineering / Manufacturing Instructions",
            placeholder=(
                "Add material, wall thickness concept, draft angles, machining zones, "
                "thermal requirements, mounting interfaces, tolerances, or other requirements."
            ),
            height=120,
        )
    with np2:
        non_brake_material = st.selectbox(
            "Material",
            [
                "Cast Iron",
                "Aluminium Alloy",
                "Steel",
                "Ductile Iron",
                "High-Strength Aluminium",
                "Custom / Prompt Based",
            ],
        )
        non_brake_finish = st.selectbox(
            "Surface / Presentation",
            [
                "As-Cast",
                "Machined",
                "Shot-Blasted",
                "Brushed Metal",
                "OEM Industrial",
                "Technical CAD",
                "Custom / Prompt Based",
            ],
        )
        non_brake_visualization = st.selectbox(
            "Visualization",
            [
                "Studio Product Photography",
                "Blueprint / CAD Presentation",
                "Exploded Engineering View",
                "Industrial Manufacturing View",
                "Cinematic Product Visualization",
                "Custom",
            ],
        )
    non_brake_scope = st.text_area(
        "🎯 Strict Product Scope",
        placeholder=(
            "State what must appear in the image and what must not appear. "
            "Example: show only the cylinder block casting; no brake parts, wheels, "
            "seat covers, upholstery, or unrelated accessories."
        ),
        height=90,
    )

st.divider()

# ==========================================
# 🖼️ GENERATION SETTINGS
# ==========================================
st.markdown("### 🖼️ Concept Generation Matrix")
num_images = st.select_slider("Number of Concept Variations to Generate", options=[1, 3, 5], value=1)

# --------------------------------------
# 🎯 STRICT IMAGE SUBJECT CONTROL
# --------------------------------------
st.info(
    "Image generation follows the selected Part Selection. "
    "Brake components retain the existing brake controls; non-brake components "
    "use dedicated prompt-based controls and are not converted into brake designs."
)

# --------------------------------------
# 🚀 EXECUTION PIPELINE
# --------------------------------------
if st.button("🚀 EXECUTE DESIGN SUITE"):
    if selected_part_category == "Brake Components":
        combined_dim_source = f"{design_prompt}\n{custom_instruction}"
        dim_callouts_list = extract_dimension_callouts(combined_dim_source)
        dim_prompt_clause = (
            "Include clear engineering CAD dimension lines, diameter callouts, and technical annotation styling matching: "
            + "; ".join(dim_callouts_list)
            if dim_callouts_list else ""
        )

        brake_prompt = f"""
Create a professional automotive engineering design concept for {vehicle}.

PRIMARY COMPONENT — STRICT:
The image must primarily and clearly show ONLY the selected Design Focus:
{component_focus}.

Brake architecture: {brake_type}.
Axle: {axle}.
Rotor / drum specification: {rotor}.
Caliper / hardware specification: {caliper}.
Material: {material}.
Finish: {finish}.
Component details: {", ".join(details) if details else "standard"}.
Engineering / visual features: {", ".join(features) if features else "standard"}.
User design idea: {design_prompt or "Develop a premium OEM+ concept."}
Additional engineering instructions: {custom_instruction or "Maintain physically plausible automotive packaging."}
{dim_prompt_clause}
Visualization: {lighting}.

PRODUCT SCOPE:
The selected brake component is the hero subject. Do not introduce seat covers,
upholstery, interior trim, piping, threading, stitching, steering-wheel covers,
or unrelated vehicle accessories.

If the selected focus is Brake Disc / Rotor Only, show the brake disc/rotor as the
hero product. If Brake Drum Only, show the brake drum as the hero product.
If Steering Knuckle Only, show the steering knuckle as the hero product.
If Brake Plate / Pressure Plate Only, show that plate component as the hero product.

SUPPORTED BRAKE PRODUCTS:
- Brake Discs: high-performance ventilated and solid brake rotors.
- Brake Drums: heavy-duty rear brake components.
- Steering Knuckles: precision-engineered suspension parts.
- Brake Plates & Pressure Plates: thermal-stable cast-iron plate components.

VISUAL QUALITY:
Show realistic automotive manufacturing details, credible geometry, mounting
relationships, wheel clearance where relevant, ventilation/cooling features where
applicable, machined/cast surfaces, and professional product visualization.
Center the component cleanly in frame with clear margins for dimensional callouts.
This is a concept visualization and not a certified safety-critical engineering drawing.
"""
        market_query = f"{vehicle} {brake_type} {rotor} {caliper}"
        analysis_prompt = (
            f"Analyze the engineering design and 2026 market trends for {vehicle} ({axle} {brake_type}, "
            f"{rotor}, {caliper}, {material}, {finish}, focus: {component_focus}). "
            f"Incorporate these user design & dimensional specifications: {design_prompt} {custom_instruction}. "
            f"Cover geometry, thermal management, CNC manufacturability, and OEM+ design."
        )
        analysis_context = {
            "summary_title": f"{vehicle} — {axle} {brake_type} ({rotor}, {component_focus})",
            "material": material,
            "finish": finish,
            "dimensions_note": "; ".join(dim_callouts_list) if dim_callouts_list else "Standard OEM rotor/hub envelope"
        }
        caption_prefix = "Brake Design Concept"
        part_overlay_label = f"{vehicle} {component_focus}"

    else:
        selected_component = selected_part_focus.strip() or selected_part_category
        non_brake_prompt = locals().get("non_brake_prompt", "")
        non_brake_engineering = locals().get("non_brake_engineering", "")
        non_brake_material = locals().get("non_brake_material", "Custom / Prompt Based")
        non_brake_finish = locals().get("non_brake_finish", "Custom / Prompt Based")
        non_brake_visualization = locals().get("non_brake_visualization", "Technical CAD")
        non_brake_scope = locals().get("non_brake_scope", "")
        combined_dim_source = f"{non_brake_prompt}\n{non_brake_engineering}"
        dim_callouts_list = extract_dimension_callouts(combined_dim_source)

        brake_prompt = f"""
Create a professional industrial/automotive engineering design concept.

PRIMARY COMPONENT — ABSOLUTE:
The image must primarily and clearly show ONLY:
{selected_component}.

PART CATEGORY:
{selected_part_category}.

USER DESIGN PROMPT:
{non_brake_prompt or "Develop a realistic, manufacturable professional concept for the selected component."}

ENGINEERING / MANUFACTURING INSTRUCTIONS:
{non_brake_engineering or "Maintain physically plausible geometry and manufacturing logic."}

MATERIAL:
{non_brake_material}.

SURFACE / PRESENTATION:
{non_brake_finish}.

VISUALIZATION:
{non_brake_visualization}.

STRICT PRODUCT SCOPE:
{non_brake_scope or "Show only the selected component and only the interfaces/details required to explain it."}

IMPORTANT:
Do NOT convert this request into a brake design.
Do NOT add brake discs, brake drums, calipers, brake shoes, backing plates,
rotors, wheels, seat covers, upholstery, piping, threading, stitching,
steering-wheel covers, or unrelated accessories unless the user explicitly
requests one of them in the prompt.

SUPPORTED NON-BRAKE PRODUCT EXAMPLES:
- Cylinder Blocks: cast-condition engine blocks.
- Cylinder Heads: precision-cast components for machinery and engines.
- Crank Cases: castings primarily applied in compressors for the consumer durable sector.

If another automotive component is explicitly named by the user, generate that
component instead of substituting a brake component.

VISUAL QUALITY:
Use credible cast or machined surfaces, ribs, bosses, cavities, mounting points,
interfaces, draft/machining logic, realistic proportions, and professional
industrial product visualization. Avoid invented branding and impossible geometry.
Center the component cleanly in frame with clear margins for dimensional callouts.
This is a concept visualization and not a certified engineering drawing.
"""
        market_query = f"{selected_component} {selected_part_category} automotive component manufacturing"
        analysis_prompt = (
            f"Analyze the engineering design and 2026 manufacturing trends for {selected_component} "
            f"({selected_part_category}, {non_brake_material}, {non_brake_finish}). "
            f"Incorporate these specifications: {non_brake_prompt} {non_brake_engineering}. "
            f"Focus on material, casting/machining, thermal management, and OEM/industrial design."
        )
        analysis_context = {
            "summary_title": f"{selected_component} ({selected_part_category})",
            "material": non_brake_material,
            "finish": non_brake_finish,
            "dimensions_note": "; ".join(dim_callouts_list) if dim_callouts_list else "Custom component envelope"
        }
        caption_prefix = f"{selected_component} Design Concept"
        part_overlay_label = selected_component

    st.write(f"🎨 Generating {num_images} AI Design Concept(s)...")
    progress = st.progress(0)
    generated_images = []

    for i in range(num_images):
        iteration_prompt = brake_prompt + f"\nDesign variation: {i + 1}"
        img = generate_ai_image(
            iteration_prompt,
            MODEL_OPTIONS[selected_model]
        )

        if img:
            if show_dimension_overlay:
                img = apply_dimension_annotations(img, combined_dim_source, part_label=part_overlay_label)
            generated_images.append(img)
            st.image(
                img,
                caption=f"{caption_prefix} {i + 1}",
                use_container_width=True
            )

        progress.progress((i + 1) / num_images)

    st.write("🌐 Fetching Real-World Market References...")
    market_refs = fetch_market_references(market_query)

    st.write("📊 Analyzing Design & Market Trends...")
    analysis = call_openrouter(analysis_prompt, context_summary=analysis_context)

    if market_refs:
        st.markdown("### 🌐 Market References")
        for ref in market_refs:
            st.write(ref)

    if analysis:
        st.markdown("### 📊 Design & Market Analysis")
        st.write(analysis)

    if generated_images:
        st.success(
            f"Generated {len(generated_images)} "
            f"{caption_prefix.lower()}(s)."
        )
    else:
        st.warning(
            "No AI design image was generated. "
            "Check the selected AI model and credentials."
        )
