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
st.set_page_config(page_title="إدارة حلباوي - نسخة الميزان", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

# دالة فتح نافذة الطباعة (نسخة الطول Portrait)
def open_print_window(html_content):
    js = f"""
    <script>
    var printWin = window.open('', '', 'width=900,height=1000');
    printWin.document.write(`
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial'; direction: rtl; padding: 5mm; background: white; }}
                .invoice-box {{ border: 3px solid black; padding: 15px; margin-bottom: 20px; box-sizing: border-box; }}
                h2 {{ text-align: center; border-bottom: 3px solid black; padding-bottom: 10px; font-size: 24px; margin-top:0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border: 2px solid black; padding: 8px; text-align: center; font-size: 18px; font-weight: bold; }}
                .col-t {{ width: 10%; }} .col-qty {{ width: 20%; }} .col-name {{ width: 70%; text-align: right; }}
                @media print {{ @page {{ size: A4 portrait; margin: 10mm; }} }}
            </style>
        </head>
        <body>
            ${html_content}
            <script>setTimeout(function() {{ window.print(); window.close(); }}, 800);</script>
        </body>
        </html>
    `);
    printWin.document.close();
    </script>
    """
    st.components.v1.html(js, height=0)

# --- 2. نظام الدخول وحماية الـ Session ---
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    for name in ["Logo.JPG", "logo.jpg", "Logo.png"]:
        if os.path.exists(name): st.image(name, use_container_width=True); break
    col_l = st.columns([1, 2, 1])[1]
    with col_l:
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024": st.session_state.admin_logged_in = True; st.rerun()
            else: st.error("كلمة السر خطأ")
    st.stop()

# --- 3. الاتصال بـ Google Spreadsheet ---
@st.cache_resource
def get_sh():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال: {e}"); return None

sh = get_sh()

if sh:
    delegates = [ws.title for ws in sh.worksheets() if ws.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    
    # قسم الإشعارات
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            try:
                data = sh.worksheet(rep).get_all_values()
                if len(data) > 1 and 'الحالة' in data[0]:
                    if any(r[data[0].index('الحالة')] == "بانتظار التصديق" for r in data[1:]):
                        st.session_state.orders.append({"name": rep})
            except: continue

    if 'orders' in st.session_state and st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 طلب: {o['name']}", key=f"o_{o['name']}"):
                st.session_state.active_rep = o['name']; st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw = ws.get_all_values()
        if len(raw) > 1:
            df = pd.DataFrame(raw[1:], columns=raw[0])
            df.columns = df.columns.str.strip()
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    st.info(f"مراجعة طلب: {selected_rep}")
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    c1, c2 = st.columns(2)
                    # --- كبسة الطباعة (بالطول) ---
                    if c1.button("🖨️ طباعة للمراجعة", use_container_width=True):
                        p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                        h = ""
                        for tg in edited['الوجهة'].unique():
                            t_df = edited[edited['الوجهة'] == tg]
                            rows = "".join([f"<tr><td class='col-t'>{i+1}</td><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-name'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(t_df.iterrows())])
                            h += f'<div class="invoice-box"><h2>{tg}</h2><div style="display:flex; justify-content:space-between; font-weight:bold;"><span>المندوب: {selected_rep}</span><span>{p_now}</span></div><table><thead><tr><th class="col-t">ت</th><th class="col-qty">العدد</th><th class="col-name">اسم الصنف</th></tr></thead><tbody>{rows}</tbody></table></div>'
                        open_print_window(h)

                    # --- كبسة التصديق النهائي ---
                    if c2.button("🚀 تصديق وإغلاق الطلب", type="primary", use_container_width=True):
                        idx = raw[0].index('الحالة') + 1
                        with st.spinner("جاري التحديث..."):
                            for _, r in edited.iterrows():
                                try: ws.update_cell(int(r['row_no']), idx, "تم التصديق"); time.sleep(0.3)
                                except: pass
                        st.success("✅ تم التصديق!"); time.sleep(1); st.session_state.orders = []; st.rerun()
