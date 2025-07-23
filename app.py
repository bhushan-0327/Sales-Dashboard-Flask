import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from utils.analyze import process_sales_data, generate_charts

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER_CHARTS = 'static/charts'
ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER_CHARTS'] = STATIC_FOLDER_CHARTS

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER_CHARTS, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'sales_file' not in request.files:
        return redirect(url_for('index', error='No file part'))
    
    file = request.files['sales_file']
    
    if file.filename == '':
        return redirect(url_for('index', error='No selected file'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            cleaned_df, summary_cards_data, cleaned_summary_data = process_sales_data(filepath)
            
            chart_paths = generate_charts(cleaned_df, app.config['STATIC_FOLDER_CHARTS'])

            dashboard_data = {
                'daily_sales_chart': chart_paths.get('daily_sales_chart'),
                'monthly_profit_chart': chart_paths.get('monthly_profit_chart'),
                'top_products_chart': chart_paths.get('top_products_chart'),
                'category_split_chart': chart_paths.get('category_split_chart'),
                'summary_cards': summary_cards_data
            }
            
            os.remove(filepath)

            return render_template('dashboard.html', 
                                   dashboard_data=dashboard_data,
                                   cleaned_summary=cleaned_summary_data)
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('index', error=f'Error processing file: {str(e)}'))
    else:
        return redirect(url_for('index', error='Invalid file type. Please upload CSV or Excel files.'))

@app.route('/static/charts/<filename>')
def serve_chart(filename):
    return send_from_directory(app.config['STATIC_FOLDER_CHARTS'], filename)

if __name__ == '__main__':
    app.run()
