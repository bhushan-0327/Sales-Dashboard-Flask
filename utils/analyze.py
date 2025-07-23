import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import warnings

warnings.filterwarnings('ignore')

def auto_detect_columns(df):
    column_mapping = {}
    df_lower_cols = {col.lower(): col for col in df.columns}

    column_candidates = {
        'date': ['date', 'order date', 'sale date', 'transaction date', 'invoice date', 'timestamp'],
        'product': ['product', 'item', 'product name', 'item name'],
        'quantity': ['quantity', 'qty', 'units'],
        'selling_price': ['selling price', 'price', 'unit price', 'sale price', 'revenue per unit'],
        'cost_price': ['cost price', 'cost', 'unit cost', 'purchase price'],
        'category': ['category', 'product category', 'item category'],
        'total_sale': ['total sale', 'total sales', 'revenue', 'gross sales'],
        'total_cost': ['total cost', 'cost of goods sold', 'cogs']
    }

    for generic_name, candidates in column_candidates.items():
        found = False
        for candidate in candidates:
            if candidate in df.columns:
                column_mapping[generic_name] = candidate
                found = True
                break
        if not found:
            for candidate in candidates:
                if candidate in df_lower_cols:
                    column_mapping[generic_name] = df_lower_cols[candidate]
                    found = True
                    break
            
    required_columns = ['date', 'product', 'quantity', 'selling_price']
    for col in required_columns:
        if col not in column_mapping:
            raise ValueError(f"Could not auto-detect '{col}' column. Please ensure your file has a column with a common name for '{col}'.")

    return column_mapping

def process_sales_data(filepath):
    file_extension = filepath.rsplit('.', 1)[1].lower()

    if file_extension == 'csv':
        df = pd.read_csv(filepath)
    elif file_extension in ['xls', 'xlsx']:
        df = pd.read_excel(filepath)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")

    original_records = len(df)

    col_map = auto_detect_columns(df.copy())
    df.rename(columns={v: k for k, v in col_map.items()}, inplace=True)

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df.dropna(subset=['date'], inplace=True)

    numeric_cols = ['quantity', 'selling_price']
    if 'cost_price' in df.columns:
        numeric_cols.append('cost_price')
    if 'total_sale' in df.columns:
        numeric_cols.append('total_sale')
    if 'total_cost' in df.columns:
        numeric_cols.append('total_cost')

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=[col], inplace=True)
            df = df[df[col] >= 0]

    if 'total_sale' not in df.columns:
        df['total_sale'] = df['quantity'] * df['selling_price']

    if 'cost_price' in df.columns and 'total_cost' not in df.columns:
        df['total_cost'] = df['quantity'] * df['cost_price']
    elif 'total_cost' not in df.columns:
        df['total_cost'] = 0

    df['profit'] = df['total_sale'] - df['total_cost']

    cleaned_records = len(df)
    data_accuracy = f"{(cleaned_records / original_records * 100):.2f}%" if original_records > 0 else "0.00%"

    total_income = df['total_sale'].sum()
    total_expense = df['total_cost'].sum()
    net_profit = df['profit'].sum()

    income_change_percent = 'N/A'
    expense_change_percent = 'N/A'
    profit_change_percent = 'N/A'

    if not df.empty and 'date' in df.columns:
        df_sorted = df.sort_values(by='date')
        
        df_sorted['month_year'] = df_sorted['date'].dt.to_period('M')
        monthly_summary = df_sorted.groupby('month_year').agg(
            total_sale=('total_sale', 'sum'),
            total_cost=('total_cost', 'sum'),
            profit=('profit', 'sum')
        ).reset_index()
        
        if len(monthly_summary) >= 2:
            current_month_data = monthly_summary.iloc[-1]
            previous_month_data = monthly_summary.iloc[-2]

            if previous_month_data['total_sale'] != 0:
                income_change_percent = f"{((current_month_data['total_sale'] - previous_month_data['total_sale']) / previous_month_data['total_sale'] * 100):.2f}%"
            if previous_month_data['total_cost'] != 0:
                expense_change_percent = f"{((current_month_data['total_cost'] - previous_month_data['total_cost']) / previous_month_data['total_cost'] * 100):.2f}%"
            if previous_month_data['profit'] != 0:
                profit_change_percent = f"{((current_month_data['profit'] - previous_month_data['profit']) / previous_month_data['profit'] * 100):.2f}%"
        else:
            pass

    summary_cards_data = {
        'total_income': f"₹{total_income:,.2f}", 
        'total_expense': f"₹{total_expense:,.2f}", 
        'net_profit': f"₹{net_profit:,.2f}", 
        'income_change_percent': income_change_percent,
        'expense_change_percent': expense_change_percent,
        'profit_change_percent': profit_change_percent
    }

    cleaned_summary_data = {
        'total_records_processed': original_records,
        'valid_records': cleaned_records,
        'data_accuracy': data_accuracy,
        'date_range': f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}" if not df.empty else "N/A",
        'currency_used': 'INR'
    }

    return df, summary_cards_data, cleaned_summary_data

def save_chart_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{img_base64}"

def generate_charts(df, charts_dir):
    chart_paths = {}

    plt.style.use('dark_background')
    sns.set_style("darkgrid") 

    if not df.empty and 'date' in df.columns and 'total_sale' in df.columns:
        daily_sales = df.groupby(df['date'].dt.date)['total_sale'].sum().reset_index()
        daily_sales['date'] = pd.to_datetime(daily_sales['date'])
        daily_sales = daily_sales.sort_values('date')

        if not daily_sales.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            sns.lineplot(x='date', y='total_sale', data=daily_sales, ax=ax, color='#7B68EE', linewidth=2.5) 
            
            ax.set_title('Daily Sales Trend', color='white', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date', color='white', fontsize=13)
            ax.set_ylabel('Daily Sales (₹)', color='white', fontsize=13) 
            
            ax.tick_params(axis='x', colors='white', rotation=0, labelsize=11) 
            ax.tick_params(axis='y', colors='white', labelsize=11)
            ax.spines['bottom'].set_color('gray')
            ax.spines['left'].set_color('gray')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.grid(True, linestyle='--', alpha=0.5, color='gray') 

            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            
            chart_paths['daily_sales_chart'] = save_chart_to_base64(fig)
        else:
            chart_paths['daily_sales_chart'] = None
    else:
        chart_paths['daily_sales_chart'] = None

    if not df.empty and 'date' in df.columns and 'profit' in df.columns:
        df['month'] = df['date'].dt.to_period('M')
        monthly_profit = df.groupby('month')['profit'].sum().reset_index()
        monthly_profit['month'] = monthly_profit['month'].dt.strftime('%b')

        if not monthly_profit.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            sns.barplot(x='month', y='profit', data=monthly_profit, ax=ax, color='#32CD32') 
            
            ax.set_title('Monthly Profit Overview', color='white', fontsize=16, fontweight='bold')
            ax.set_xlabel('Month', color='white', fontsize=13)
            ax.set_ylabel('Monthly Profit (₹)', color='white', fontsize=13)
            
            ax.tick_params(axis='x', colors='white', rotation=0, labelsize=11)
            ax.tick_params(axis='y', colors='white', labelsize=11)
            ax.spines['bottom'].set_color('gray')
            ax.spines['left'].set_color('gray')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.grid(axis='y', linestyle='--', alpha=0.5, color='gray')
            
            chart_paths['monthly_profit_chart'] = save_chart_to_base64(fig)
        else:
            chart_paths['monthly_profit_chart'] = None
    else:
        chart_paths['monthly_profit_chart'] = None

    if not df.empty and 'product' in df.columns and 'total_sale' in df.columns:
        top_products = df.groupby('product')['total_sale'].sum().nlargest(5).reset_index()

        if not top_products.empty:
            fig, ax = plt.subplots(figsize=(8, 8)) 
            colors_pie = ['#FFD700', '#FFA500', '#FFC125', '#FFB90F', '#EEAD0E'] 
            ax.pie(top_products['total_sale'], labels=top_products['product'], autopct='%1.1f%%', startangle=90, colors=colors_pie, textprops={'color': 'black', 'fontsize': 11, 'fontweight': 'bold'}, pctdistance=0.8) 
            
            ax.set_title('Top 5 Products by Sales', color='white', fontsize=16, fontweight='bold')
            ax.axis('equal') 
            chart_paths['top_products_chart'] = save_chart_to_base64(fig)
        else:
            chart_paths['top_products_chart'] = None
    else:
        chart_paths['top_products_chart'] = None

    if not df.empty and 'category' in df.columns and 'total_sale' in df.columns:
        category_sales = df.groupby('category')['total_sale'].sum().reset_index()
        
        if not category_sales.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            colors_category_bar = ['#FF6347', '#4682B4', '#DAA520', '#6A5ACD', '#20B2AA'] 
            sns.barplot(x='category', y='total_sale', data=category_sales, ax=ax, palette=colors_category_bar)
            
            ax.set_title('Sales by Category', color='white', fontsize=16, fontweight='bold')
            ax.set_xlabel('Category', color='white', fontsize=13)
            ax.set_ylabel('Sales (₹)', color='white', fontsize=13) 
            
            ax.tick_params(axis='x', colors='white', rotation=0, labelsize=11)
            ax.tick_params(axis='y', colors='white', labelsize=11)
            ax.spines['bottom'].set_color('gray')
            ax.spines['left'].set_color('gray')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.grid(axis='y', linestyle='--', alpha=0.5, color='gray')

            chart_paths['category_split_chart'] = save_chart_to_base64(fig)
        else:
            chart_paths['category_split_chart'] = None
    else:
        chart_paths['category_split_chart'] = None

    return chart_paths
