import spacy
import fitz  # PyMuPDF
import webbrowser
import os
import html
import json
import concurrent.futures
from deep_translator import GoogleTranslator

# --- CONFIGURATION ---
PDF_PATH = "K.pdf"
START_PAGE = 11
END_PAGE = 20
CACHE_FILE = "my_german_vocab.json"

# --- MAPPINGS FOR FULL NAMES ---
POS_MAP = {
    "DET": "Determiner", "NOUN": "Noun", "VERB": "Verb", "AUX": "Auxiliary Verb",
    "ADJ": "Adjective", "ADV": "Adverb", "PRON": "Pronoun", "ADP": "Preposition",
    "CCONJ": "Conjunction", "SCONJ": "Conjunction", "PROPN": "Proper Noun",
    "PART": "Particle", "NUM": "Number"
}
CASE_MAP = {"Nom": "Nominative", "Acc": "Accusative", "Dat": "Dative", "Gen": "Genitive"}
GENDER_MAP = {"Masc": "Masculine", "Fem": "Feminine", "Neut": "Neuter"}
TENSE_MAP = {"Pres": "Present", "Past": "Past", "Fut": "Future"}

# Load Model
print("Loading language model...")
try:
    nlp = spacy.load("de_core_news_lg")
except OSError:
    print("Error: Model not found. Run: python -m spacy download de_core_news_lg")
    exit()

# --- HELPER FUNCTIONS ---

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def extract_text(path, start, end):
    if not os.path.exists(path): return None
    doc = fitz.open(path)
    text = ""
    s_idx = max(0, start - 1)
    e_idx = min(len(doc), end)
    print(f"Extracting pages {s_idx+1} to {e_idx}...")
    for i in range(s_idx, e_idx):
        text += doc[i].get_text("text").replace("-\n", "") + "\n\n"
    return text

def translate_chunk(chunk):
    try:
        translator = GoogleTranslator(source='de', target='en')
        results = translator.translate_batch(chunk)
        return dict(zip(chunk, results))
    except Exception as e:
        print(f"Chunk failed: {e}")
        return {}

def smart_translate(words):
    vocab_cache = load_cache()
    unique_words = list(set(words))
    unknown_words = [w for w in unique_words if w not in vocab_cache]
    
    if not unknown_words:
        print("All words found in cache! Skipping translation...")
        return vocab_cache

    print(f"Found {len(unknown_words)} new words to translate. Starting parallel fetch...")
    chunk_size = 50
    chunks = [unknown_words[i:i + chunk_size] for i in range(0, len(unknown_words), chunk_size)]

    new_translations = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_chunk = {executor.submit(translate_chunk, chunk): chunk for chunk in chunks}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_chunk)):
            data = future.result()
            new_translations.update(data)
            print(f"Batch {i+1}/{len(chunks)} complete...")

    vocab_cache.update(new_translations)
    save_cache(vocab_cache)
    print("Cache updated and saved.")
    return vocab_cache

def generate_html(doc, translation_map):
    css = """
    <style>
        /* SERIF FONT FOR READING */
        body { font-family: 'Georgia', 'Times New Roman', serif; background: #f9f9f9; padding: 20px; color: #111; display: flex; gap: 20px; height: 100vh; overflow: hidden; }
        
        /* Layout */
        .text-area { flex: 3; background: #fff; padding: 50px; border-radius: 4px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow-y: auto; line-height: 1.8; font-size: 19px; }
        .sidebar { flex: 1; background: #fff; padding: 25px; border-radius: 4px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); display: flex; flex-direction: column; font-family: 'Segoe UI', sans-serif; }
        
        /* Sidebar Styling */
        .sb-word { font-size: 2em; font-weight: bold; color: #222; font-family: 'Georgia', serif; }
        .sb-meaning { font-size: 1.1em; background: #f0f4c3; padding: 15px; border-radius: 6px; border-left: 5px solid #afb42b; margin-bottom: 20px; }
        
        /* Token Styling */
        .token { cursor: pointer; padding: 1px 2px; border-radius: 3px; transition: background 0.2s; }
        .token:hover { background-color: #fff59d; }
        .token.active { background-color: #ffeb3b; }
        
        /* VERBS: Black & Bold */
        .verb-finite { font-weight: 900; color: #000; border-bottom: 2px solid #000; }
        .verb-end    { font-weight: 900; color: #000; border-bottom: 2px dashed #666; }
        
        /* GENDERS */
        .gender-Masc { border-bottom: 2px solid #90caf9; } /* Light Blue */
        .gender-Fem  { border-bottom: 2px solid #ef9a9a; } /* Light Red */
        .gender-Neut { border-bottom: 2px solid #a5d6a7; } /* Light Green */
        
        .btn { display:block; margin-top:10px; padding: 10px; background: #eee; text-align:center; text-decoration: none; color: #333; border-radius:4px; font-size:0.9em; }
        .btn:hover { background: #ddd; }
    </style>
    """

    js = """
    <script>
        function updateSidebar(element) {
            document.querySelectorAll('.token').forEach(t => t.classList.remove('active'));
            element.classList.add('active');
            
            const text = element.innerText;
            const lemma = element.getAttribute('data-lemma');
            const trans = element.getAttribute('data-trans');
            const grammar = element.getAttribute('data-grammar');
            
            document.getElementById('sb-word').innerText = text;
            document.getElementById('sb-lemma').innerText = "Base: " + lemma;
            document.getElementById('sb-meaning').innerText = trans;
            document.getElementById('sb-grammar').innerHTML = grammar;
            
            const cleanLemma = lemma.replace(/[^\\wäöüÄÖÜß]/g, '');
            document.getElementById('btn-duden').href = "https://www.duden.de/suchen/dudenonline/" + cleanLemma;
        }
    </script>
    """

    html_content = f"""
    <!DOCTYPE html>
    <html><head>{css}</head><body>
    <div class="text-area">
        <h3 style="margin-top:0">Kafka Reader (Pages {START_PAGE}-{END_PAGE})</h3>
        {js}
        <div style="margin-bottom:30px; color:#555; font-size:0.8em; font-family:sans-serif;">
            <span style="border-bottom: 2px solid #90caf9; margin-right:10px">Masculine</span> 
            <span style="border-bottom: 2px solid #ef9a9a; margin-right:10px">Feminine</span> 
            <span style="border-bottom: 2px solid #a5d6a7; margin-right:10px">Neuter</span> 
            <span style="border-bottom: 2px solid #000; font-weight:bold">Verbs</span>
        </div>
    """

    for token in doc:
        if "\n" in token.text:
            html_content += "<br>"
            continue
            
        lemma = token.lemma_
        translation = translation_map.get(lemma, "...")
        
        # --- BUILD GRAMMAR TEXT (FULL NAMES) ---
        # 1. POS
        raw_pos = token.pos_
        full_pos = POS_MAP.get(raw_pos, raw_pos)
        grammar_lines = [f"<strong>Part of Speech:</strong> {full_pos}"]
        
        # 2. Gender
        raw_gen = token.morph.get("Gender")
        if raw_gen:
            full_gen = GENDER_MAP.get(raw_gen[0], raw_gen[0])
            grammar_lines.append(f"<strong>Gender:</strong> {full_gen}")
            
        # 3. Case
        raw_case = token.morph.get("Case")
        if raw_case:
            full_case = CASE_MAP.get(raw_case[0], raw_case[0])
            grammar_lines.append(f"<strong>Case:</strong> {full_case}")

        # 4. Tense (for Verbs)
        if token.pos_ in ["VERB", "AUX"]:
            raw_tense = token.morph.get("Tense")
            if raw_tense:
                full_tense = TENSE_MAP.get(raw_tense[0], raw_tense[0])
                grammar_lines.append(f"<strong>Tense:</strong> {full_tense}")
        
        grammar_html = "<br>".join(grammar_lines)

        # --- CSS CLASSES ---
        classes = ["token"]
        # Gender Color
        if raw_gen: 
            classes.append(f"gender-{raw_gen[0]}")
        
        # Verb Bold/Underline
        if token.pos_ in ["VERB", "AUX"]:
            if token.morph.get("VerbForm") == ["Fin"]: classes.append("verb-finite")
            else: classes.append("verb-end")

        class_str = " ".join(classes)
        
        # Escape strings
        safe_trans = html.escape(translation)
        safe_lemma = html.escape(lemma)
        safe_grammar = html.escape(grammar_html)
        
        html_content += f"""<span class="{class_str}" data-lemma="{safe_lemma}" data-trans="{safe_trans}" data-grammar="{safe_grammar}" onclick="updateSidebar(this)">{token.text_with_ws}</span>"""

    html_content += """
    </div>
    <div class="sidebar">
        <div id="sb-word" class="sb-word">Welcome</div>
        <div id="sb-lemma" style="color:#666; font-style:italic; margin-bottom:15px">Click a word</div>
        
        <div style="font-weight:bold; color:#555; margin-bottom:5px;">English Meaning:</div>
        <div id="sb-meaning" class="sb-meaning">...</div>
        
        <div style="font-weight:bold; color:#555; margin-bottom:5px;">Grammar:</div>
        <div id="sb-grammar" style="background:#f9f9f9; padding:15px; border-radius:4px; border:1px solid #eee; line-height:1.6; font-size:0.95em;"></div>
        
        <a id="btn-duden" href="#" target="_blank" class="btn">📖 Open in Duden</a>
    </div>
    </body></html>
    """
    return html_content

# --- EXECUTION ---
text = extract_text(PDF_PATH, START_PAGE, END_PAGE)

if text:
    print("Analyzing grammar...")
    nlp.max_length = 3000000
    doc = nlp(text)
    
    words_to_translate = [t.lemma_ for t in doc if t.is_alpha]
    translations = smart_translate(words_to_translate)
    
    print("Generating HTML...")
    output_html = generate_html(doc, translations)
    
    filename = "kafka_reader.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(output_html)
        
    print(f"Done! Opening {filename}...")
    webbrowser.open("file://" + os.path.abspath(filename))