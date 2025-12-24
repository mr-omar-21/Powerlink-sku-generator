from flask import Flask, render_template_string, request, send_file, redirect
import pandas as pd
import barcode
from barcode.writer import ImageWriter
import random
import string
import io
import zipfile

app = Flask(__name__)

# --- POWERLINK BRANDED HTML & CSS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Powerlink SKU Tool</title>
    <style>
        :root { --yellow: #FEE500; --dark: #121417; --gray: #1E2126; --text: #FFFFFF; }
        body { background-color: var(--dark); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }
        .header { background-color: var(--dark); padding: 20px; border-bottom: 2px solid var(--yellow); text-align: center; }
        .header h1 { color: var(--yellow); margin: 0; letter-spacing: 2px; }
        .container { max-width: 900px; margin: 40px auto; padding: 20px; }
        .card { background: var(--gray); padding: 30px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { border-left: 5px solid var(--yellow); padding-left: 15px; margin-bottom: 25px; }
        input[type="text"], input[type="file"] { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #444; background: #000; color: white; box-sizing: border-box; }
        .btn { background-color: var(--yellow); color: black; padding: 12px 24px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.3s; font-size: 16px; }
        .btn:hover { background-color: #e6cf00; transform: translateY(-2px); }
        .result-area { text-align: center; margin-top: 20px; padding: 20px; border: 1px dashed var(--yellow); border-radius: 8px; }
        .barcode-img { background: white; padding: 15px; border-radius: 5px; margin-top: 15px; }
        .footer { text-align: center; font-size: 12px; color: #666; margin-top: 50px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>POWERLINK</h1>
        <p>SKU & BARCODE GENERATOR</p>
    </div>

    <div class="container">
        <div class="card">
            <h2>⚡ Single SKU Generation</h2>
            <form method="POST" action="/generate_single">
                <input type="text" name="biz" placeholder="Business Name" required>
                <input type="text" name="prod" placeholder="Product Name" required>
                <button type="submit" class="btn">GENERATE SKU</button>
            </form>
            
            {% if sku %}
            <div class="result-area">
                <p>Generated SKU: <strong style="color: var(--yellow); font-size: 24px;">{{ sku }}</strong></p>
                <img src="data:image/png;base64,{{ barcode_base64 }}" class="barcode-img">
            </div>
            {% endif %}
        </div>

        <div class="card">
            <h2>📁 Bulk Excel Processing</h2>
            <p style="font-size: 14px; color: #aaa;">Upload an Excel file with 'Business' and 'Product' columns.</p>
            <form method="POST" action="/generate_bulk" enctype="multipart/form-data">
                <input type="file" name="file" accept=".xlsx" required>
                <button type="submit" class="btn">PROCESS & DOWNLOAD ALL</button>
            </form>
        </div>
    </div>

    <div class="footer">
        © 2024 Powerlink Design | powerlink.design@gmail.com | www.powerlink.cfd
    </div>
</body>
</html>
"""

# --- PYTHON LOGIC ---
def create_sku(biz, prod):
    b = str(biz)[:3].upper()
    p = str(prod)[:3].upper()
    r = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{b}-{p}-{r}"

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate_single', methods=['POST'])
def generate_single():
    import base64
    biz = request.form.get('biz')
    prod = request.form.get('prod')
    sku = create_sku(biz, prod)
    
    # Generate barcode
    code128 = barcode.get_barcode_class('code128')
    rv = io.BytesIO()
    code128(sku, writer=ImageWriter()).write(rv)
    barcode_base64 = base64.b64encode(rv.getvalue()).decode('utf-8')
    
    return render_template_string(HTML_TEMPLATE, sku=sku, barcode_base64=barcode_base64)

@app.route('/generate_bulk', methods=['POST'])
def generate_bulk():
    file = request.files['file']
    if not file: return redirect('/')
    
    df = pd.read_excel(file)
    df.columns = [c.strip().capitalize() for c in df.columns]
    
    if 'Business' not in df.columns or 'Product' not in df.columns:
        return "Error: Missing Columns. Need 'Business' and 'Product'."

    df['SKU'] = df.apply(lambda x: create_sku(x['Business'], x['Product']), axis=1)
    
    # Create ZIP in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Add Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        zf.writestr("Powerlink_SKUs.xlsx", excel_buffer.getvalue())
        
        # Add Barcodes
        code128 = barcode.get_barcode_class('code128')
        for sku in df['SKU']:
            img_buf = io.BytesIO()
            code128(sku, writer=ImageWriter()).write(img_buf)
            zf.writestr(f"barcodes/{sku}.png", img_buf.getvalue())
            
    memory_file.seek(0)
    return send_file(memory_file, download_name="Powerlink_Batch.zip", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)