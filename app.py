import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="إدارة حلباوي - النسخة الاحترافية", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

# دالة فتح نافذة الطباعة (التزكاية الذكية لفك تداخل الأعمدة)
def open_print_window(html_content):
    js = f"""
    <script>
    var printWin = window.open('', '', 'width=1100,height=850');
    if (printWin) {{
        printWin.document.write(`
            <html>
            <head>
                <title>طباعة حلباوي</title>
                <style>
                    body {{ font-family: 'Arial', sans-serif; direction: rtl; padding: 10mm; background: white; }}
                    .print-row {{ display: flex; justify-content: space-between; gap: 10mm; margin-bottom: 15mm; page-break-inside: avoid; }}
                    .invoice-box {{ width: 48%; border: 3px solid black; padding: 15px; box-sizing: border-box; }}
                    h2 {{ text-align: center; border-bottom: 3px solid black; padding-bottom: 10px; margin-top: 0; font-size: 26px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ border: 2px solid black; padding: 8px; text-align: center; font-size: 19px; font-weight: bold; color: black; }}
                    .col-t {{ width: 10%; }} .col-qty {{ width: 20%; }} .col-name {{ width: 70%; text-align: right; }}
                    @media print {{ @page {{ size: A4 landscape; margin: 5mm; }} }}
                </style>
            </head>
            <body>
                ${html_content}
                <script>
                    setTimeout(function() {{ window.print(); window.close(); }}, 1000);
                <\\/script>
            </body>
            </html>
        `);
        printWin.document.close();
    }} else {{
        alert("يرجى السماح بالنوافذ المنبثقة (Pop-ups) للطباعة");
    }}
    </script>
    """
    st.components.v1.html(js, height=0)

# --- 2. نظام الدخول المحمي ---
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    for name in ["Logo.JPG", "logo.jpg", "Logo.png"]:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            break
    col2 = st.columns([1, 2, 1])[1]
    with col2:
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("كلمة السر خطأ")
    st.stop()

# --- 3. الربط مع Google ---
@st.cache_resource
def get_spreadsheet():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        # تأكد أن هذا الـ ID هو الصحيح لملفك
        return client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    except Exception as e:
        st.error(f"خطأ في الاتصال بجوجل: {e}")
        return None

sh = get_spreadsheet()

if sh:
    delegates = [work.title for work in sh.worksheets() if work.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    
    st.markdown("<h2 style='text-align:center;'>لوحة تحكم حلباوي</h2>", unsafe_allow_html=True)
    
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            try:
                ws = sh.worksheet(rep)
                data = ws.get_all_values()
                if len(data) > 1:
                    header = data[0]
                    if 'الحالة' in header:
                        idx = header.index('الحالة')
                        if any(row[idx] == "بانتظار التصديق" for row in data[1:]):
                            st.session_state.orders.append({"name": rep})
            except: continue

    if 'orders' in st.session_state and st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 طلب: {o['name']}", key=f"btn_{o['name']}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw_data = ws.get_all_values()
        if len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            df.columns = df.columns.str.strip()
            
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    
                    st.info(f"تعديل طلبات: {selected_rep}")
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    if st.button("🚀 تصديق، طباعة وإرسال النهائي", type="primary", use_container_width=True):
                        # 1. تحضير الطباعة
                        print_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                        all_html = ""
                        for target in edited['الوجهة'].unique():
                            t_df = edited[edited['الوجهة'] == target]
                            rows = "".join([f"<tr><td class='col-t'>{i+1}</td><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-name'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(t_df.iterrows())])
                            invoice = f"""
                            <div class="invoice-box">
                                <h2>{target}</h2>
                                <div style='display:flex; justify-content:space-between; font-weight:bold;'>
                                    <span>المندوب: {selected_rep}</span><span>{print_now}</span>
                                </div>
                                <table><thead><tr><th class='col-t'>ت</th><th class='col-qty'>العدد</th><th class='col-name'>اسم الصنف</th></tr></thead><tbody>{rows}</tbody></table>
                            </div>"""
                            all_html += f"<div class='print-row'>{invoice}{invoice}</div>"
                        
                        open_print_window(all_html)
                        
                        # 2. تحديث جوجل (Key Fix)
                        idx_status = raw_data[0].index('الحالة') + 1
                        with st.spinner("جاري التحديث..."):
                            for _, r in edited.iterrows():
                                try:
                                    ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                                    time.sleep(0.3)
                                except Exception as e:
                                    st.error(f"فشل تحديث السطر {r['row_no']}")
                        
                        st.success("✅ تم التصديق بنجاح")
                        time.sleep(1)
                        st.session_state.orders = []
                        st.rerun()
