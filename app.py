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
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# --- 1. إعدادات الصفحة والستايل ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); font-weight: bold; height: 50px;
    }
    .company-title {
        font-family: 'Arial Black', sans-serif;
        color: #D4AF37; text-align: center; font-size: 50px;
        text-shadow: 2px 2px 4px #000000; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. محركات النظام ---
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
        p_sheet = _sh.worksheet("الأسعار")
        p_data = p_sheet.get_all_values()
        prices = {row[0].strip(): float(row[1]) for row in p_data[1:] if len(row) > 1 and row[1]}
        d_sheet = _sh.worksheet("البيانات")
        d_data = d_sheet.get_all_values()
        phones = {row[0].strip(): row[1].strip() for row in d_data if len(row) > 1}
        return prices, phones
    except: return {}, {}

def fix_arabic(text):
    """تحويل النص العربي ليظهر بشكل صحيح في الـ PDF"""
    if not text: return ""
    reshaped_text = reshape(text)
    return get_display(reshaped_text)

def generate_invoice_pdf(rep_name, customer_name, items_list, inv_no, price_dict):
    pdf = FPDF()
    pdf.add_page()
    # ملاحظة: FPDF تحتاج لملف خط يدعم العربي، سنستخدم Arial حالياً ونعالج النص
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="HELBAWI BROS", ln=True, align='C')
    pdf.ln(10)
    
    g_total = 0.0
    for item in items_list:
        name = item.get('اسم الصنف', '---')
        qty = float(item.get('الكميه المطلوبه', 0))
        price = price_dict.get(name, 0.0)
        total = qty * price
        g_total += total
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Customer: {customer_name}", ln=True, align='L')
    pdf.cell(200, 10, txt=f"Total Amount: ${g_total:.2f}", ln=True, align='L')
    return pdf.output(dest='S').encode('latin-1'), g_total

# --- 3. إدارة الحالة والدخول ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'orders' not in st.session_state: st.session_state.orders = []

if not st.session_state.admin_logged_in:
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == "Hlb_Admin_2024": 
            st.session_state.admin_logged_in = True
            st.rerun()
    st.stop()

st.markdown('<div class="company-title">Helbawi Bros</div>', unsafe_allow_html=True)
sh = get_sh()

if sh:
    # --- فحص الإشعارات (إصلاح الـ NameError) ---
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True, type="secondary"):
        with st.spinner("جاري الفحص..."):
            st.session_state.orders = []
            excluded = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Status"]
            for ws_obj in sh.worksheets():
                if ws_obj.title not in excluded:
                    data = ws_obj.get_all_values()
                    if len(data) > 1:
                        header = data[0]
                        if 'الحالة' in header:
                            idx_status = header.index('الحالة')
                            idx_time = header.index('التاريخ و الوقت') if 'التاريخ و الوقت' in header else -1
                            for row in data[1:]:
                                if len(row) > idx_status and row[idx_status] == "بانتظار التصديق":
                                    t_val = row[idx_time] if idx_time != -1 else "---"
                                    st.session_state.orders.append({"name": ws_obj.title, "time": t_val})
                                    break

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}\n🕒 {o['time']}", key=f"btn_{i}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    delegates = [o['name'] for o in st.session_state.orders]
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        full_data = ws.get_all_values()
        header = full_data[0]
        df = pd.DataFrame(full_data[1:], columns=header)
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
        
        if not pending.empty:
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'اسم الزبون']], hide_index=True)

            # --- الخطوة 1: الطباعة ---
            if st.button("🖨️ الخطوة 1: فتح صفحة الطباعة", use_container_width=True):
                st.write("تم تجهيز نسخة الطباعة (استخدم CTRL+P)")

            # --- الخطوة 2: إرسال PDF وواتساب ---
            if st.button("📄 الخطوة 2: إرسال الروابط", use_container_width=True):
                prices, phones = get_system_data(sh)
                for tg in edited['اسم الزبون'].unique():
                    cust_items = edited[edited['اسم الزبون'] == tg].to_dict('records')
                    pdf_b, total = generate_invoice_pdf(selected_rep, tg, cust_items, "1001", prices)
                    st.download_button(f"📥 تحميل PDF: {tg}", data=pdf_b, file_name=f"{tg}.pdf")
                    
                    phone = phones.get(selected_rep, "").replace("+", "").replace(" ", "")
                    if phone:
                        msg = urllib.parse.quote(f"تم تصديق طلبية {tg}. المجموع: ${total:.2f}")
                        st.markdown(f'<a href="https://wa.me/{phone}?text={msg}" target="_blank">💬 واتساب {tg}</a>', unsafe_allow_html=True)

            # --- الخطوة 3: التصديق النهائي ---
            if st.button("🚀 الخطوة 3: تصديق نهائي وتحديث الشيت", type="primary", use_container_width=True):
                with st.spinner("جاري الحفظ..."):
                    idx_status = header.index('الحالة') + 1
                    updates = []
                    for _, r in edited.iterrows():
                        updates.append({'range': gspread.utils.rowcol_to_a1(int(r['row_no']), idx_status), 'values': [["تم التصديق"]]})
                    ws.batch_update(updates)
                    st.success("✅ تم التصديق في الجداول!")
                    st.session_state.orders = [o for o in st.session_state.orders if o['name'] != selected_rep]
                    time.sleep(1)
                    st.rerun()
