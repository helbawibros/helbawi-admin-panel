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
from fpdf import FPDF  # أضفنا المكتبة هنا لضمان العمل

# --- 1. المحركات والدالات (المصنع) ---

def generate_invoice_pdf(rep_name, customer_name, items_list):
    pdf = FPDF()
    pdf.add_page()
    
    # رأس الفاتورة
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="HELBAWI BROS - INVOICE", ln=True, align='C')
    
    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Delegate: {rep_name}", ln=True)
    pdf.cell(200, 10, txt=f"Customer: {customer_name}", ln=True)
    pdf.ln(5)
    
    # تصميم الجدول
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Product Detail", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
    pdf.cell(30, 10, "Price", 1, 0, 'C', True)
    pdf.cell(40, 10, "Total", 1, 1, 'C', True)
    
    total_invoice = 0.0
    for item in items_list:
        try:
            # الخطة الذكية: سحب السعر من عمود "سعر" في الشيت
            price_raw = item.get('سعر', 0)
            price = float(price_raw) if str(price_raw).replace('.','').isdigit() else 0.0
            
            qty_raw = item.get('الكميه المطلوبه', 0)
            qty = float(qty_raw) if str(qty_raw).replace('.','').isdigit() else 0.0
            
            row_total = price * qty
            total_invoice += row_total
            
            pdf.cell(90, 10, "Item Detail", 1)
            pdf.cell(30, 10, f"{qty:g}", 1, 0, 'C')
            pdf.cell(30, 10, f"${price:.2f}", 1, 0, 'C')
            pdf.cell(40, 10, f"${row_total:.2f}", 1, 1, 'C')
        except: continue
        
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, txt=f"GRAND TOTAL: ${total_invoice:.2f}", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1'), total_invoice

@st.cache_resource
def get_sh():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1flePWR4hlSMjVToZfkselaf0M95fcFMtcn_G-KCK3yQ")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال بجوجل: {e}")
        return None

@st.cache_data(ttl=600)
def fetch_delegates(_sh):
    try:
        all_worksheets = _sh.worksheets()
        excluded_list = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Status", "رقم الطلب", "بيانات المندوبين", "المبيعات", "الاسعار"]
        return [ws.title for ws in all_worksheets if ws.title not in excluded_list]
    except Exception as e:
        return []

# --- 2. إعدادات الصفحة والستايل ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); font-weight: bold; height: 50px;
    }
    div[data-testid="column"] button {
        background-color: #28a745 !important; color: white !important;
        height: 100px !important; border: 2px solid #1e7e34 !important;
        font-size: 18px !important; white-space: pre-wrap !important;
    }
    .company-title {
        font-family: 'Arial Black', sans-serif;
        color: #D4AF37; text-align: center; font-size: 50px;
        text-shadow: 2px 2px 4px #000000; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'orders' not in st.session_state: st.session_state.orders = []

# --- 3. نظام الدخول ---
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
st.divider()

# --- 4. تشغيل النظام وجلب البيانات ---
sh = get_sh()

if sh:
    delegates = fetch_delegates(sh)
    if not delegates:
        time.sleep(2)
        st.cache_data.clear()
        delegates = fetch_delegates(sh)

    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True, type="secondary"):
        st.session_state.orders = []
        with st.spinner("جاري الفحص..."):
            for rep in delegates:
                try:
                    data = sh.worksheet(rep).get_all_values()
                    if len(data) > 1:
                        header = data[0]
                        idx_status = header.index('الحالة')
                        for row in data[1:]:
                            if row[idx_status] == "بانتظار التصديق":
                                st.session_state.orders.append({"name": rep, "time": "جديد"})
                                break
                except: continue

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}", key=f"o_{o['name']}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw = ws.get_all_values()
        if len(raw) > 1:
            header = [h.strip() for h in raw[0]]
            df = pd.DataFrame(raw[1:], columns=header)
            
            if len(df.columns) >= 6:
                df.columns.values[5] = "رقم الطلب"
            
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    
                    # نأخذ الأعمدة الموجودة فعلياً بما فيها "سعر" إذا توفر
                    cols_to_show = ['row_no', 'رقم الطلب', 'اسم الصنف', 'الكميه المطلوبه', 'سعر', 'الوجهة']
                    existing_cols = [c for c in cols_to_show if c in pending.columns]
                    edited = st.data_editor(pending[existing_cols], hide_index=True, use_container_width=True)
                    
                    # --- كود الطباعة HTML (لا يتغير) ---
                    p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    h_content = ""
                    for tg in edited['الوجهة'].unique():
                        curr_rows = edited[edited['الوجهة'] == tg]
                        rows_html = "".join([f"<tr><td>{i+1}</td><td style='text-align:right;'>{r['اسم الصنف']}</td><td><b>{r['الكميه المطلوبه']}</b></td></tr>" for i, (_, r) in enumerate(curr_rows.iterrows())])
                        single_table = f"""<div style="width: 49%; border: 1.5px solid black; padding: 5px; background: white; color: black;"><div style="text-align: center; font-weight: bold; border-bottom: 2px solid black;">{tg}</div><table style="width:100%; border-collapse:collapse; margin-top:5px;"><thead><tr style="background:#eee;"><th>ت</th><th>اسم الصنف</th><th>العدد</th></tr></thead><tbody>{rows_html}</tbody></table></div>"""
                        h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:15px; page-break-inside:avoid;">{single_table}{single_table}</div>'

                    print_html = f"""<script>function doPrint() {{ var w = window.open('', '', 'width=1000'); w.document.write(`<html><body dir="rtl">{h_content}<script>setTimeout(function() {{ window.print(); window.close(); }}, 800);<\\/script></body></html>`); w.document.close(); }}</script><button onclick="doPrint()" style="width:100%; height:60px; background:#28a745; color:white; font-weight:bold; font-size:20px; border-radius:10px; cursor:pointer;">🖨️ طباعة الطلبات</button>"""
                    st.components.v1.html(print_html, height=80)

                    # --- كبسة الـ PDF الجديدة والمطورة ---
                    st.markdown("---")
                    if st.button("📄 توليد فواتير PDF للزبائن", use_container_width=True):
                        for tg in edited['الوجهة'].unique():
                            try:
                                cust_items = edited[edited['الوجهة'] == tg].to_dict('records')
                                pdf_bytes, total = generate_invoice_pdf(selected_rep, tg, cust_items)
                                st.download_button(label=f"📥 تحميل فاتورة {tg} (${total:.2f})", data=pdf_bytes, file_name=f"Invoice_{tg}.pdf", mime="application/pdf", key=f"pdf_{tg}")
                            except Exception as e:
                                st.error(f"⚠️ خطأ في فاتورة {tg}: {e}")

                    # --- كبسة التصديق ---
                    if st.button("🚀 تصديق وإغلاق الطلب نهائياً", type="primary", use_container_width=True):
                        idx_status = header.index('الحالة') + 1
                        idx_qty = header.index('الكميه المطلوبه') + 1
                        with st.spinner("جاري التحديث..."):
                            for _, r in edited.iterrows():
                                try:
                                    ws.update_cell(int(r['row_no']), idx_qty, r['الكميه المطلوبه'])
                                    ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                                except: continue
                        st.success("✅ تم التصديق!")
                        time.sleep(1)
                        st.rerun()
