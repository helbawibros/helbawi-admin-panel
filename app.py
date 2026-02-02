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

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

# --- 2. دالة معالجة العربي للـ PDF ---
def fix_arabic(text):
    if not text: return ""
    # إعادة تشكيل الحروف وتعديل الاتجاه (من اليمين لليسار)
    reshaped_text = reshape(str(text))
    return get_display(reshaped_text)

# --- 3. محركات النظام ---
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

# دالة توليد PDF معدلة لتجنب الانهيار
def generate_invoice_pdf(customer_name, items_list, price_dict):
    pdf = FPDF()
    pdf.add_page()
    # ملاحظة: FPDF1.7 لا تدعم العربي بشكل كامل، سنكتب العناوين بالإنجليزية لتجنب الـ UnicodeError
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="HELBAWI BROS - INVOICE", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Customer: {customer_name}", ln=True)
    
    total_amount = 0.0
    for item in items_list:
        price = price_dict.get(item['اسم الصنف'], 0.0)
        qty = float(item['الكميه المطلوبه'])
        total_amount += (price * qty)
    
    pdf.cell(200, 10, txt=f"Total Amount: ${total_amount:.2f}", ln=True)
    return pdf.output(dest='S').encode('latin-1'), total_amount

# --- 4. واجهة الإدارة ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'orders' not in st.session_state: st.session_state.orders = []

if not st.session_state.admin_logged_in:
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == "Hlb_Admin_2024": 
            st.session_state.admin_logged_in = True
            st.rerun()
    st.stop()

st.title("📦 لوحة تحكم Helbawi Bros")
sh = get_sh()

if sh:
    # زر فحص التنبيهات (تم إصلاح الـ NameError هنا)
    if st.button("🔔 فحص الطلبات الجديدة", use_container_width=True):
        st.session_state.orders = []
        excluded = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Status"]
        for ws_obj in sh.worksheets():
            if ws_obj.title not in excluded:
                data = ws_obj.get_all_values()
                if len(data) > 1:
                    header = data[0]
                    if 'الحالة' in header:
                        idx = header.index('الحالة')
                        if any(row[idx] == "بانتظار التصديق" for row in data[1:]):
                            st.session_state.orders.append(ws_obj.title)

    if st.session_state.orders:
        selected_rep = st.selectbox("اختر المندوب:", ["-- اختر --"] + st.session_state.orders)
        
        if selected_rep != "-- اختر --":
            ws = sh.worksheet(selected_rep)
            data = ws.get_all_values()
            header = data[0]
            df = pd.DataFrame(data[1:], columns=header)
            df['row_no'] = range(2, len(df) + 2)
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

            if not pending.empty:
                edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'اسم الزبون']], hide_index=True)

                # --- ترتيب الكبسات المطلوب ---
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🖨️ 1: طباعة", use_container_width=True):
                        st.success("جاهز للطباعة")

                with col2:
                    if st.button("📄 2: إرسال PDF", use_container_width=True):
                        prices, phones = get_system_data(sh)
                        for tg in edited['اسم الزبون'].unique():
                            items = edited[edited['اسم الزبون'] == tg].to_dict('records')
                            pdf_b, total = generate_invoice_pdf(tg, items, prices)
                            st.download_button(f"تحميل فاتورة {tg}", data=pdf_b, file_name=f"{tg}.pdf")
                            # رابط واتساب
                            phone = phones.get(selected_rep, "").replace(" ", "")
                            if phone:
                                msg = urllib.parse.quote(f"فاتورة {tg}\nالمجموع: ${total}")
                                st.markdown(f"[💬 واتساب {tg}](https://wa.me/{phone}?text={msg})")

                with col3:
                    if st.button("🚀 3: تصديق نهائي", type="primary", use_container_width=True):
                        idx_status = header.index('الحالة') + 1
                        updates = [{'range': gspread.utils.rowcol_to_a1(int(r['row_no']), idx_status), 'values': [["تم التصديق"]]} for _, r in edited.iterrows()]
                        ws.batch_update(updates)
                        st.success("✅ تم التصديق!")
                        time.sleep(1)
                        st.rerun()
