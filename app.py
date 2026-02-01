import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time
import urllib.parse
from fpdf import FPDF
import base64

# --- 1. إعدادات الصفحة والستايل ---
st.set_page_config(page_title="إدارة حلباوي - النظام المتكامل", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); font-weight: bold; height: 50px;
    }
    div[data-testid="column"] button {
        background-color: #28a745 !important; color: white !important;
        height: 80px !important; border: 2px solid #1e7e34 !important;
        font-size: 16px !important; white-space: pre-wrap !important;
    }
    .company-title {
        font-family: 'Arial Black', sans-serif;
        color: #D4AF37; text-align: center; font-size: 50px;
        text-shadow: 2px 2px 4px #000000; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الوظائف الأساسية (جلب البيانات وإنتاج PDF) ---

@st.cache_resource
def get_sh():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1flePWR4hlSMjVToZfkselaf0M95fcFMtcn_G-KCK3yQ")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال بجوجل: {e}")
        return None

@st.cache_data(ttl=300)
def get_system_data(_sh):
    try:
        # جلب الأسعار
        p_sheet = _sh.worksheet("الأسعار")
        p_data = p_sheet.get_all_values()
        prices = {row[0].strip(): float(row[1]) for row in p_data[1:] if len(row) > 1 and row[1]}
        
        # جلب أرقام المناديب من شيت "البيانات"
        d_sheet = _sh.worksheet("البيانات")
        d_data = d_sheet.get_all_values()
        phones = {row[0].strip(): row[1].strip() for row in d_data[1:] if len(row) > 1}
        
        return prices, phones
    except:
        return {}, {}

def generate_invoice_pdf(rep_name, customer_name, items_list, inv_no, price_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Helbawi Bros - Invoice", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Invoice No: {inv_no} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='R')
    pdf.cell(200, 10, txt=f"Delegate: {rep_name} | Customer: {customer_name}", ln=True, align='L')
    pdf.ln(10)

    # الجدول
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(80, 10, "Item", 1, 0, 'C', True)
    pdf.cell(25, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Price", 1, 0, 'C', True)
    pdf.cell(25, 10, "VAT", 1, 0, 'C', True)
    pdf.cell(35, 10, "Total", 1, 1, 'C', True)

    g_total, v_total = 0.0, 0.0
    for item in items_list:
        name = item['اسم الصنف']
        qty = float(item['الكميه المطلوبه'])
        price = price_dict.get(name, 0.0)
        has_vat = "*" in name
        vat = (qty * price * 0.11) if has_vat else 0.0
        row_t = (qty * price) + vat
        g_total += row_t
        v_total += vat

        pdf.cell(80, 10, name[:25], 1)
        pdf.cell(25, 10, f"{qty:g}", 1, 0, 'C')
        pdf.cell(30, 10, f"{price:.2f}", 1, 0, 'C')
        pdf.cell(25, 10, f"{vat:.2f}", 1, 0, 'C')
        pdf.cell(35, 10, f"{row_t:.2f}", 1, 1, 'C')

    pdf.ln(5)
    pdf.cell(160, 10, f"Total VAT: ${v_total:.2f}", 0, 1, 'R')
    pdf.cell(160, 10, f"Grand Total: ${g_total:.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1'), g_total

# --- 3. نظام الدخول والواجهة ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    col_l = st.columns([1, 2, 1])[1]
    with col_l:
        st.markdown("<h2 style='text-align:center;'>تسجيل الدخول</h2>", unsafe_allow_html=True)
        pwd = st.text_input("كلمة السر الخاصة بالإدارة", type="password")
        if st.button("دخول النظام", use_container_width=True):
            if pwd == "Hlb_Admin_2024": 
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("كلمة السر خطأ")
    st.stop()

st.markdown('<div class="company-title">Helbawi Bros</div>', unsafe_allow_html=True)
sh = get_sh()

# --- باقي كود نظام الطلبات كما هو عندك مع دمج ميزات الـ PDF والواتساب في زر التصديق ---
# (ملاحظة: هذا الكود سيعمل مع شيتات المندوبين بانتظار فحص الإشعارات)
if sh:
    # ... (كود جلب المندوبين وفحص الإشعارات) ...
    # سأضع لك الجزء الحساس (زر التصديق) مدموجاً بالواتساب والأسعار
    
    # [هنا تضع كود عرض الطلبات واختيار المندوب من كودك السابق]
    # وعند الوصول لزر التصديق، استخدم هذا المنطق:
    
    # (هذا تبسيط للجزء الأخير من كودك بعد التعديل):
    if st.button("🚀 تصديق الطلب وإصدار الفاتورة"):
        prices, phones = get_system_data(sh)
        # 1. تنفيذ التصديق في الشيتات (كما في كودك)
        # 2. توليد الـ PDF وإظهار زر واتساب
        # 3. فتح الرابط: f"https://web.whatsapp.com/send?phone={phones.get(selected_rep)}&text=..."
