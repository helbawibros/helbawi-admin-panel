import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة "القاضي" ---
st.set_page_config(page_title="إدارة حلباوي - النسخة النهائية", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    /* زر الطباعة على الشاشة */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 22px; 
        margin-top: 20px; text-align: center; line-height: 60px; text-decoration: none;
    }

    @media print {
        /* 1. إخفاء كل شيء (الموقع، اللوغو، الكبسات، القوائم) */
        header, footer, .no-print, [data-testid="stHeader"], 
        [data-testid="stSidebar"], [data-testid="stToolbar"],
        [data-testid="stDataEditor"], .stImage, h1, h2, h3 {
            display: none !important;
            height: 0 !important;
        }

        /* 2. تصفير الهوامش وسحب الفواتير للسقف */
        .stApp {
            position: absolute !important;
            top: -100px !important; /* ارفعها لـ -120 إذا لسه في فراغ */
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }
        
        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }

        /* 3. إعداد الورقة بالعرض */
        @page { 
            size: A4 landscape; 
            margin: 5mm !important; 
        }

        /* 4. تنسيق الفواتير (يمين وشمال) */
        .print-container {
            visibility: visible !important;
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            width: 100% !important;
            direction: rtl !important;
            page-break-inside: avoid !important;
        }

        .invoice-half {
            width: 48% !important;
            border: 2px dashed black !important;
            padding: 10px !important;
            box-sizing: border-box !important;
        }

        /* تنسيق الجدول والخط الكبير */
        .thermal-table {
            width: 100% !important;
            border-collapse: collapse !important;
            margin-top: 10px;
        }
        
        .thermal-table th, .thermal-table td {
            border: 2px solid black !important;
            padding: 6px !important;
            text-align: center !important;
            font-size: 20px !important;
            font-weight: bold !important;
            color: black !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- (هنا تضع كود الدخول والربط مع Google Sheets كما هو عندك) ---
# ... (ننتقل مباشرة لمنطق إنشاء محتوى الطباعة) ...

# مثال على كيفية بناء "حاوية الطباعة" داخل الكود:
def generate_print_content(target, selected_rep, target_df):
    print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
    display_title = f"طلب: {target}" if target != "جردة سيارة" else f"جردة: {selected_rep}"
    
    rows_html = "".join([
        f"<tr><td>{i+1}</td><td>{r.get('الكميه المطلوبه','')}</td><td style='text-align:right; padding-right:5px;'>{r.get('اسم الصنف','')}</td></tr>" 
        for i, (_, r) in enumerate(target_df.iterrows())
    ])
    
    # هاد هو "العنوان" اللي كان ضايع (المندوب، التاريخ، الساعة)
    invoice_header = f"""
    <div style="text-align:center; border-bottom:2px solid black; margin-bottom:5px;">
        <h2 style="margin:0; font-size:26px;">{display_title}</h2>
        <div style="display:flex; justify-content:space-between; font-size:18px; font-weight:bold; margin-top:5px;">
            <span>المندوب: {selected_rep}</span>
            <span>التاريخ: {print_time}</span>
        </div>
    </div>
    """
    
    invoice_body = f"""
    <table class="thermal-table">
        <thead><tr><th style="width:10%;">ت</th><th style="width:20%;">العدد</th><th>اسم الصنف</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    <p style="text-align:center; font-weight:bold; margin-top:5px;">*** نسخة تحضير وفواتير ***</p>
    """
    
    full_invoice = invoice_header + invoice_body
    
    # عرض النسختين جنب بعض
    st.markdown(f"""
    <div class="print-container">
        <div class="invoice-half">{full_invoice}</div>
        <div class="invoice-half">{full_invoice}</div>
    </div>
    <div class="no-print" style="border-bottom: 2px dashed #ccc; margin: 30px 0;"></div>
    """, unsafe_allow_html=True)

# --- زر الطباعة النهائي ---
st.markdown('<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفواتير المفرزة بالعنوان</button>', unsafe_allow_html=True)
