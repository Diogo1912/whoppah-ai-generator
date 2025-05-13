import os
import base64
import json
import re
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import openai

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

def encode_image(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_json_block(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else "{}"

@app.route('/', methods=['GET', 'POST'])
def index():
    title = ""
    custom_prompt = ""
    image_urls = []
    ai_result = {}

    if request.method == 'POST':
        title = request.form.get('title', '')
        custom_prompt = request.form.get('custom_prompt', '')
        files = request.files.getlist('images')

        image_messages = []
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_urls.append(filepath)

                base64_img = encode_image(filepath)
                image_messages.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_img}"
                    }
                })

        # Compose a strong system message with clear instructions
        system_prompt = f"""
You are a professional assistant for a second-hand furniture marketplace.

Your task is to:
1. Analyze uploaded images and title.
2. Use the user-provided prompt to generate a seller-friendly description.
3. Return a JSON response with the following fields:
- description: respond to the user's custom prompt, focusing on tone/style.
- colors: list of dominant colors of the item only.
- materials: list of materials detected in the item.
- categories: most suited category for the item.
- styles: most appropriate style.
- brand: if possible, extract from the title.
- quality: overall quality (EXCELLENT, GOOD, FAIR, POOR).
- usageSigns: list of visible signs of wear/damage.
- usageSignsDescription: optional free-text summary if wear is found.
- feedback: analysis of photo quality, background, lighting, composition.

Respond only with a JSON object, no commentary.
        """

        full_prompt = f"""
User prompt for description:
\"{custom_prompt}\"

Title: \"{title}\"
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user", "content": [{"type": "text", "text": full_prompt.strip()}] + image_messages}
                ]
            )

            raw = response.choices[0].message.content
            cleaned = extract_json_block(raw)
            ai_result = json.loads(cleaned)

        except Exception as e:
            print("❌ GPT error:", e)
            ai_result = {
                "description": "Could not generate output. Try a different prompt.",
                "colors": [],
                "materials": [],
                "categories": "",
                "styles": "",
                "brand": "",
                "quality": "",
                "usageSigns": [],
                "usageSignsDescription": "",
                "feedback": ""
            }

    return render_template(
        'index.html',
        title=title,
        custom_prompt=custom_prompt,
        image_urls=image_urls,
        ai_result=ai_result
    )

if __name__ == '__main__':
    app.run(debug=True)