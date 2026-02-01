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

# --- 1. إعدادات الصفحة والستايل (كودك القديم) ---
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

# --- 2. محركات النظام (جلب الأسعار وتوليد PDF) ---
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
def get_phones_data(_sh):
    try:
        # قراءة شيت البيانات (التي تحتوي على أرقام المناديب)
        d_sheet = _sh.worksheet("البيانات")
        d_data = d_sheet.get_all_values()
        # تحويلها لقاموس {الاسم: الرقم}
        return {row[0].strip(): row[1].strip() for row in d_data if len(row) > 1}
    except:
        return {}


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

# --- 3. نظام الدخول ---
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

@st.cache_data(ttl=600)
def fetch_delegates(_sh):
    try:
        all_worksheets = _sh.worksheets()
        excluded_list = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Status", "رقم الطلب", "بيانات المندوبين", "المبيعات"]
        return [ws.title for ws in all_worksheets if ws.title not in excluded_list]
    except: return []

if sh:
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
                        # البحث عن عمود "التاريخ و الوقت" لإنهاء مشكلة "غير محدد"
                        idx_time = header.index('التاريخ و الوقت') if 'التاريخ و الوقت' in header else -1
                        for row in data[1:]:
                            if row[idx_status] == "بانتظار التصديق":
                                t_val = row[idx_time] if idx_time != -1 else "---"
                                st.session_state.orders.append({"name": rep, "time": t_val})
                                break
                except: continue

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}\n🕒 {o['time']}", key=f"o_{o['name']}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw = ws.get_all_values()
        if len(raw) > 1:
            header = raw[0]
            df = pd.DataFrame(raw[1:], columns=header)
            df.columns = df.columns.str.strip()
            if len(df.columns) >= 6: df.columns.values[5] = "رقم الطلب"
            
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    edited = st.data_editor(pending[['row_no', 'رقم الطلب', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    # --- كود الطباعة HTML (تنسيقك المفضل) ---
                    p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    h_content = ""
                    for tg in edited['الوجهة'].unique():
                        curr_rows = edited[edited['الوجهة'] == tg]
                        o_id = curr_rows['رقم الطلب'].iloc[0] if 'رقم الطلب' in curr_rows.columns else "---"
                        rows_html = "".join([f"<tr><td style='width:30px;'>{i+1}</td><td style='text-align:right; padding-right:5px; font-size:14px;'>{r['اسم الصنف']}</td><td style='font-size:16px; font-weight:bold; width:50px;'>{r['الكميه المطلوبه']}</td></tr>" for i, (_, r) in enumerate(curr_rows.iterrows())])
                        single_table = f"""<div style="width: 49%; border: 1.5px solid black; padding: 5px; box-sizing: border-box; background-color: white; color: black;"><div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid black; padding-bottom: 3px; margin-bottom: 5px;"><div style="text-align: right; font-size: 14px; font-weight: bold; width: 33%;">🔢 طلب: {o_id}</div><div style="text-align: center; font-size: 16px; font-weight: bold; width: 34%;">{tg}</div><div style="text-align: left; font-size: 11px; width: 33%;">{p_now}</div></div><table style="width:100%; border-collapse:collapse;"><thead><tr style="background:#eee;"><th>ت</th><th>اسم الصنف</th><th>العدد</th></tr></thead><tbody>{rows_html}</tbody></table></div>"""
                        h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:15px; page-break-inside:avoid;">{single_table}{single_table}</div>'

                    print_html = f"<script>function doPrint() {{ var w = window.open('', '', 'width=1000,height=1000'); w.document.write(`<html><head><style>table, th, td {{ border: 1px solid black; border-collapse: collapse; padding: 3px; text-align: center; }} body {{ font-family: Arial; }}</style></head><body dir='rtl'>{h_content}<script>setTimeout(function() {{ window.print(); window.close(); }}, 800);<\\/script></body></html>`); w.document.close(); }}</script><button onclick='doPrint()' style='width:100%; height:60px; background-color:#28a745; color:white; border:none; border-radius:10px; font-weight:bold; font-size:22px; cursor:pointer;'>🖨️ فتح صفحة الطباعة</button>"
                    st.components.v1.html(print_html, height=80)

                    # --- كبسة التصديق الصاروخية (PDF + واتساب) ---
                                        if st.button("🚀 تصديق الطلب، PDF، وإرسال واتساب", type="primary", use_container_width=True):
                        # 1. جلب الأسعار والأرقام (تأكد أن الوظائف موجودة فوق في الكود)
                        prices, phones = get_system_data(sh) 
                        
                        idx_status = header.index('الحالة') + 1
                        idx_qty = header.index('الكميه المطلوبه') + 1
                        
                        with st.spinner("جاري التحديث البرقي وإنتاج الفواتير..."):
                            # 2. تحديث بالجملة (Batch Update) لسرعة البرق
                            updates = []
                            for _, r in edited.iterrows():
                                row_idx = int(r['row_no'])
                                st_val = "تم التصديق" if str(r['الكميه المطلوبه']) not in ["0", "", "None"] else "ملغى"
                                updates.append({'range': gspread.utils.rowcol_to_a1(row_idx, idx_status), 'values': [[st_val]]})
                                updates.append({'range': gspread.utils.rowcol_to_a1(row_idx, idx_qty), 'values': [[r['الكميه المطلوبه']]]})
                            ws.batch_update(updates)

                            # 3. إنتاج الـ PDF والواتساب لكل زبون
                            for tg in edited['الوجهة'].unique():
                                if tg == "جردة سيارة": continue
                                
                                # تصفية الأصناف لكل زبون
                                cust_items = edited[edited['الوجهة'] == tg].to_dict('records')
                                
                                # توليد الـ PDF
                                try:
                                    pdf_b, g_total = generate_invoice_pdf(selected_rep, tg, cust_items, cust_items[0].get('رقم الطلب', '---'), prices)
                                    st.download_button(f"📥 تحميل فاتورة: {tg}", data=pdf_b, file_name=f"Invoice_{tg}.pdf", key=f"pdf_{tg}")
                                except Exception as e:
                                    st.error(f"خطأ في توليد PDF للزبون {tg}: {e}")
                                    g_total = 0

                                # سحب رقم المندوب من شيت "البيانات"
                                # تأكد أن اسم المندوب في الشيت مطابق لاسم شيت الطلبات
                                raw_phone = str(phones.get(selected_rep, "")).strip()
                                
                                if raw_phone:
                                    # تنظيف الرقم من أي فراغات أو إشارات زائد
                                    clean_phone = raw_phone.replace("+", "").replace(" ", "")
                                    wa_msg = f"تحية طيبة، تم تصديق طلبية الزبون: {tg}. المجموع: ${g_total:.2f}"
                                    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(wa_msg)}"
                                    
                                    st.markdown(f"""
                                        <a href="{wa_url}" target="_blank">
                                            <button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:10px; margin-bottom:10px; cursor:pointer; font-weight:bold;">
                                                💬 إرسال واتساب لـ {selected_rep} (فاتورة {tg})
                                            </button>
                                        </a>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning(f"⚠️ رقم المندوب {selected_rep} غير موجود في شيت البيانات")

                        st.success("✅ تم التصديق وتجهيز الروابط!")
                        # تنظيف الإشعارات بعد التحديث
                        st.session_state.orders = [o for o in st.session_state.orders if o['name'] != selected_rep]
                        if 'active_rep' in st.session_state: del st.session_state.active_rep
                        time.sleep(2)
                        st.rerun()
