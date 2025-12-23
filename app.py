import os
import tempfile

from flask import Flask, render_template, request

from engine.analyzer import GermanAnalyzer

app = Flask(__name__)
analyzer = GermanAnalyzer()


@app.get("/")
def upload_form():
    return render_template("index.html")


@app.post("/analyze")
def analyze_pdf():
    text_input = request.form.get("text_input")
    if text_input is not None:
        html_content = analyzer.analyze_to_html(text_input)
        return render_template("reader.html", content=html_content)

    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return "No text provided or file uploaded", 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        uploaded_file.save(temp_pdf.name)
        temp_path = temp_pdf.name

    text = analyzer.extract_text_from_pdf(temp_path, 1, 10)
    html_content = analyzer.analyze_to_html(text)

    os.remove(temp_path)

    return render_template("reader.html", content=html_content)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
