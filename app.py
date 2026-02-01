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

# --- 1. الإعدادات والستايل (من كودك المفضل) ---
st.set_page_config(page_title="إدارة حلباوي - النظام المتكامل", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); font-weight: bold; height: 50px;
    }
    .rep-btn {
        background-color: #28a745 !important; color: white !important;
        border-radius: 10px; padding: 10px; margin-bottom: 5px;
        text-align: center; border: 2px solid #1e7e34;
    }
    .company-title {
        font-family: 'Arial Black', sans-serif;
        color: #D4AF37; text-align: center; font-size: 50px;
        text-shadow: 2px 2px 4px #000000; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. محركات النظام (PDF + جلب بيانات) ---
@st.cache_resource
def get_sh():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1flePWR4hlSMjVToZfkselaf0M95fcFMtcn_G-KCK3yQ")
    except: return None

@st.cache_data(ttl=300)
def get_system_data(_sh):
    try:
        p_sheet = _sh.worksheet("الأسعار")
        p_data = p_sheet.get_all_values()
        prices = {row[0].strip(): float(row[1]) for row in p_data[1:] if len(row) > 1 and row[1]}
        d_sheet = _sh.worksheet("البيانات")
        d_data = d_sheet.get_all_values()
        phones = {row[0].strip(): row[1].strip() for row in d_data[1:] if len(row) > 1}
        return prices, phones
    except: return {}, {}

def generate_invoice_pdf(rep_name, customer_name, items_list, inv_no, price_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Helbawi Bros - Invoice", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Invoice No: {inv_no} | Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='R')
    pdf.cell(200, 10, txt=f"Delegate: {rep_name} | Customer: {customer_name}", ln=True, align='L')
    pdf.ln(10)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(80, 10, "Item", 1, 0, 'C', True)
    pdf.cell(25, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Price", 1, 0, 'C', True)
    pdf.cell(25, 10, "VAT", 1, 0, 'C', True)
    pdf.cell(35, 10, "Total", 1, 1, 'C', True)
    g_total, v_total = 0.0, 0.0
    for item in items_list:
        name = item.get('اسم الصنف', '---')
        qty = float(item.get('الكميه المطلوبه', 0))
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

# --- 3. تسجيل الدخول ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    col_l = st.columns([1, 2, 1])[1]
    with col_l:
        st.markdown("<h2 style='text-align:center;'>تسجيل الدخول</h2>", unsafe_allow_html=True)
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024": 
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("خطأ")
    st.stop()

st.markdown('<div class="company-title">Helbawi Bros</div>', unsafe_allow_html=True)
sh = get_sh()

@st.cache_data(ttl=600)
def fetch_delegates(_sh):
    try:
        ws_list = _sh.worksheets()
        excluded = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Status", "رقم الطلب", "المبيعات", "Sheet1"]
        return [ws.title for ws in ws_list if ws.title not in excluded]
    except: return []

if sh:
    delegates = fetch_delegates(sh)
    if 'orders_data' not in st.session_state: st.session_state.orders_data = []
    
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True, type="secondary"):
        st.session_state.orders_data = []
        for rep in delegates:
            try:
                data = sh.worksheet(rep).get_all_values()
                if len(data) > 1:
                    header = data[0]
                    idx_status = header.index('الحالة')
                    idx_time = header.index('الوقت') if 'الوقت' in header else (header.index('التاريخ') if 'التاريخ' in header else -1)
                    
                    for row in data[1:]:
                        if row[idx_status] == "بانتظار التصديق":
                            t_val = row[idx_time] if idx_time != -1 else "🕒 غير مسجل"
                            st.session_state.orders_data.append({"name": rep, "time": t_val})
                            break
            except: continue

    # عرض أزرار المندوبين (كما في كودك المفضل)
    if st.session_state.orders_data:
        cols = st.columns(len(st.session_state.orders_data))
        for i, o in enumerate(st.session_state.orders_data):
            with cols[i]:
                if st.button(f"📦 {o['name']}\n{o['time']}", key=f"rep_btn_{o['name']}_{i}"):
                    st.session_state.active_rep = o['name']

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw = ws.get_all_values()
        if len(raw) > 1:
            header = raw[0]
            df = pd.DataFrame(raw[1:], columns=header)
            df['row_no'] = range(2, len(df) + 2)
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
            
            if not pending.empty:
                st.info(f"📋 طلبات {selected_rep} | أرسل في: {pending['الوقت'].iloc[0] if 'الوقت' in pending.columns else '---'}")
                pending['الوجهة'] = pending['اسم الزبون'].fillna('جردة سيارة').str.strip()
                edited = st.data_editor(pending[['row_no', 'رقم الطلب', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                
                # --- كود الطباعة HTML المزدوج ---
                p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                h_content = ""
                for tg in edited['الوجهة'].unique():
                    curr_rows = edited[edited['الوجهة'] == tg]
                    o_id = curr_rows['رقم الطلب'].iloc[0]
                    rows_html = "".join([f"<tr><td>{i+1}</td><td style='text-align:right;'>{r['اسم الصنف']}</td><td>{r['الكميه المطلوبه']}</td></tr>" for i, (_, r) in enumerate(curr_rows.iterrows())])
                    single_table = f"""<div style="width: 48%; border: 1.5px solid black; padding: 5px; margin: 2px;"><div style="display: flex; justify-content: space-between; border-bottom: 2px solid black;"><div>طلب: {o_id}</div><div style="font-weight:bold;">{tg}</div><div>{p_now}</div></div><table style="width:100%; border-collapse:collapse;"><thead><tr style="background:#eee;"><th>ت</th><th>اسم الصنف</th><th>العدد</th></tr></thead><tbody>{rows_html}</tbody></table></div>"""
                    h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:15px; page-break-inside:avoid;">{single_table}{single_table}</div>'

                st.components.v1.html(f"<script>function doPrint() {{ var w = window.open('', '', 'width=1000,height=1000'); w.document.write(`<html><head><style>table, th, td {{ border: 1px solid black; border-collapse: collapse; padding: 3px; text-align: center; }}</style></head><body dir='rtl'>{h_content}<script>setTimeout(function() {{ window.print(); window.close(); }}, 800);<\\/script></body></html>`); w.document.close(); }}</script><button onclick='doPrint()' style='width:100%; height:60px; background-color:#28a745; color:white; border-radius:10px; font-size:22px;'>🖨️ فتح صفحة الطباعة</button>", height=80)

                # --- التحديث بالجملة (Batch) + PDF ---
                if st.button("🚀 تصديق الطلب وإصدار الفواتير PDF", type="primary", use_container_width=True):
                    prices, phones = get_system_data(sh)
                    idx_status = header.index('الحالة') + 1
                    idx_qty = header.index('الكميه المطلوبه') + 1
                    
                    with st.spinner("🚀 جاري معالجة الطلبات بسرعة القصوى..."):
                        updates = []
                        for _, r in edited.iterrows():
                            row_idx = int(r['row_no'])
                            st_val = "تم التصديق" if str(r['الكميه المطلوبه']) not in ["0", ""] else "ملغى"
                            updates.append({'range': gspread.utils.rowcol_to_a1(row_idx, idx_status), 'values': [[st_val]]})
                            updates.append({'range': gspread.utils.rowcol_to_a1(row_idx, idx_qty), 'values': [[r['الكميه المطلوبه']]]})
                        
                        ws.batch_update(updates)

                        for tg in edited['الوجهة'].unique():
                            if tg == "جردة سيارة": continue
                            items = edited[edited['الوجهة'] == tg].to_dict('records')
                            pdf_b, g_total = generate_invoice_pdf(selected_rep, tg, items, items[0].get('رقم الطلب', '---'), prices)
                            st.download_button(f"📥 تحميل فاتورة: {tg}", data=pdf_b, file_name=f"Invoice_{tg}.pdf")
                            
                            phone = phones.get(selected_rep, "")
                            wa_url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(f'تحية طيبة، مرفق فاتورة {tg}. المجموع: ${g_total:.2f}')}"
                            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:10px; border-radius:5px; margin-bottom:10px;">💬 إرسال واتساب لـ {selected_rep}</button></a>', unsafe_allow_html=True)

                    st.success("✅ تم تصديق الطلبية بالكامل!")
                    st.session_state.orders_data = [o for o in st.session_state.orders_data if o['name'] != selected_rep]
                    if 'active_rep' in st.session_state: del st.session_state.active_rep
                    time.sleep(1)
                    st.rerun()
