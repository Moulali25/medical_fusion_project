import os
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename

# Import local modules
from models import db, User, Fusion
from ml_fusion import MedicalImageFusion
from auth import auth as auth_blueprint

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')
UPLOAD_FOLDER_MRI = os.path.join(BASE_DIR, 'uploads', 'mri')
UPLOAD_FOLDER_PET = os.path.join(BASE_DIR, 'uploads', 'pet')
UPLOAD_FOLDER_TEMP = os.path.join(BASE_DIR, 'uploads', 'temp')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs', 'fused')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'best_fusion_model.keras')
DB_NAME = "database.db"

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['SECRET_KEY'] = 'medfuse_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, DB_NAME)}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '') # Load from environment

CORS(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Register Blueprints
app.register_blueprint(auth_blueprint, url_prefix='/api/auth')

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER_MRI, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_PET, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_TEMP, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Load ML Model
print("Initializing Fusion Service...")
fusion_service = None
try:
    fusion_service = MedicalImageFusion(
        MODEL_PATH, 
        gemini_api_key=app.config['GEMINI_API_KEY']
    )
except Exception as e:
    print(f"CRITICAL ERROR: Could not load model. Ensure {MODEL_PATH} exists.")

# --- ROUTES ---

@app.route('/')
def home():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_image():
    """Endpoint for pre-fusion analysis"""
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    img_type = request.form.get('type', 'GENERIC') # Get type (MRI/PET)
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    timestamp = int(time.time())
    filename = secure_filename(f"temp_{timestamp}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER_TEMP, filename)
    file.save(filepath)

    try:
        # Pass the type to the service
        report = fusion_service.generate_report(filepath, img_type=img_type)
        return jsonify({"message": "Analysis Complete", "report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/fuse', methods=['POST'])
@login_required
def fuse_images():
    if not fusion_service:
        return jsonify({"error": "Model not loaded"}), 500

    if 'mri_image' not in request.files or 'pet_image' not in request.files:
        return jsonify({"error": "Missing files"}), 400

    mri_file = request.files['mri_image']
    pet_file = request.files['pet_image']
    
    if mri_file.filename == '' or pet_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Secure filenames
    timestamp = int(time.time())
    mri_filename = secure_filename(f"{timestamp}_mri_{mri_file.filename}")
    pet_filename = secure_filename(f"{timestamp}_pet_{pet_file.filename}")
    
    mri_path = os.path.join(UPLOAD_FOLDER_MRI, mri_filename)
    pet_path = os.path.join(UPLOAD_FOLDER_PET, pet_filename)
    
    mri_file.save(mri_path)
    pet_file.save(pet_path)
    
    # Run pre-fusion strict validation to prevent fusing non-medical images
    if not fusion_service.is_valid_medical_image(mri_path, "MRI"):
        return jsonify({"error": "The uploaded MRI is NOT a valid medical scan. Fusion aborted."}), 400
        
    if not fusion_service.is_valid_medical_image(pet_path, "PET"):
        return jsonify({"error": "The uploaded PET is NOT a valid medical scan. Fusion aborted."}), 400

    # Fusion
    output_filename = f"fused_{timestamp}.png"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    try:
        # Fuse now returns path AND report
        _, report = fusion_service.fuse(mri_path, pet_path, output_path)
        
        # Save to DB
        new_fusion = Fusion(
            user_id=current_user.id,
            mri_path=mri_filename,
            pet_path=pet_filename,
            result_path=output_filename
        )
        db.session.add(new_fusion)
        db.session.commit()

        # Get Gemini Recommendation
        recommendation = fusion_service.get_gemini_recommendation(report)
        report['recommendation'] = recommendation

        # Get all three reports
        mri_report = fusion_service.generate_report(mri_path, img_type="MRI")
        pet_report = fusion_service.generate_report(pet_path, img_type="PET")

        # Save Report to Text File (Hospital Format)
        report_filename = output_filename.replace('.png', '.txt')
        report_path = os.path.join(OUTPUT_FOLDER, report_filename)

        def format_report_to_lines(rep, rec_text=None):
            sep = "=" * 60
            thin = "-" * 60
            lines = []
            lines.append(sep)
            lines.append(f"  {rep.get('hospital_name', 'MedFuse Imaging Centre').upper()}")
            lines.append(f"  {rep.get('hospital_address', '')}")
            lines.append(f"  {rep.get('department', 'Department of Radiology')}")
            lines.append(sep)
            lines.append("")
            lines.append(f"  {rep.get('title', 'MEDICAL IMAGING REPORT')}")
            lines.append("")
            lines.append(thin)
            lines.append(f"  Accession No.     : {rep.get('accession_no', 'N/A')}")
            lines.append(f"  Date of Exam      : {rep.get('date_of_examination', time.strftime('%d %B %Y'))}")
            lines.append(f"  Time of Exam      : {rep.get('time_of_examination', time.strftime('%H:%M'))}")
            lines.append(f"  Referring Physician: {rep.get('referring_physician', 'N/A')}")
            lines.append(f"  Reporting Radiologist: {rep.get('reporting_radiologist', 'N/A')}")
            lines.append(thin)
            lines.append("")
            lines.append("CLINICAL INDICATION:")
            lines.append(f"  {rep.get('clinical_indication', 'N/A')}")
            lines.append("")
            lines.append("EXAMINATION:")
            lines.append(f"  {rep.get('examination', 'N/A')}")
            lines.append("")
            lines.append("TECHNIQUE:")
            lines.append(f"  {rep.get('technique', 'N/A')}")
            lines.append("")
            lines.append("FINDINGS:")

            findings = rep.get('findings', {})
            if isinstance(findings, dict):
                label_map = {
                    'cortical_structures': 'Cortical Structures',
                    'white_matter': 'White Matter',
                    'ventricular_system': 'Ventricular System',
                    'basal_ganglia_thalami': 'Basal Ganglia & Thalami',
                    'brainstem_cerebellum': 'Brainstem & Cerebellum',
                    'extra_axial_spaces': 'Extra-Axial Spaces',
                    'vascular': 'Vascular Structures',
                    'post_contrast': 'Post-Contrast Enhancement',
                    'radiotracer_distribution': 'Radiotracer Distribution',
                    'frontal_lobes': 'Frontal Lobes',
                    'temporal_parietal': 'Temporal & Parietal Lobes',
                    'basal_ganglia': 'Basal Ganglia',
                    'cerebellum': 'Cerebellum',
                    'suv_measurement': 'SUV Measurement',
                    'artifacts': 'Artifacts',
                    'fusion_quality': 'Fusion Quality',
                    'anatomical_metabolic_correlation': 'Anatomical-Metabolic Correlation',
                    'focal_lesion_assessment': 'Focal Lesion Assessment',
                    'colormap_interpretation': 'Colormap Interpretation',
                    'general': 'General',
                }
                for key, value in findings.items():
                    label = label_map.get(key, key.replace('_', ' ').title())
                    if isinstance(value, list):
                        lines.append(f"\n  {label}:")
                        for item in value:
                            lines.append(f"    - {item}")
                    else:
                        lines.append(f"\n  {label}:\n    {value}")
            elif isinstance(findings, list):
                for f_item in findings:
                    lines.append(f"  - {f_item}")

            lines.append("")
            lines.append(thin)
            lines.append("IMPRESSION:")
            for imp_line in rep.get('impression', 'N/A').split('\n'):
                lines.append(f"  {imp_line}")
            lines.append("")
            lines.append("RECOMMENDATIONS:")
            lines.append(f"  {rep.get('recommendations', rec_text if rec_text else 'N/A')}")
            lines.append("")
            if rec_text:
                lines.append("AI RECOMMENDATION (Gemini):")
                lines.append(f"  {rec_text}")
                lines.append("")
            lines.append(thin)
            lines.append("LIMITATIONS / DISCLAIMER:")
            lines.append(f"  {rep.get('limitations', 'N/A')}")
            lines.append("")
            lines.append(sep)
            lines.append(f"  Digitally issued by MedFuse AI Reporting System")
            lines.append(f"  Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(sep)
            lines.append("\n\n")
            return lines

        all_lines = []
        all_lines.extend(format_report_to_lines(mri_report))
        all_lines.extend(format_report_to_lines(pet_report))
        all_lines.extend(format_report_to_lines(report, recommendation))

        report_text = "\n".join(all_lines)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        result_url = f"/outputs/fused/{output_filename}"
        report_url = f"/outputs/fused/{report_filename}"
        
        return jsonify({
            "message": "Fusion Successful!",
            "fused_image_url": result_url,
            "report_url": report_url,
            "fusion_id": new_fusion.id,
            "report": report
        })
    except Exception as e:
        print(f"Fusion Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    history = Fusion.query.filter_by(user_id=current_user.id).order_by(Fusion.timestamp.desc()).all()
    results = []
    for h in history:
        results.append({
            "id": h.id,
            "date": h.timestamp.strftime("%Y-%m-%d %H:%M"),
            "fused_url": f"/outputs/fused/{h.result_path}"
        })
    return jsonify(results)

# Serve output images
@app.route('/outputs/fused/<filename>')
def serve_fused_image(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized!")

if not os.path.exists(os.path.join(BASE_DIR, DB_NAME)):
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
