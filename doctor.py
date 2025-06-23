import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
from PIL import Image, ImageTk
from translate import Translator
import pyttsx3
import speech_recognition as sr
import re
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from datetime import datetime
import logging
import colorsys

# Set up logging
logging.basicConfig(filename='chatbot_errors.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DoctorChatbotApp:
    def __init__(self, root, username):
        self.root = root
        self.username = username
        # Set window to 80% of screen size
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        self.root.title(f"Online Doctor Chatbot - {username}")
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.configure(bg='#d8d8d8')

        # Initialize attributes
        self.language = 'en'
        self.tts_engine = pyttsx3.init()
        self.patient_data = {"age_group": "", "symptoms": [], "vitals": {}, "duration": "", "allergies": "", "history": "", "lifestyle": "", "severity": "mild"}
        self.diagnosis_state = "age_group"
        self.follow_up_questions = []
        self.prescription_history = []
        self.uploaded_image = None
        self.theme = "light"  # Add theme state

        # Initialize database
        self.init_database()

        # UI setup with tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Chat tab
        self.chat_frame = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(self.chat_frame, text="Chat")

        # Prescription history tab
        self.history_frame = tk.Frame(self.notebook, bg='#f0f0f0')
        self.notebook.add(self.history_frame, text="Prescription History")

        # Canvas and scrollbar for chat
        self.canvas = tk.Canvas(self.chat_frame, bg='#f0f0f0')
        self.scrollbar = tk.Scrollbar(self.chat_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#f0f0f0')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Top frame for toggle button (at the top-left corner)
        self.top_frame = tk.Frame(self.scrollable_frame, bg='#f0f0f0')
        self.top_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")

        # Toggle Theme button in the top-left corner
        self.theme_button = tk.Button(self.top_frame, text="Toggle Theme", command=self.toggle_theme, 
                                      bg='#000000', fg='white', font=('Arial', 10, 'bold'))
        self.theme_button.pack(side=tk.LEFT)

        # Heading (below the top frame)
        self.heading = tk.Label(self.scrollable_frame, text="ONLINE DOCTOR CHATBOT", 
                                bg='#f0f0f0', fg='black', font=('Arial', 16, 'bold'))
        self.heading.grid(row=1, column=0, columnspan=5, padx=10, pady=10)

        # Disclaimer
        self.disclaimer = tk.Label(self.scrollable_frame, text="Note: This is not a substitute for professional medical advice. Consult a doctor to confirm prescriptions.", 
                                   bg='#f0f0f0', fg='#FF0000', font=('Arial', 10, 'italic'))
        self.disclaimer.grid(row=2, column=0, columnspan=5, padx=10, pady=5)

        # Chat log
        self.chat_log = scrolledtext.ScrolledText(self.scrollable_frame, state='disabled', wrap=tk.WORD, 
                                                  bg='#ffffff', fg='#000000', height=15, font=('Arial', 12))
        self.chat_log.grid(row=3, column=0, columnspan=5, padx=10, pady=10, sticky="nsew")

        # Severity slider
        self.severity_label = tk.Label(self.scrollable_frame, text="Symptom Severity:", bg='#f0f0f0', font=('Arial', 10))
        self.severity_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.severity_scale = tk.Scale(self.scrollable_frame, from_=1, to=3, orient=tk.HORIZONTAL, 
                                       bg='#f0f0f0', font=('Arial', 10), 
                                       tickinterval=1, label="1:Mild 2:Moderate 3:Severe")
        self.severity_scale.set(1)
        self.severity_scale.grid(row=4, column=1, columnspan=4, padx=10, pady=5, sticky="ew")

        # Entry box and buttons (aligned in one line)
        self.input_frame = tk.Frame(self.scrollable_frame, bg='#f0f0f0')
        self.input_frame.grid(row=5, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

        self.entry_box = tk.Entry(self.input_frame, width=50, bg='#ffffff', fg='#000000', font=('Arial', 12))
        self.entry_box.pack(side=tk.LEFT, padx=(0, 5))
        self.entry_box.bind("<Return>", self.send_response)

        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_response, 
                                     bg='#28A745', fg='white', font=('Arial', 10, 'bold'))
        self.send_button.pack(side=tk.LEFT, padx=5)

        self.mic_button = tk.Button(self.input_frame, text="Speak", command=self.speech_to_text, 
                                    bg='#28A745', fg='white', font=('Arial', 10, 'bold'))
        self.mic_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = tk.Button(self.input_frame, text="Reset Chat", command=self.reset_chat, 
                                      bg='#FF0000', fg='white', font=('Arial', 10, 'bold'))
        self.reset_button.pack(side=tk.LEFT, padx=5)

        # Additional buttons frame (below entry box)
        self.additional_buttons_frame = tk.Frame(self.scrollable_frame, bg='#f0f0f0')
        self.additional_buttons_frame.grid(row=6, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

        # Language selection with search bar using Combobox
        self.languages = {
            'Arabic': 'ar',
            'Assamese': 'as',
            'Bengali': 'bn',
            'Bodo': 'brx',
            'Chinese (Simplified)': 'zh-cn',
            'Danish': 'da',
            'Dutch': 'nl',
            'English': 'en',
            'Finnish': 'fi',
            'French': 'fr',
            'German': 'de',
            'Greek': 'el',
            'Gujarati': 'gu',
            'Hebrew': 'he',
            'Hindi': 'hi',
            'Indonesian': 'id',
            'Italian': 'it',
            'Japanese': 'ja',
            'Kannada': 'kn',
            'Kashmiri': 'ks',
            'Konkani': 'kok',
            'Korean': 'ko',
            'Maithili': 'mai',
            'Malayalam': 'ml',
            'Manipuri/Meitei': 'mni',
            'Marathi': 'mr',
            'Nepali': 'ne',
            'Odia': 'or',
            'Polish': 'pl',
            'Portuguese': 'pt',
            'Punjabi': 'pa',
            'Russian': 'ru',
            'Sanskrit': 'sa',
            'Santali': 'sat',
            'Sindhi': 'sd',
            'Spanish': 'es',
            'Swahili': 'sw',
            'Swedish': 'sv',
            'Tamil': 'ta',
            'Telugu': 'te',
            'Thai': 'th',
            'Turkish': 'tr',
            'Urdu': 'ur',
            'Vietnamese': 'vi'
        }
        self.all_languages = sorted(self.languages.keys())  # Store the full sorted list for filtering
        self.language_combobox = ttk.Combobox(self.additional_buttons_frame, values=self.all_languages, state='readonly', font=('Arial', 10, 'bold'))
        self.language_combobox.set('Select Language')
        self.language_combobox.pack(side=tk.LEFT, padx=5)
        # Style the Combobox to match the previous OptionMenu
        self.language_combobox.configure(foreground='white')
        self.language_combobox.option_add('*TCombobox*Listbox*Background', '#007BFF')
        self.language_combobox.option_add('*TCombobox*Listbox*Foreground', 'white')
        self.language_combobox.option_add('*TCombobox*Listbox*Font', ('Arial', 10, 'bold'))
        # Bind events for search and selection
        self.language_combobox.bind('<KeyRelease>', self.filter_languages)
        self.language_combobox.bind('<<ComboboxSelected>>', self.on_language_select)

        self.upload_button = tk.Button(self.additional_buttons_frame, text="Upload Skin Image", command=self.upload_image, 
                                       bg='#007BFF', fg='white', font=('Arial', 10, 'bold'))
        self.upload_button.pack(side=tk.LEFT, padx=5)

        self.prescription_button = tk.Button(self.additional_buttons_frame, text="Generate Prescription", command=self.generate_prescription, 
                                             bg='#007BFF', fg='white', font=('Arial', 10, 'bold'))
        self.prescription_button.pack(side=tk.LEFT, padx=5)

        self.pdf_button = tk.Button(self.additional_buttons_frame, text="Export Latest to PDF", command=self.export_to_pdf, 
                                    bg='#007BFF', fg='white', font=('Arial', 10, 'bold'))
        self.pdf_button.pack(side=tk.LEFT, padx=5)

        # Prescription history log
        self.history_log = scrolledtext.ScrolledText(self.history_frame, wrap=tk.WORD, 
                                                    bg='#ffffff', fg='#000000', height=20, font=('Arial', 12))
        self.history_log.pack(padx=10, pady=10, fill="both", expand=True)

        # Buttons to export and delete selected prescription
        self.history_pdf_button = tk.Button(self.history_frame, text="Export Selected to PDF", 
                                            command=self.export_selected_to_pdf, 
                                            bg='#007BFF', fg='white', font=('Arial', 10, 'bold'))
        self.history_pdf_button.pack(padx=5, pady=5, side=tk.LEFT)

        self.delete_button = tk.Button(self.history_frame, text="Delete", 
                                       command=self.delete_selected_prescription, 
                                       bg='#FF0000', fg='white', font=('Arial', 10, 'bold'))
        self.delete_button.pack(padx=5, pady=5, side=tk.LEFT)

        # Diagnostic questions
        self.questions = {
            "age_group": "Is the patient a child (under 18) or an adult? Please respond with 'child' or 'adult'.",
            "vitals": "Please provide any known vital signs (e.g., temperature in °F, heart rate in bpm). Enter 'unknown' if not available.",
            "initial": "Please describe the patient's symptoms in detail.",
            "duration": "How long have the symptoms been present?",
            "allergies": "Does the patient have any known allergies or pre-existing conditions?",
            "history": "Has the patient experienced similar symptoms before?",
            "lifestyle": "Can you provide details about the patient's diet, exercise, or recent travel?",
            "follow_up": "Please answer the following symptom-specific question: ",
            "final": "Thank you for the information. I will generate a prescription based on the responses."
        }

        # Follow-up question templates (including skin conditions)
        self.follow_up_templates = {
            "fever": ["Is the fever accompanied by a rash?", "Do you have chills or night sweats?"],
            "cough": ["Is the cough dry or productive (with phlegm)?", "Is the cough worse at night?"],
            "headache": ["Is the headache accompanied by nausea or sensitivity to light?", "Does it feel like a throbbing pain?"],
            "diarrhea": ["Is there blood in the stool?", "Are you experiencing dehydration symptoms like dizziness?"],
            "rash": ["Is the rash itchy?", "Does it spread or change in appearance?"],
            "eczema": ["Is the skin dry or cracked?", "Is there oozing or crusting?"],
            "psoriasis": ["Are there thick, scaly patches?", "Is it painful or itchy?"],
            "acne": ["Is the acne inflamed or pustular?", "Does it appear on the face, back, or chest?"]
        }

        self.serious_symptoms = ["chest pain", "difficulty breathing", "severe abdominal pain", "unconsciousness", "severe bleeding", "severe skin infection"]

        # Load user profile
        self.load_user_profile()
        self.display_message("Doctor", self.translate_text(self.questions[self.diagnosis_state]))

    def init_database(self):
        try:
            self.conn = sqlite3.connect("medical_data.db")
            self.cursor = self.conn.cursor()

            # Drop existing conditions table to ensure fresh data
            self.cursor.execute("DROP TABLE IF EXISTS conditions")
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS conditions (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    symptom TEXT,
                    age_group TEXT,
                    severity TEXT,
                    treatment TEXT,
                    description TEXT,
                    severity_info TEXT,
                    causes TEXT,
                    prevention TEXT
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    username TEXT PRIMARY KEY,
                    age_group TEXT,
                    allergies TEXT,
                    history TEXT,
                    lifestyle TEXT
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS prescriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    prescription_text TEXT,
                    timestamp TEXT
                )
            ''')

            # Insert sample data (force insert every time)
            sample_data = [
                ("fever", "fever", "adult", "mild", "Acetaminophen 500mg every 6 hours as needed (max 3g daily).", 
                 "Fever is a temporary increase in body temperature above the normal range.", 
                 "Mild to Moderate", "Viral or bacterial infections", "Stay hydrated, rest"),
                ("fever", "fever", "adult", "moderate", "Ibuprofen 400mg every 6 hours as needed (max 3.2g daily).", 
                 "Fever is a temporary increase in body temperature above the normal range.", 
                 "Moderate to Severe", "Infections or inflammation", "Monitor temperature, seek doctor if persistent"),
                ("fever", "fever", "adult", "severe", "Seek medical attention if fever exceeds 103°F or persists beyond 3 days.", 
                 "Fever is a temporary increase in body temperature above the normal range.", 
                 "Severe", "Serious infections", "Immediate medical consultation"),
                ("fever", "fever", "child", "mild", "Acetaminophen 10-15mg/kg every 6 hours as needed (max 75mg/kg daily).", 
                 "Fever in children often indicates an immune response to infection.", 
                 "Mild", "Viral infections", "Ensure hydration, monitor temperature"),
                ("fever", "fever", "child", "moderate", "Acetaminophen 10-15mg/kg every 6 hours. Consult pediatrician if persistent.", 
                 "Fever in children often indicates an immune response to infection.", 
                 "Moderate", "Bacterial infections", "Consult pediatrician if persistent"),
                ("fever", "fever", "child", "severe", "Seek pediatrician immediately if fever exceeds 102°F or lasts over 24 hours.", 
                 "Fever in children often indicates an immune response to infection.", 
                 "Severe", "Serious infections", "Immediate pediatric consultation"),
                
                ("cough", "cough", "adult", "mild", "Dextromethorphan 10-20mg every 4 hours as needed.", 
                 "Cough is a reflex to clear the airways of irritants or mucus.", 
                 "Mild", "Cold or allergies", "Stay hydrated, avoid irritants"),
                ("cough", "cough", "child", "mild", "Honey (for ages 1+), 1-2 tsp at bedtime.", 
                 "Cough in children can be due to viral infections or irritants.", 
                 "Mild", "Viral infections", "Use a humidifier, avoid smoke"),
                
                ("headache", "headache", "adult", "mild", "Ibuprofen 200-400mg every 6 hours as needed (max 3.2g daily).", 
                 "Headache is pain in the head, often due to tension or dehydration.", 
                 "Mild to Moderate", "Stress or dehydration", "Stay hydrated, reduce stress"),
                ("headache", "headache", "child", "mild", "Acetaminophen 10-15mg/kg every 6 hours as needed.", 
                 "Headache in children may be due to fatigue or minor infections.", 
                 "Mild", "Fatigue or infections", "Ensure rest, monitor symptoms"),
                
                ("diarrhea", "diarrhea", "adult", "mild", "Loperamide 2mg after each loose stool (max 8mg daily).", 
                 "Diarrhea involves frequent loose or watery stools.", 
                 "Mild to Moderate", "Food poisoning or viral infection", "Stay hydrated, eat bland foods"),
                ("diarrhea", "diarrhea", "child", "mild", "Oral rehydration solution (e.g., Pedialyte), 50-100mL/kg over 4 hours.", 
                 "Diarrhea in children can lead to dehydration if not managed.", 
                 "Mild", "Viral infections", "Use oral rehydration, avoid sugary drinks"),
                
                ("rash", "rash", "adult", "mild", "Hydrocortisone cream 1% applied 2-3 times daily for 7 days.", 
                 "Rash is an area of irritated or swollen skin, often itchy.", 
                 "Mild", "Allergic reaction", "Avoid irritants, keep skin clean"),
                ("rash", "rash", "adult", "moderate", "Clotrimazole cream 1% applied twice daily for 2 weeks; consult doctor if no improvement.", 
                 "Rash is an area of irritated or swollen skin, often itchy.", 
                 "Moderate", "Fungal infection", "Keep area dry, consult doctor if persistent"),
                ("rash", "rash", "adult", "severe", "Prednisone 20mg daily for 5 days under medical supervision; seek dermatologist immediately.", 
                 "Rash is an area of irritated or swollen skin, often itchy.", 
                 "Severe", "Severe allergic reaction", "Seek medical attention"),
                ("rash", "rash", "child", "mild", "Hydrocortisone cream 0.5% applied once daily for 5 days; consult pediatrician.", 
                 "Rash in children can be due to allergies or infections.", 
                 "Mild", "Allergic reaction", "Use hypoallergenic products, consult pediatrician"),
                ("rash", "rash", "child", "moderate", "Hydrocortisone cream 0.5% applied twice daily for 7 days; consult pediatrician if persistent.", 
                 "Rash in children can be due to allergies or infections.", 
                 "Moderate", "Eczema flare-up", "Keep skin moisturized, avoid triggers"),
                ("rash", "rash", "child", "severe", "Seek pediatrician immediately if rash spreads or worsens.", 
                 "Rash in children can be due to allergies or infections.", 
                 "Severe", "Infection or severe allergy", "Immediate medical consultation"),
                
                ("eczema", "eczema", "adult", "mild", "Moisturize with Cetaphil twice daily; apply Hydrocortisone 1% as needed for 7 days.", 
                 "Eczema causes dry, itchy, and inflamed skin patches.", 
                 "Mild", "Dry skin or irritants", "Moisturize regularly, avoid harsh soaps"),
                ("eczema", "eczema", "adult", "moderate", "Apply Tacrolimus ointment 0.1% twice daily for 2 weeks; consult dermatologist if no relief.", 
                 "Eczema causes dry, itchy, and inflamed skin patches.", 
                 "Moderate", "Chronic irritation", "Use fragrance-free products, consult dermatologist"),
                ("eczema", "eczema", "adult", "severe", "Prednisone 20mg daily for 5 days under medical supervision; seek dermatologist immediately.", 
                 "Eczema causes dry, itchy, and inflamed skin patches.", 
                 "Severe", "Infection or severe flare-up", "Seek medical attention"),
                ("eczema", "eczema", "child", "mild", "Moisturize with fragrance-free lotion twice daily; apply Hydrocortisone 0.5% as needed for 5 days.", 
                 "Eczema in children often appears as itchy patches.", 
                 "Mild", "Dry skin or allergens", "Use gentle skincare, avoid triggers"),
                ("eczema", "eczema", "child", "moderate", "Moisturize with fragrance-free lotion; apply Tacrolimus ointment 0.03% twice daily for 7 days; consult pediatrician.", 
                 "Eczema in children often appears as itchy patches.", 
                 "Moderate", "Chronic irritation", "Keep skin hydrated, consult pediatrician"),
                ("eczema", "eczema", "child", "severe", "Apply wet wrap therapy with Hydrocortisone 0.5% twice daily for 3 days; seek pediatrician if infection occurs.", 
                 "Eczema in children often appears as itchy patches.", 
                 "Severe", "Infection or severe flare-up", "Immediate pediatric consultation"),
                
                ("psoriasis", "psoriasis", "adult", "mild", "Apply Coal tar ointment 2% nightly for 14 days; use moisturizer daily.", 
                 "Psoriasis causes thick, scaly patches on the skin.", 
                 "Mild", "Autoimmune response", "Moisturize, avoid stress"),
                ("psoriasis", "psoriasis", "adult", "moderate", "Apply Calcipotriene ointment 0.005% twice daily for 4 weeks; consult dermatologist.", 
                 "Psoriasis causes thick, scaly patches on the skin.", 
                 "Moderate", "Chronic condition", "Use prescribed treatments, consult dermatologist"),
                ("psoriasis", "psoriasis", "adult", "severe", "Methotrexate 7.5mg weekly under medical supervision; seek dermatologist immediately.", 
                 "Psoriasis causes thick, scaly patches on the skin.", 
                 "Severe", "Severe autoimmune flare-up", "Seek medical attention"),
                ("psoriasis", "psoriasis", "child", "mild", "Apply Coal tar ointment 1% nightly for 7 days; use fragrance-free moisturizer daily.", 
                 "Psoriasis in children presents as scaly patches.", 
                 "Mild", "Genetic predisposition", "Moisturize, avoid irritants"),
                ("psoriasis", "psoriasis", "child", "moderate", "Apply Calcipotriene ointment 0.005% once daily for 14 days; consult pediatric dermatologist.", 
                 "Psoriasis in children presents as scaly patches.", 
                 "Moderate", "Chronic condition", "Use gentle treatments, consult dermatologist"),
                ("psoriasis", "psoriasis", "child", "severe", "Seek pediatric dermatologist immediately; consider phototherapy under supervision.", 
                 "Psoriasis in children presents as scaly patches.", 
                 "Severe", "Severe flare-up", "Immediate medical consultation"),
                
                ("acne", "acne", "adult", "mild", "Use Benzoyl Peroxide 2.5% gel once daily for 2 weeks.", 
                 "Acne is a common skin condition where hair follicles become clogged with oil and dead skin cells.", 
                 "Mild to Severe", "Hormonal changes, bacteria", "Cleanse face regularly"),
                ("acne", "acne", "adult", "moderate", "Use Benzoyl Peroxide 5% gel twice daily for 4 weeks; consult dermatologist if no improvement.", 
                 "Acne is a common skin condition where hair follicles become clogged with oil and dead skin cells.", 
                 "Moderate", "Excess oil production", "Avoid oily products, consult dermatologist"),
                ("acne", "acne", "adult", "severe", "Isotretinoin 0.5mg/kg daily for 4-6 months under medical supervision; seek dermatologist immediately.", 
                 "Acne is a common skin condition where hair follicles become clogged with oil and dead skin cells.", 
                 "Severe", "Cystic acne", "Seek medical attention"),
                ("acne", "acne", "child", "mild", "Use Salicylic Acid 0.5% wash once daily; consult pediatrician.", 
                 "Acne in children can occur due to early hormonal changes.", 
                 "Mild", "Hormonal changes", "Use gentle cleansers, consult pediatrician"),
                ("acne", "acne", "child", "moderate", "Use Salicylic Acid 1% wash twice daily for 2 weeks; consult pediatrician if persistent.", 
                 "Acne in children can occur due to early hormonal changes.", 
                 "Moderate", "Bacterial infection", "Keep skin clean, consult pediatrician"),
                ("acne", "acne", "child", "severe", "Seek pediatric dermatologist immediately; consider low-dose isotretinoin under supervision.", 
                 "Acne in children can occur due to early hormonal changes.", 
                 "Severe", "Severe cystic acne", "Immediate medical consultation"),
                
                # Adding Fever & Cough entries
                ("fever", "fever and cough", "adult", "mild", "Acetaminophen 500mg every 6 hours as needed (max 3g daily).", 
                 "Fever is a temporary increase in body temperature above the normal range.", 
                 "Mild to Moderate", "Viral or bacterial infections", "Stay hydrated, rest"),
                
                ("cough", "fever and cough", "adult", "mild", "Dextromethorphan 10-20mg every 4 hours as needed.", 
                 "Cough is a reflex to clear the airways of irritants or mucus.", 
                 "Mild", "Cold or allergies", "Stay hydrated, avoid irritants"),
                
                ("fever", "fever and cough", "adult", "moderate", "Ibuprofen 400mg every 6 hours as needed (max 3.2g daily).", 
                 "Fever is a temporary increase in body temperature above the normal range.", 
                 "Moderate to Severe", "Infections or inflammation", "Monitor temperature, seek doctor if persistent"),
                
                ("cough", "fever and cough", "adult", "moderate", "Dextromethorphan 10-20mg every 4 hours as needed.", 
                 "Cough is a reflex to clear the airways of irritants or mucus.", 
                 "Mild", "Cold or allergies", "Stay hydrated, avoid irritants"),
                
                ("fever", "fever and cough", "child", "severe", "Seek pediatrician immediately if fever exceeds 102°F or lasts over 24 hours.", 
                 "Fever in children often indicates an immune response to infection.", 
                 "Severe", "Serious infections", "Immediate pediatric consultation"),
                
                ("cough", "fever and cough", "child", "severe", "Honey (for ages 1+), 1-2 tsp at bedtime.", 
                 "Cough in children can be due to viral infections or irritants.", 
                 "Mild", "Viral infections", "Use a humidifier, avoid smoke"),
                
                # Adding Headache & Fever entries
                ("headache", "headache and fever", "adult", "mild", "Ibuprofen 200-400mg every 6 hours as needed (max 3.2g daily).", 
                 "Headache is pain in the head, often due to tension or dehydration.", 
                 "Mild to Moderate", "Stress or dehydration", "Stay hydrated, reduce stress"),
                
                ("fever", "headache and fever", "adult", "mild", "Acetaminophen 500mg every 6 hours as needed (max 3g daily).", 
                 "Fever is a temporary increase in body temperature above the normal range.", 
                 "Mild to Moderate", "Viral or bacterial infections", "Stay hydrated, rest"),
                
                ("headache", "headache and fever", "child", "moderate", "Acetaminophen 10-15mg/kg every 6 hours as needed.", 
                 "Headache in children may be due to fatigue or minor infections.", 
                 "Mild", "Fatigue or infections", "Ensure rest, monitor symptoms"),
                
                ("fever", "headache and fever", "child", "moderate", "Acetaminophen 10-15mg/kg every 6 hours. Consult pediatrician if persistent.", 
                 "Fever in children often indicates an immune response to infection.", 
                 "Moderate", "Bacterial infections", "Consult pediatrician if persistent"),
                
                # Adding Diarrhea & Cough entries
                ("diarrhea", "diarrhea and cough", "adult", "mild", "Loperamide 2mg after each loose stool (max 8mg daily).", 
                 "Diarrhea involves frequent loose or watery stools.", 
                 "Mild to Moderate", "Food poisoning or viral infection", "Stay hydrated, eat bland foods"),
                
                ("cough", "diarrhea and cough", "adult", "mild", "Dextromethorphan 10-20mg every 4 hours as needed.", 
                 "Cough is a reflex to clear the airways of irritants or mucus.", 
                 "Mild", "Cold or allergies", "Stay hydrated, avoid irritants"),
                
                ("diarrhea", "diarrhea and cough", "child", "moderate", "Oral rehydration solution (e.g., Pedialyte), 50-100mL/kg over 4 hours.", 
                 "Diarrhea in children can lead to dehydration if not managed.", 
                 "Mild", "Viral infections", "Use oral rehydration, avoid sugary drinks"),
                
                ("cough", "diarrhea and cough", "child", "moderate", "Honey (for ages 1+), 1-2 tsp at bedtime.", 
                 "Cough in children can be due to viral infections or irritants.", 
                 "Mild", "Viral infections", "Use a humidifier, avoid smoke")
            ]
            logging.debug("Inserting sample data into conditions table: %s", sample_data)
            self.cursor.executemany("INSERT INTO conditions (name, symptom, age_group, severity, treatment, description, severity_info, causes, prevention) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", sample_data)
            self.conn.commit()
            # Verify insertion
            self.cursor.execute("SELECT symptom, age_group, severity, treatment FROM conditions")
            inserted_data = self.cursor.fetchall()
            logging.debug("Verified data in conditions table: %s", inserted_data)

            # Fix invalid timestamps in the database (run once, then comment out or remove)
            self.fix_invalid_timestamps()
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            messagebox.showerror("Error", "Failed to initialize database. Please try again.")

    def fix_invalid_timestamps(self):
        try:
            self.cursor.execute("SELECT id, timestamp FROM prescriptions WHERE timestamp LIKE '2025-04-d %'")
            invalid_entries = self.cursor.fetchall()
            for id_, timestamp in invalid_entries:
                new_timestamp = timestamp.replace('-d ', '-28 ')
                self.cursor.execute("UPDATE prescriptions SET timestamp = ? WHERE id = ?", (new_timestamp, id_))
            self.conn.commit()
            logging.info("Fixed invalid timestamps in prescriptions table.")
        except sqlite3.Error as e:
            logging.error(f"Error fixing timestamps: {e}")

    def load_user_profile(self):
        try:
            self.cursor.execute("SELECT age_group, allergies, history, lifestyle FROM user_profiles WHERE username = ?", (self.username,))
            result = self.cursor.fetchone()
            if result:
                self.patient_data["age_group"], self.patient_data["allergies"], self.patient_data["history"], self.patient_data["lifestyle"] = result
            # Load prescription history
            self.cursor.execute("SELECT prescription_text, timestamp FROM prescriptions WHERE username = ? ORDER BY timestamp DESC", (self.username,))
            self.prescription_history = self.cursor.fetchall()
            self.update_history_log()
        except sqlite3.Error as e:
            logging.error(f"Error loading user profile: {e}")

    def save_user_profile(self):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO user_profiles (username, age_group, allergies, history, lifestyle)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.username, self.patient_data["age_group"], self.patient_data["allergies"], 
                  self.patient_data["history"], self.patient_data["lifestyle"]))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error saving user profile: {e}")

    def filter_languages(self, event):
        # Get the current text in the Combobox
        search_text = self.language_combobox.get().strip().lower()
        if search_text == 'select language':
            search_text = ''
        
        # Filter languages based on the search text
        if search_text:
            filtered_languages = [lang for lang in self.all_languages if search_text in lang.lower()]
        else:
            filtered_languages = self.all_languages

        # Update the Combobox values
        self.language_combobox['values'] = filtered_languages

        # If there's text, keep the dropdown open; otherwise, close it
        if filtered_languages:
            self.language_combobox.event_generate('<Down>')
        else:
            self.language_combobox.set('Select Language')

    def on_language_select(self, event):
        selected_language = self.language_combobox.get()
        if selected_language != 'Select Language' and selected_language in self.languages:
            self.set_language(selected_language)
        # Reset the Combobox values to the full list after selection
        self.language_combobox['values'] = self.all_languages

    def set_language(self, lang):
        self.language = self.languages[lang]
        self.display_message("Doctor", f"Language set to {self.language}")
        self.display_message("Doctor", self.translate_text(self.questions[self.diagnosis_state]))

    def translate_text(self, text):
        try:
            translator = Translator(to_lang=self.language)
            return translator.translate(text)
        except Exception as e:
            logging.error(f"Translation error: {e}")
            return text

    def display_message(self, sender, message):
        self.chat_log.config(state='normal')
        self.chat_log.insert(tk.END, f"{sender}: {message}\n")
        self.chat_log.config(state='disabled')
        self.chat_log.yview(tk.END)
        if sender == "Doctor":
            self.text_to_speech(message)

    def update_history_log(self):
        self.history_log.config(state='normal')
        self.history_log.delete(1.0, tk.END)
        for prescription, timestamp in self.prescription_history:
            self.history_log.insert(tk.END, f"[{timestamp}]\n{prescription}\n\n")
        self.history_log.config(state='disabled')

    def send_response(self, event=None):
        user_response = self.entry_box.get().strip()
        if not user_response:
            return

        self.display_message("User", user_response)
        self.entry_box.delete(0, tk.END)

        try:
            # Store user response
            if self.diagnosis_state == "age_group":
                if user_response.lower() in ["child", "adult"]:
                    self.patient_data["age_group"] = user_response.lower()
                    self.save_user_profile()
                else:
                    self.display_message("Doctor", "Please specify 'child' or 'adult'.")
                    return
            elif self.diagnosis_state == "vitals":
                self.patient_data["vitals"] = self.parse_vitals(user_response)
            elif self.diagnosis_state == "initial":
                # Check if the response is a command like "next" after an image upload
                if user_response.lower() != "next":
                    self.patient_data["symptoms"].append(user_response)
                    # Enhance symptom detection with keyword matching
                    symptom_lower = user_response.lower()
                    if "scaly" in symptom_lower or "scale" in symptom_lower:
                        self.patient_data["symptoms"].append("psoriasis")
                        logging.debug("Detected psoriasis from user input: %s", user_response)
                    elif "dry" in symptom_lower or "cracked" in symptom_lower:
                        self.patient_data["symptoms"].append("eczema")
                        logging.debug("Detected eczema from user input: %s", user_response)
                    elif "pimple" in symptom_lower or "acne" in symptom_lower:
                        self.patient_data["symptoms"].append("acne")
                        logging.debug("Detected acne from user input: %s", user_response)
                    # Generate follow-up questions
                    self.follow_up_questions.extend(self.generate_follow_up_questions(user_response))
                # Check if there are follow-up questions (from either text input or image upload)
                if self.follow_up_questions:
                    self.diagnosis_state = "follow_up"
                    self.display_message("Doctor", self.translate_text(self.questions["follow_up"] + self.follow_up_questions[0]))
                    return
            elif self.diagnosis_state == "follow_up":
                self.patient_data["symptoms"].append(user_response)
                if self.follow_up_questions:
                    self.follow_up_questions.pop(0)
                if self.follow_up_questions:
                    self.display_message("Doctor", self.translate_text(self.questions["follow_up"] + self.follow_up_questions[0]))
                    return
            elif self.diagnosis_state in self.patient_data:
                self.patient_data[self.diagnosis_state] = user_response
                if self.diagnosis_state in ["allergies", "history", "lifestyle"]:
                    self.save_user_profile()

            # Update severity from slider
            severity_map = {1: "mild", 2: "moderate", 3: "severe"}
            self.patient_data["severity"] = severity_map.get(self.severity_scale.get(), "mild")

            # Update diagnosis state
            state_order = ["age_group", "vitals", "initial", "follow_up", "duration", "allergies", "history", "lifestyle", "final"]
            current_index = state_order.index(self.diagnosis_state)
            next_index = current_index + 1
            while next_index < len(state_order) and state_order[next_index] == "follow_up" and not self.follow_up_questions:
                next_index += 1
            if next_index < len(state_order):
                self.diagnosis_state = state_order[next_index]
                self.display_message("Doctor", self.translate_text(self.questions[self.diagnosis_state]))
            else:
                self.entry_box.config(state='disabled')
                self.send_button.config(state='disabled')
                # Automatically generate prescription when reaching the final state
                self.generate_prescription()
        except Exception as e:
            logging.error(f"Error in send_response: {e}")
            self.display_message("Doctor", "An error occurred. Please try again or reset the chat.")

    def parse_vitals(self, response):
        vitals = {}
        try:
            temp_match = re.search(r'temperature\s*(\d+\.?\d*)\s*(°F|F|°C|C|degrees)', response, re.IGNORECASE)
            hr_match = re.search(r'heart rate\s*(\d+)\s*(bpm)?', response, re.IGNORECASE)
            if temp_match:
                temp = float(temp_match.group(1))
                unit = temp_match.group(2).upper()
                if "C" in unit:
                    temp = (temp * 9/5) + 32  # Convert Celsius to Fahrenheit
                vitals["temperature"] = temp
            if hr_match:
                vitals["heart_rate"] = int(hr_match.group(1))
        except Exception as e:
            logging.error(f"Error parsing vitals: {e}")
        return vitals

    def generate_follow_up_questions(self, symptom_desc):
        questions = []
        symptom_lower = symptom_desc.lower()
        for condition, templates in self.follow_up_templates.items():
            if condition in symptom_lower:
                questions.extend(templates)
        return questions[:2]

    def text_to_speech(self, text):
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logging.error(f"TTS error: {e}")

    def speech_to_text(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()

        try:
            with mic as source:
                self.display_message("Doctor", "Listening...")
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)
            user_response = recognizer.recognize_google(audio)
            self.entry_box.delete(0, tk.END)
            self.entry_box.insert(0, user_response)
            self.send_response()
        except sr.UnknownValueError:
            self.display_message("Doctor", "Sorry, I couldn't understand. Please try again.")
        except sr.RequestError:
            self.display_message("Doctor", "Sorry, the speech recognition service is unavailable.")
        except Exception as e:
            logging.error(f"Speech recognition error: {e}")

    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")])
        if file_path:
            try:
                self.uploaded_image = Image.open(file_path)
                self.display_message("Doctor", f"Image uploaded successfully from {file_path}")
                # Analyze the image immediately and append the result to symptoms
                detected_condition = self.analyze_image(self.uploaded_image)
                if detected_condition:
                    self.patient_data["symptoms"].append(detected_condition)
                    self.display_message("Doctor", f"Image analysis suggests: {detected_condition}")
                    # Generate follow-up questions based on the detected condition
                    self.follow_up_questions.extend(self.generate_follow_up_questions(detected_condition))
                    if self.follow_up_questions and self.diagnosis_state != "initial":
                        self.display_message("Doctor", self.translate_text(self.questions["follow_up"] + self.follow_up_questions[0]))
            except Exception as e:
                logging.error(f"Error loading image: {e}")
                self.display_message("Doctor", "Failed to load image. Please try again with a valid image file.")

    def analyze_image(self, image):
        try:
            # Convert image to RGB and resize for analysis
            img = image.convert('RGB').resize((100, 100))
            pixels = list(img.getdata())

            # Simple color analysis for skin conditions
            red_count = sum(1 for p in pixels if p[0] > 180 and p[1] < 120 and p[2] < 120)  # Adjusted threshold for redness
            white_count = sum(1 for p in pixels if all(c > 200 for c in p))  # Whitish patches for psoriasis
            yellow_count = sum(1 for p in pixels if p[0] > 150 and p[1] > 150 and p[2] < 100)  # Yellowish for acne pustules
            total_pixels = len(pixels)
            redness_ratio = red_count / total_pixels
            white_ratio = white_count / total_pixels
            yellow_ratio = yellow_count / total_pixels

            # Log the ratios for debugging
            logging.debug(f"Redness ratio: {redness_ratio}, White ratio: {white_ratio}, Yellow ratio: {yellow_ratio}")

            # Prioritize conditions based on color analysis
            if yellow_ratio > 0.05:  # Threshold for yellowish pustules (acne)
                logging.debug("Detected acne from image analysis")
                return "acne"
            elif white_ratio > 0.1:  # Threshold for white patches (psoriasis)
                logging.debug("Detected psoriasis from image analysis")
                return "psoriasis"
            elif redness_ratio > 0.15:  # Threshold for redness (rash)
                logging.debug("Detected rash from image analysis")
                return "rash"
            elif any(colorsys.rgb_to_hsv(p[0]/255, p[1]/255, p[2]/255)[1] < 0.2 for p in pixels) and any(p[0] < 100 for p in pixels):  # Dry/dull for eczema
                logging.debug("Detected eczema from image analysis")
                return "eczema"
            logging.debug("No skin condition detected from image")
            return None
        except Exception as e:
            logging.error(f"Error analyzing image: {e}")
            return None

    def generate_prescription(self):
        if not self.patient_data["age_group"]:
            messagebox.showerror("Error", "Age group not specified. Please reset and specify 'child' or 'adult'.")
            return

        # Ensure age_group is correctly set
        age_group = self.patient_data["age_group"].lower()
        prescription = f"Prescription for {'Child' if age_group == 'child' else 'Adult'} Patient:\n"
        # Add timestamp
        prescription += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        prescription += "**Symptoms and Diagnosis**\n"
        serious_condition_flag = False

        try:
            # Analyze symptoms
            for symptom_desc in self.patient_data["symptoms"]:
                symptom_lower = symptom_desc.lower()
                
                # Check for serious symptoms
                for serious in self.serious_symptoms:
                    if serious in symptom_lower:
                        serious_condition_flag = True
                        prescription += f"URGENT: {serious.capitalize()} is a serious symptom. Seek emergency medical care immediately.\n"
                        break
                
                if serious_condition_flag:
                    continue

                # Query database for treatments and additional info
                try:
                    # Use exact symptom and ensure severity matches
                    self.cursor.execute('''
                        SELECT treatment, description, severity_info, causes, prevention 
                        FROM conditions 
                        WHERE symptom = ? AND age_group = ? AND severity = ?
                    ''', (symptom_lower, age_group, self.patient_data["severity"]))
                    results = self.cursor.fetchall()
                    if not results:
                        # Fallback to mild severity if no match
                        self.cursor.execute('''
                            SELECT treatment, description, severity_info, causes, prevention 
                            FROM conditions 
                            WHERE symptom = ? AND age_group = ? AND severity = ?
                        ''', (symptom_lower, age_group, "mild"))
                        results = self.cursor.fetchall()
                    for treatment, description, severity_info, causes, prevention in results:
                        prescription += f"- Symptom: {symptom_lower}\n"
                        prescription += f"Treatment: {treatment}\n"
                        prescription += f"Description: {description}\n"
                        prescription += f"Severity: {severity_info}\n"
                        prescription += f"Causes: {causes}\n"
                        prescription += f"Prevention: {prevention}\n\n"
                    if not results:
                        prescription += f"- No specific treatment found for {symptom_lower}. Consult a doctor.\n"
                except sqlite3.Error as e:
                    logging.error(f"Database query error in generate_prescription: {e}")
                    prescription += "- Error retrieving treatment. Please consult a doctor.\n"

            # Incorporate vitals
            if self.patient_data["vitals"].get("temperature"):
                temp = self.patient_data["vitals"]["temperature"]
                if (age_group == "child" and temp > 102) or (age_group == "adult" and temp > 103):
                    prescription += f"Warning: High temperature ({temp}°F). Seek medical attention immediately.\n"
            if self.patient_data["vitals"].get("heart_rate"):
                hr = self.patient_data["vitals"]["heart_rate"]
                if hr > 100 or hr < 60:
                    prescription += f"Warning: Abnormal heart rate ({hr} bpm). Consult a doctor.\n"

            # Incorporate patient data
            prescription += "**Patient Information**\n"
            if self.patient_data["duration"]:
                prescription += f"Symptom Duration: {self.patient_data['duration']}\n"
            if self.patient_data["allergies"]:
                prescription += f"Allergies: {self.patient_data['allergies']}\n"
            else:
                prescription += "Allergies: None reported\n"
            if self.patient_data["history"]:
                prescription += f"Medical History: {self.patient_data['history']}\n"
            else:
                prescription += "Medical History: No similar symptoms reported\n"
            if self.patient_data["lifestyle"]:
                prescription += f"Lifestyle Factors: {self.patient_data['lifestyle']}\n"
            else:
                prescription += "Lifestyle Factors: None reported\n"

            # General advice
            if not serious_condition_flag:
                prescription += "\n**General Recommendations**\n"
                prescription += "- Verify all medications with a healthcare professional.\n"
                prescription += "- Monitor symptoms and seek medical attention if they worsen.\n"
                prescription += f"- {'Ensure a pediatrician reviews all treatments for children.' if age_group == 'child' else 'Check for drug interactions if on other medications.'}\n"

            prescription += "\n**Disclaimer**: These are suggested prescriptions. Consult a qualified doctor to confirm dosages and appropriateness. This chatbot is not a substitute for professional medical advice."

            # Store the prescription in self.current_prescription
            self.current_prescription = prescription

            # Save to database with corrected timestamp format
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                self.cursor.execute("INSERT INTO prescriptions (username, prescription_text, timestamp) VALUES (?, ?, ?)", 
                                    (self.username, prescription, timestamp))
                self.conn.commit()
                self.prescription_history.insert(0, (prescription, timestamp))
                self.update_history_log()
            except sqlite3.Error as e:
                logging.error(f"Database error while saving prescription: {e}")
                messagebox.showerror("Error", "Failed to save prescription to database. It will not appear in history. Check chatbot_errors.log for details.")
                # Still add to in-memory history to allow PDF export
                self.prescription_history.insert(0, (prescription, timestamp))
                self.update_history_log()

            # Display prescription in a separate window
            prescription_window = tk.Toplevel(self.root)
            prescription_window.title("Prescription")
            prescription_window.geometry("600x400")
            prescription_window.configure(bg='#f0f0f0')

            prescription_text = scrolledtext.ScrolledText(prescription_window, wrap=tk.WORD, bg='#ffffff', fg='#000000', height=20, font=('Arial', 12))
            prescription_text.insert(tk.END, prescription)
            prescription_text.pack(padx=10, pady=10, fill="both", expand=True)

            close_button = tk.Button(prescription_window, text="Close", command=prescription_window.destroy, 
                                    bg='#FF0000', fg='white', font=('Arial', 10, 'bold'))
            close_button.pack(pady=5)

            # Confirm in chat log
            self.display_message("Doctor", "Prescription generated and displayed in a new window.")
        except Exception as e:
            logging.error(f"Error generating prescription: {e}")
            self.display_message("Doctor", "Failed to generate prescription. Please try again.")

    def export_to_pdf(self):
        if not hasattr(self, "current_prescription"):
            self.display_message("Doctor", "No prescription generated yet.")
            return

        try:
            filename = f"prescription_{self.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica", 12)
            y = 750
            for line in self.current_prescription.split("\n"):
                c.drawString(50, y, line)
                y -= 15
                if y < 50:
                    c.showPage()
                    y = 750
            c.save()

            # Create a popup window to display the prescription
            popup = tk.Toplevel(self.root)
            popup.title("Microsoft Outlook")
            popup.geometry("400x300")
            popup.configure(bg='#f0f0f0')

            # Title bar
            title_label = tk.Label(popup, text="Microsoft Outlook", bg='#0078D4', fg='white', font=('Arial', 10, 'bold'), pady=5)
            title_label.pack(fill='x')

            # Prescription text
            text_label = tk.Label(popup, text=self.current_prescription, bg='#ffffff', fg='#000000', justify='left', wraplength=360, font=('Arial', 10))
            text_label.pack(padx=10, pady=10, fill='both', expand=True)

            # OK button
            ok_button = tk.Button(popup, text="OK", command=popup.destroy, bg='#0078D4', fg='white', font=('Arial', 10, 'bold'))
            ok_button.pack(pady=5)

        except Exception as e:
            logging.error(f"Error exporting PDF: {e}")
            self.display_message("Doctor", "Failed to export PDF. Please try again.")

    def export_selected_to_pdf(self):
        try:
            # Get selected text from history log
            selected_text = self.history_log.get(tk.SEL_FIRST, tk.SEL_LAST)
            if not selected_text:
                self.display_message("Doctor", "Please select a prescription in the history log.")
                return

            # Extract timestamp from selected text
            timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{1,2} \d{2}:\d{2}:\d{2})\]', selected_text)
            if not timestamp_match:
                self.display_message("Doctor", "Could not identify the prescription. Ensure the timestamp is in a valid format [YYYY-MM-DD HH:MM:SS].")
                return

            timestamp = timestamp_match.group(1)
            # Query database for the exact prescription
            self.cursor.execute("SELECT prescription_text FROM prescriptions WHERE username = ? AND timestamp = ?", 
                                (self.username, timestamp))
            result = self.cursor.fetchone()
            if not result:
                self.display_message("Doctor", "Prescription not found in database.")
                return

            prescription_text = result[0]
            # Generate PDF
            filename = f"prescription_{self.username}_{timestamp.replace(' ', '_').replace(':', '')}.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica", 12)
            y = 750
            for line in prescription_text.split("\n"):
                c.drawString(50, y, line)
                y -= 15
                if y < 50:
                    c.showPage()
                    y = 750
            c.save()
            self.display_message("Doctor", f"Selected prescription saved as {filename}")
        except tk.TclError:
            self.display_message("Doctor", "Please select a prescription in the history log.")
        except Exception as e:
            logging.error(f"Error exporting selected PDF: {e}")
            self.display_message("Doctor", "Failed to export selected prescription. Please try again.")

    def delete_selected_prescription(self):
        try:
            # Get selected text from history log
            selected_text = self.history_log.get(tk.SEL_FIRST, tk.SEL_LAST)
            if not selected_text:
                self.display_message("Doctor", "Please select a prescription in the history log to delete.")
                return

            # Extract timestamp from selected text
            timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{1,2} \d{2}:\d{2}:\d{2})\]', selected_text)
            if not timestamp_match:
                self.display_message("Doctor", "Could not identify the prescription. Ensure the timestamp is in a valid format [YYYY-MM-DD HH:MM:SS].")
                return

            timestamp = timestamp_match.group(1)
            # Delete from database
            self.cursor.execute("DELETE FROM prescriptions WHERE username = ? AND timestamp = ?", (self.username, timestamp))
            self.conn.commit()

            # Update in-memory history
            self.prescription_history = [(p, t) for p, t in self.prescription_history if t != timestamp]
            self.update_history_log()
            self.display_message("Doctor", f"Prescription from {timestamp} has been deleted.")
        except tk.TclError:
            self.display_message("Doctor", "Please select a prescription in the history log to delete.")
        except sqlite3.Error as e:
            logging.error(f"Database error while deleting prescription: {e}")
            self.display_message("Doctor", "Failed to delete prescription. Please try again.")
        except Exception as e:
            logging.error(f"Error deleting prescription: {e}")
            self.display_message("Doctor", "An error occurred while deleting. Please try again.")

    def reset_chat(self):
        # Clear all patient data, including age_group, to start fresh
        self.patient_data = {"age_group": "", "symptoms": [], "vitals": {}, "duration": "", 
                             "allergies": self.patient_data["allergies"], "history": self.patient_data["history"], 
                             "lifestyle": self.patient_data["lifestyle"], "severity": "mild"}
        # Always start from the age_group question
        self.diagnosis_state = "age_group"
        self.follow_up_questions = []
        self.uploaded_image = None
        self.chat_log.config(state='normal')
        self.chat_log.delete(1.0, tk.END)
        self.chat_log.config(state='disabled')
        self.entry_box.config(state='normal')
        self.send_button.config(state='normal')
        self.severity_scale.set(1)
        self.display_message("Doctor", self.translate_text(self.questions[self.diagnosis_state]))

    def toggle_theme(self):
        if self.theme == "light":
            # Switch to dark mode
            self.theme = "dark"
            self.root.configure(bg='#2e2e2e')
            self.chat_frame.configure(bg='#2e2e2e')
            self.history_frame.configure(bg='#2e2e2e')
            self.canvas.configure(bg='#2e2e2e')
            self.scrollable_frame.configure(bg='#2e2e2e')
            self.top_frame.configure(bg='#2e2e2e')
            self.heading.configure(bg='#2e2e2e', fg='black')
            self.disclaimer.configure(bg='#2e2e2e', fg='#FF4444')
            self.chat_log.configure(bg='#3c3c3c', fg='#ffffff')
            self.severity_label.configure(bg='#2e2e2e', fg='#ffffff')
            self.severity_scale.configure(bg='#2e2e2e', fg='#ffffff', troughcolor='#4a4a4a')
            self.entry_box.configure(bg='#3c3c3c', fg='#ffffff')
            self.input_frame.configure(bg='#2e2e2e')
            self.additional_buttons_frame.configure(bg='#2e2e2e')
            self.send_button.configure(bg='#28A745', fg='white')
            self.mic_button.configure(bg='#28A745', fg='white')
            self.upload_button.configure(bg='#007BFF', fg='white')
            self.prescription_button.configure(bg='#007BFF', fg='white')
            self.pdf_button.configure(bg='#007BFF', fg='white')
            self.reset_button.configure(bg='#FF0000', fg='white')
            self.theme_button.configure(bg='#000000', fg='white')
            self.history_log.configure(bg='#3c3c3c', fg='#ffffff')
            self.history_pdf_button.configure(bg='#007BFF', fg='white')
            self.delete_button.configure(bg='#FF0000', fg='white')
            self.language_combobox.configure(foreground='white')
            self.language_combobox.option_add('*TCombobox*Listbox*Background', '#007BFF')
            self.language_combobox.option_add('*TCombobox*Listbox*Foreground', 'white')
        else:
            # Switch to light mode
            self.theme = "light"
            self.root.configure(bg='#d8d8d8')
            self.chat_frame.configure(bg='#f0f0f0')
            self.history_frame.configure(bg='#f0f0f0')
            self.canvas.configure(bg='#f0f0f0')
            self.scrollable_frame.configure(bg='#f0f0f0')
            self.top_frame.configure(bg='#f0f0f0')
            self.heading.configure(bg='#f0f0f0', fg='black')
            self.disclaimer.configure(bg='#f0f0f0', fg='#FF0000')
            self.chat_log.configure(bg='#ffffff', fg='#000000')
            self.severity_label.configure(bg='#f0f0f0', fg='#000000')
            self.severity_scale.configure(bg='#f0f0f0', fg='#000000', troughcolor='#d3d3d3')
            self.entry_box.configure(bg='#ffffff', fg='#000000')
            self.input_frame.configure(bg='#f0f0f0')
            self.additional_buttons_frame.configure(bg='#f0f0f0')
            self.send_button.configure(bg='#28A745', fg='white')
            self.mic_button.configure(bg='#28A745', fg='white')
            self.upload_button.configure(bg='#007BFF', fg='white')
            self.prescription_button.configure(bg='#007BFF', fg='white')
            self.pdf_button.configure(bg='#007BFF', fg='white')
            self.reset_button.configure(bg='#FF0000', fg='white')
            self.theme_button.configure(bg='#000000', fg='white')
            self.history_log.configure(bg='#ffffff', fg='#000000')
            self.history_pdf_button.configure(bg='#007BFF', fg='white')
            self.delete_button.configure(bg='#FF0000', fg='white')
            self.language_combobox.configure(foreground='white')
            self.language_combobox.option_add('*TCombobox*Listbox*Background', '#007BFF')
            self.language_combobox.option_add('*TCombobox*Listbox*Foreground', 'white')

        # Update the button text to reflect the current theme
        self.theme_button.configure(text=f"Toggle to {'Light' if self.theme == 'dark' else 'Dark'} Mode")

    def __del__(self):
        try:
            self.conn.close()
        except:
            pass

class LoginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Login")
        self.root.geometry("300x200")
        self.root.configure(bg='#f0f0f0')

        # Initialize user database
        self.init_user_database()
        
        self.username_label = tk.Label(root, text="Username", bg='#f0f0f0', font=('Arial', 12))
        self.username_label.pack(pady=5)
        self.username_entry = tk.Entry(root, font=('Arial', 12))
        self.username_entry.pack(pady=5)
        
        self.password_label = tk.Label(root, text="Password", bg='#f0f0f0', font=('Arial', 12))
        self.password_label.pack(pady=5)
        self.password_entry = tk.Entry(root, show='*', font=('Arial', 12))
        self.password_entry.pack(pady=5)
        
        # Frame to hold Login and Register buttons side by side
        self.button_frame = tk.Frame(root, bg='#f0f0f0')
        self.button_frame.pack(pady=10)
        
        self.login_button = tk.Button(self.button_frame, text="Login", command=self.check_login, 
                                      bg='#0078D4', fg='white', font=('Arial', 10, 'bold'))
        self.login_button.pack(side=tk.LEFT, padx=5)
        
        self.register_button = tk.Button(self.button_frame, text="Register", command=self.register_user, 
                                         bg='#28A745', fg='white', font=('Arial', 10, 'bold'))
        self.register_button.pack(side=tk.LEFT, padx=5)

    def init_user_database(self):
        try:
            self.conn = sqlite3.connect("medical_data.db")
            self.cursor = self.conn.cursor()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"User database initialization error: {e}")
            messagebox.showerror("Error", "Failed to initialize user database. Please try again.")

    def check_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return
        
        try:
            self.cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            result = self.cursor.fetchone()
            if result and result[0] == password:
                self.conn.close()
                self.root.destroy()
                main_app(username)
            else:
                messagebox.showerror("Error", "Incorrect Username or Password")
        except sqlite3.Error as e:
            logging.error(f"Login error: {e}")
            messagebox.showerror("Error", "An error occurred during login. Please try again.")

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Username and password cannot be empty.")
            return
        
        try:
            # Check if username already exists
            self.cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if self.cursor.fetchone():
                messagebox.showerror("Error", "Username already exists. Please choose a different username.")
                return
            
            # Insert new user into the database
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            messagebox.showinfo("Success", "Registration successful! Please log in with your new credentials.")
            self.username_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
        except sqlite3.Error as e:
            logging.error(f"Registration error: {e}")
            messagebox.showerror("Error", "An error occurred during registration. Please try again.")

    def __del__(self):
        try:
            self.conn.close()
        except:
            pass

def main_app(username):
    root = tk.Tk()
    app = DoctorChatbotApp(root, username)
    root.mainloop()

if __name__ == "__main__":
    login_root = tk.Tk()
    login_app = LoginApp(login_root)
    login_root.mainloop()