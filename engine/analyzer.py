import spacy
import fitz  # PyMuPDF
import html
import json
import os
import concurrent.futures
from deep_translator import GoogleTranslator

class GermanAnalyzer:
    """
    The Core Engine for Gerüst.
    Handles PDF extraction, Linguistic Analysis (spaCy), and Translation (DeepTranslator).
    """

    # --- MAPPINGS FOR HUMAN-READABLE GRAMMAR ---
    POS_MAP = {
        "DET": "Determiner", "NOUN": "Noun", "VERB": "Verb", "AUX": "Auxiliary Verb",
        "ADJ": "Adjective", "ADV": "Adverb", "PRON": "Pronoun", "ADP": "Preposition",
        "CCONJ": "Conjunction", "SCONJ": "Conjunction", "PROPN": "Proper Noun",
        "PART": "Particle", "NUM": "Number"
    }
    CASE_MAP = {"Nom": "Nominative", "Acc": "Accusative", "Dat": "Dative", "Gen": "Genitive"}
    GENDER_MAP = {"Masc": "Masculine", "Fem": "Feminine", "Neut": "Neuter"}
    TENSE_MAP = {"Pres": "Present", "Past": "Past", "Fut": "Future"}

    def __init__(self, model_name="de_core_news_md", cache_file="german_vocab.json"):
        print(f"Initializing Gerüst Engine with model: {model_name}...")
        try:
            self.nlp = spacy.load(model_name)
            # Increase max length for large book chapters
            self.nlp.max_length = 3000000 
        except OSError:
            raise OSError(f"Model '{model_name}' not found. Please run: python -m spacy download {model_name}")
        
        self.cache_file = cache_file
        self.vocab_cache = self._load_cache()

    # --- CACHING SYSTEM ---
    def _load_cache(self):
        """Loads existing translations from local JSON file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache ({e}). Starting fresh.")
                return {}
        return {}

    def _save_cache(self):
        """Saves current translations to local JSON file."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.vocab_cache, f, ensure_ascii=False, indent=2)
            print("Vocabulary cache saved.")
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    # --- PDF EXTRACTION ---
    def extract_text_from_pdf(self, pdf_path, start_page, end_page):
        """Extracts text from a specific page range (1-based index)."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        text = ""
        total_pages = len(doc)
        
        # Convert 1-based start/end to 0-based indices
        s_idx = max(0, start_page - 1)
        e_idx = min(total_pages, end_page)

        print(f"Extracting text from pages {s_idx + 1} to {e_idx}...")
        
        for i in range(s_idx, e_idx):
            # Extract text and fix hyphenated line breaks (word-\nwrap)
            page_text = doc[i].get_text("text").replace("-\n", "")
            text += page_text + "\n\n"
            
        return text

    # --- TRANSLATION LOGIC ---
    def _translate_chunk(self, chunk):
        """Helper function: Translates a list of words using Google Translate."""
        try:
            translator = GoogleTranslator(source='de', target='en')
            results = translator.translate_batch(chunk)
            return dict(zip(chunk, results))
        except Exception as e:
            print(f"Translation chunk failed: {e}")
            return {}

    def get_translations(self, doc):
        """
        Identifies unique words in the doc, checks cache, and fetches new translations
        in parallel threads. Returns a dictionary {lemma: translation}.
        """
        # Filter for content words (ignore numbers/punctuation)
        words_to_translate = [t.lemma_ for t in doc if t.is_alpha]
        unique_words = list(set(words_to_translate))
        
        unknown_words = [w for w in unique_words if w not in self.vocab_cache]
        
        if not unknown_words:
            print("All words found in cache.")
            return self.vocab_cache

        print(f"Translating {len(unknown_words)} new words (using 10 threads)...")
        
        # Chunking for parallel processing
        chunk_size = 50
        chunks = [unknown_words[i:i + chunk_size] for i in range(0, len(unknown_words), chunk_size)]
        
        new_translations = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_chunk = {executor.submit(self._translate_chunk, chunk): chunk for chunk in chunks}
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_chunk)):
                data = future.result()
                new_translations.update(data)
                # Optional: Print progress every 5 batches
                if (i + 1) % 5 == 0:
                    print(f"Processed batch {i + 1}/{len(chunks)}...")

        # Update and save cache
        self.vocab_cache.update(new_translations)
        self._save_cache()
        
        return self.vocab_cache

    # --- CORE ANALYSIS & HTML GENERATION ---
    def analyze_to_html(self, text):
        """
        Runs the full pipeline:
        1. spaCy Analysis
        2. Translation
        3. HTML Generation (body content only)
        """
        print("Running linguistic analysis...")
        doc = self.nlp(text)

        print("Fetching translations...")
        translations = self.get_translations(doc)

        print("Generating HTML...")

        # --- BUILD HTML CONTENT ---
        html_content = """
        <div class="reader-layout">
            <div class="text-area">
                <div class="legend">
                    <span class="legend-item masculine">Masculine</span>
                    <span class="legend-item feminine">Feminine</span>
                    <span class="legend-item neuter">Neuter</span>
                    <span class="legend-item verb">Verbs</span>
                </div>
        """

        for token in doc:
            if "\n" in token.text:
                html_content += "<br>"
                continue
                
            lemma = token.lemma_
            translation = translations.get(lemma, "...")
            
            # --- BUILD GRAMMAR DATA ---
            # 1. POS
            full_pos = self.POS_MAP.get(token.pos_, token.pos_)
            grammar_lines = [f"<strong>Part of Speech:</strong> {full_pos}"]
            
            # 2. Gender
            raw_gen = token.morph.get("Gender")
            if raw_gen:
                full_gen = self.GENDER_MAP.get(raw_gen[0], raw_gen[0])
                grammar_lines.append(f"<strong>Gender:</strong> {full_gen}")

            # 3. Case
            raw_case = token.morph.get("Case")
            if raw_case:
                full_case = self.CASE_MAP.get(raw_case[0], raw_case[0])
                grammar_lines.append(f"<strong>Case:</strong> {full_case}")

            # 4. Number
            raw_num = token.morph.get("Number")

            # 5. Tense (Verbs)
            if token.pos_ in ["VERB", "AUX"]:
                raw_tense = token.morph.get("Tense")
                if raw_tense:
                    full_tense = self.TENSE_MAP.get(raw_tense[0], raw_tense[0])
                    grammar_lines.append(f"<strong>Tense:</strong> {full_tense}")

            # 6. Mood (Verbs)
            raw_mood = token.morph.get("Mood")

            grammar_html = "<br>".join(grammar_lines)

            # --- CSS CLASSES ---
            classes = ["token", f"pos-{token.pos_}"]
            if raw_gen:
                classes.append(f"gender-{raw_gen[0]}")

            if token.pos_ in ["VERB", "AUX"]:
                if token.morph.get("VerbForm") == ["Fin"]:
                    classes.append("verb-finite")
                else:
                    classes.append("verb-end")

            if raw_case:
                if raw_case[0] == "Nom":
                    classes.append("case-Nom")
                elif raw_case[0] == "Acc":
                    classes.append("case-Acc")
                elif raw_case[0] == "Dat":
                    classes.append("case-Dat")
                elif raw_case[0] == "Gen":
                    classes.append("case-Gen")

            if raw_num == ["Plur"]:
                classes.append("num-Plur")

            if token.pos_ in ["VERB", "AUX"] and raw_mood == ["Sub"]:
                classes.append("mood-Subj")

            if token.ent_type_:
                classes.append("ent-Name")

            class_str = " ".join(classes)
            
            # Escape strings for HTML safety
            safe_trans = html.escape(translation)
            safe_lemma = html.escape(lemma)
            safe_grammar = html.escape(grammar_html)
            
            html_content += f"""<span class="{class_str}" data-lemma="{safe_lemma}" data-trans="{safe_trans}" data-grammar="{safe_grammar}" onclick="updateSidebar(this)">{token.text_with_ws}</span>"""

        # --- SIDEBAR & FOOTER ---
        html_content += """
            </div>
            <div class="sidebar">
                <section class="sidebar-section word-info">
                    <div class="section-header">Word Info</div>
                    <div id="sb-word" class="sb-word">Welcome</div>
                    <div id="sb-lemma" class="sb-lemma">Click a word</div>

                    <div class="sidebar-label">English Meaning:</div>
                    <div id="sb-meaning" class="sb-meaning">...</div>

                    <div class="sidebar-label">Grammar:</div>
                    <div id="sb-grammar" class="sb-grammar"></div>

                    <a id="btn-duden" href="#" target="_blank" class="btn">📖 Open in Duden</a>
                </section>
                <section id="view-settings-container" class="sidebar-section placeholder-section"></section>
                <section id="theme-switcher-container" class="sidebar-section placeholder-section"></section>
            </div>
        </div>
        """
        
        return html_content

# --- DEBUG RUNNER (Allows you to still run it locally) ---
if __name__ == "__main__":
    import webbrowser
    
    # CONFIG
    PDF_FILE = "K.pdf"
    
    analyzer = GermanAnalyzer()
    
    # Example usage:
    try:
        raw_text = analyzer.extract_text_from_pdf(PDF_FILE, start_page=11, end_page=20)
        final_html = analyzer.analyze_to_html(raw_text)
        
        with open("gerust_debug.html", "w", encoding="utf-8") as f:
            f.write(final_html)
            
        print("Success! Opening output...")
        webbrowser.open("file://" + os.path.abspath("gerust_debug.html"))
        
    except Exception as e:
        print(f"Error: {e}")