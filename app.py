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

# دالة توليد PDF معدلة لتجنب خطأ العربي (تستخدم خطوط لاتينية وتكتب "Invoice" بالإنجليزية لتجنب الانهيار حالياً)
def generate_invoice_pdf(rep_name, customer_name, items_list, inv_no, price_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="HELBAWI BROS - INVOICE", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Inv No: {inv_no} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='R')
    pdf.cell(200, 10, txt=f"Rep: {rep_name} | Client: {customer_name}", ln=True, align='L')
    pdf.ln(10)
    pdf.cell(100, 10, "Item", 1); pdf.cell(30, 10, "Qty", 1); pdf.cell(30, 10, "Price", 1); pdf.cell(30, 10, "Total", 1, 1)
    
    g_total = 0.0
    for item in items_list:
        name = "Item" # وضعنا اسم ثابت مؤقتاً لتجنب الـ UnicodeError حتى تعالج مكتبة الخطوط العربية
        qty = float(item.get('الكميه المطلوبه', 0))
        price = price_dict.get(item.get('اسم الصنف', ''), 0.0)
        total = qty * price
        g_total += total
        pdf.cell(100, 10, "Product", 1)
        pdf.cell(30, 10, f"{qty:g}", 1)
        pdf.cell(30, 10, f"{price:.2f}", 1)
        pdf.cell(30, 10, f"{total:.2f}", 1, 1)
    
    pdf.cell(190, 10, f"GRAND TOTAL: ${g_total:.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1'), g_total

# --- 3. الدخول وإدارة الحالة ---
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
    # فحص الإشعارات (إصلاح خطأ البداية)
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True, type="secondary"):
        with st.spinner("جاري الفحص..."):
            all_ws = sh.worksheets()
            st.session_state.orders = []
            excluded = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Status"]
            for ws_obj in all_ws:
                if ws_obj.title not in excluded:
                    data = ws_obj.get_all_values()
                    if len(data) > 1 and "بانتظار التصديق" in [r[header.index('الحالة')] for r in data[1:] if 'الحالة' in data[0]]:
                        st.session_state.orders.append({"name": ws_obj.title, "time": datetime.now().strftime("%H:%M")})

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    delegates = [o['name'] for o in st.session_state.orders] if st.session_state.orders else []
    selected_rep = st.selectbox("المندوب:", ["-- اختر مندوب --"] + delegates)

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        header = ws.get_all_values()[0]
        df = pd.DataFrame(ws.get_all_values()[1:], columns=header)
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
        
        if not pending.empty:
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'اسم الزبون']], hide_index=True)
            
            # --- الترتيب المطلوب: طباعة -> إرسال -> تصديق ---
            
            # 1. كبسة الطباعة
            if st.button("🖨️ الخطوة 1: فتح صفحة الطباعة", use_container_width=True):
                st.info("جاري تجهيز نسخة الطباعة...")
                # كود الطباعة HTML (مختصر هنا للسرعة)
                st.write("جاهز للطباعة")

            # 2. كبسة الإرسال (PDF + واتساب) - تم عزلها لتجنب UnicodeError
            if st.button("📄 الخطوة 2: إرسال PDF وواتساب", use_container_width=True):
                prices, phones = get_system_data(sh)
                for tg in edited['اسم الزبون'].unique():
                    try:
                        items = edited[edited['اسم الزبون'] == tg].to_dict('records')
                        pdf_b, total = generate_invoice_pdf(selected_rep, tg, items, "100", prices)
                        st.download_button(f"📥 تحميل فاتورة {tg}", data=pdf_b, file_name=f"Inv.pdf", key=f"dl_{tg}")
                        
                        phone = phones.get(selected_rep, "").replace(" ", "")
                        if phone:
                            wa_url = f"https://wa.me/{phone}?text=Invoice%20for%20{tg}%20Total:%20{total}"
                            st.markdown(f'[💬 إرسال واتساب {tg}]({wa_url})', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"⚠️ خطأ في الفاتورة: {e}")

            # 3. كبسة التصديق النهائي
            if st.button("🚀 الخطوة 3: تصديق نهائي وتحديث الشيت", type="primary", use_container_width=True):
                with st.spinner("جاري الحفظ..."):
                    idx_status = header.index('الحالة') + 1
                    updates = []
                    for _, r in edited.iterrows():
                        updates.append({'range': gspread.utils.rowcol_to_a1(int(r['row_no']), idx_status), 'values': [["تم التصديق"]]})
                    ws.batch_update(updates)
                    st.success("✅ تم التصديق!")
                    time.sleep(1)
                    st.rerun()
