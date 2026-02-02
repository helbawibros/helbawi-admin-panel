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

# --- 1. إعدادات الصفحة والستايل ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none; font-weight: bold; height: 50px;
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
        st.error(f"⚠️ خطأ اتصال: {e}")
        return None

@st.cache_data(ttl=300)
def get_system_data(_sh):
    try:
        p_sheet = _sh.worksheet("الأسعار")
        prices = {row[0].strip(): float(row[1]) for row in p_sheet.get_all_values()[1:] if len(row) > 1 and row[1]}
        d_sheet = _sh.worksheet("البيانات")
        phones = {row[0].strip(): row[1].strip() for row in d_sheet.get_all_values() if len(row) > 1}
        return prices, phones
    except: return {}, {}

def generate_invoice_pdf(rep_name, customer_name, items_list, price_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="HELBAWI BROS - INVOICE", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Client: {customer_name}", ln=True)
    pdf.ln(5)
    
    total_amount = 0.0
    for item in items_list:
        price = price_dict.get(item['اسم الصنف'], 0.0)
        qty = float(item['الكميه المطلوبه'])
        total_amount += (price * qty)
        
    pdf.cell(200, 10, txt=f"Total: ${total_amount:.2f}", ln=True)
    return pdf.output(dest='S').encode('latin-1'), total_amount

# --- 3. إدارة الجلسة والدخول ---
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
    # --- فحص الإشعارات (حل مشكلة الـ NameError) ---
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
                            for row in data[1:]:
                                if len(row) > idx_status and row[idx_status] == "بانتظار التصديق":
                                    st.session_state.orders.append({"name": ws_obj.title})
                                    break

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}", key=f"rep_{i}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    if active != "-- اختر مندوب --":
        ws = sh.worksheet(active)
        full_data = ws.get_all_values()
        header = full_data[0]
        df = pd.DataFrame(full_data[1:], columns=header)
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
        
        if not pending.empty:
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'اسم الزبون']], hide_index=True)

            # 🖨️ الخطوة 1: الطباعة
            if st.button("🖨️ الخطوة 1: طباعة التحضير", use_container_width=True):
                st.info("جاهز للطباعة (CTRL+P)")

            # 📄 الخطوة 2: الإرسال (واتساب و PDF)
            if st.button("📄 الخطوة 2: إرسال الروابط", use_container_width=True):
                prices, phones = get_system_data(sh)
                for tg in edited['اسم الزبون'].unique():
                    items = edited[edited['اسم الزبون'] == tg].to_dict('records')
                    pdf_b, total = generate_invoice_pdf(active, tg, items, prices)
                    st.download_button(f"📥 تحميل PDF لـ {tg}", data=pdf_b, file_name=f"{tg}.pdf")
                    
                    phone = phones.get(active, "").replace(" ", "")
                    if phone:
                        msg = urllib.parse.quote(f"تم تجهيز طلب {tg}. الإجمالي: ${total:.2f}")
                        st.markdown(f'<a href="https://wa.me/{phone}?text={msg}" target="_blank">💬 إرسال واتساب لـ {tg}</a>', unsafe_allow_html=True)

            # 🚀 الخطوة 3: التصديق النهائي
            if st.button("🚀 الخطوة 3: تصديق نهائي وتحديث الشيت", type="primary", use_container_width=True):
                with st.spinner("جاري التحديث..."):
                    idx_status = header.index('الحالة') + 1
                    updates = [{'range': gspread.utils.rowcol_to_a1(int(r['row_no']), idx_status), 'values': [["تم التصديق"]]} for _, r in edited.iterrows()]
                    ws.batch_update(updates)
                    st.success("✅ تم بنجاح!")
                    st.session_state.orders = [o for o in st.session_state.orders if o['name'] != active]
                    time.sleep(1)
                    st.rerun()
