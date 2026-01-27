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

# تهيئة الذاكرة
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'orders' not in st.session_state: st.session_state.orders = []

# --- 2. نظام الدخول ---
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

# --- 3. الربط مع جوجل ---
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
    st.markdown("<h2 style='text-align:center;'>لوحة تحكم حلباوي</h2>", unsafe_allow_html=True)

    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            try:
                data = sh.worksheet(rep).get_all_values()
                if len(data) > 1 and any(r[data[0].index('الحالة')] == "بانتظار التصديق" for r in data[1:]):
                    st.session_state.orders.append({"name": rep})
            except: continue

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}", key=f"o_{o['name']}"):
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
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    # تحضير كود الطباعة
                                        # تحضير كود الطباعة (نسختين يمين وشمال)
                    p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    h_content = ""
                    for tg in edited['الوجهة'].unique():
                        rows = "".join([f"<tr><td>{i+1}</td><td>{r['الكميه المطلوبه']}</td><td style='text-align:right;'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(edited[edited['الوجهة'] == tg].iterrows())])
                        
                        # قالب الفاتورة الواحدة
                        invoice_box = f"""
                        <div style="width: 48%; border: 3px solid black; padding: 10px; box-sizing: border-box;">
                            <h2 style="text-align:center; border-bottom:2px solid black; margin:0 0 10px 0; font-size:22px;">{tg}</h2>
                            <div style="display:flex; justify-content:space-between; font-weight:bold; font-size:14px;">
                                <span>المندوب: {selected_rep}</span><span>{p_now}</span>
                            </div>
                            <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                                <thead><tr><th>ت</th><th>العدد</th><th style="width:65%;">اسم الصنف</th></tr></thead>
                                <tbody>{rows}</tbody>
                            </table>
                        </div>"""

                        # دمج نسختين في سطر واحد (Flexbox)
                        h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:30px; page-break-inside:avoid;">{invoice_box}{invoice_box}</div>'

                    # --- الزر السحري (المعدل للنسختين) ---
                    print_button_html = f"""
                    <script>
                    function doPrint() {{
                        var w = window.open('', '', 'width=1100,height=1000');
                        w.document.write(`<html><head><title>طباعة نسختين</title>
                        <style>
                            body {{ font-family: Arial; direction: rtl; padding: 5mm; }}
                            th, td {{ border: 2px solid black; padding: 5px; text-align: center; font-size: 17px; font-weight: bold; }}
                            @media print {{ @page {{ size: A4 portrait; margin: 5mm; }} }}
                        </style>
                        </head><body> {h_content} <script>setTimeout(function() {{ window.print(); window.close(); }}, 800);<\\/script></body></html>`);
                        w.document.close();
                    }}
                    </script>
                    <button onclick="doPrint()" style="width:100%; height:55px; background-color:#28a745; color:white; border:none; border-radius:10px; font-weight:bold; font-size:20px; cursor:pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        🖨️ مراجعة وطباعة (نسختين يمين وشمال)
                    </button>
                    """
                    
                    st.markdown("---")
                    st.components.v1.html(print_button_html, height=70)

                    
                    if st.button("🚀 تصديق وإغلاق الطلب نهائياً", type="primary", use_container_width=True):
                        idx = raw[0].index('الحالة') + 1
                        with st.spinner("جاري التحديث..."):
                            for _, r in edited.iterrows():
                                try: ws.update_cell(int(r['row_no']), idx, "تم التصديق"); time.sleep(0.3)
                                except: pass
                        st.success("✅ تم التصديق!"); time.sleep(1); st.session_state.orders = []; st.rerun()
