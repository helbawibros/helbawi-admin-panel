import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time

# --- 1. إعدادات الصفحة والستايل ---
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

@st.cache_resource
def get_sh():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال بجوجل: {e}")
        return None

# --- 2. نظام الدخول ---
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

# --- 3. نظام الطلبات وفحص الإشعارات ---
sh = get_sh()

if sh:
    delegates = [ws.title for ws in sh.worksheets() if ws.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Status"]]
    
    if st.button("🔔 فحص الإشعارات الجديدة (الطلبات المنتظرة)", use_container_width=True, type="secondary"):
        st.session_state.orders = []
        with st.spinner("جاري فحص ملفات المندوبين..."):
            for rep in delegates:
                try:
                    data = sh.worksheet(rep).get_all_values()
                    if len(data) > 1:
                        header = data[0]
                        idx_status = header.index('الحالة')
                        idx_time = header.index('التاريخ و الوقت') if 'التاريخ و الوقت' in header else -1
                        for row in data[1:]:
                            if row[idx_status] == "بانتظار التصديق":
                                # تخزين الوقت بتنسيق أجمل
                                order_time = row[idx_time] if idx_time != -1 else "---"
                                st.session_state.orders.append({"name": rep, "time": order_time})
                                break
                except: continue

    # عرض كبسات المندوبين مع وقت الطلب
    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            # الكبسة بتبين اسم المندوب وتحته وقت الطلب
            if cols[i].button(f"📦 {o['name']}\n🕒 {o['time']}", key=f"o_{o['name']}"):
                st.session_state.active_rep = o['name']
                st.rerun()

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
                    # الجدول المعدل
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    # كود الطباعة
                                        # تحضير كود الطباعة (نسختين جنب بعض)
                    p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    h_content = ""
                    for tg in edited['الوجهة'].unique():
                        rows = "".join([f"<tr><td>{i+1}</td><td>{r['الكميه المطلوبه']}</td><td style='text-align:right;'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(edited[edited['الوجهة'] == tg].iterrows())])
                        
                        # تصميم الجدول الواحد
                        single_table = f"""
                        <div style="width: 48%; border: 2px solid black; padding: 10px; box-sizing: border-box;">
                            <h2 style="margin:0; text-align:center;">{tg}</h2>
                            <div style="display:flex; justify-content:space-between; font-size:14px; font-weight:bold; margin-top:5px;">
                                <span>المندوب: {selected_rep}</span>
                                <span>{p_now}</span>
                            </div>
                            <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                                <thead style="background:#eee;">
                                    <tr><th>ت</th><th>العدد</th><th style="width:70%;">اسم الصنف</th></tr>
                                </thead>
                                <tbody>{rows}</tbody>
                            </table>
                        </div>
                        """
                        
                        # وضع نسختين جنب بعض في حاوية واحدة
                        h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:30px; page-break-inside:avoid;">{single_table}{single_table}</div>'

                    # ستايل الجدول العام
                    final_style = "<style>table, th, td { border: 1px solid black; border-collapse: collapse; padding: 5px; text-align: center; font-size: 16px; font-weight: bold; }</style>"

                    print_html = f"""
                    <script>
                    function doPrint() {{ 
                        var w = window.open('', '', 'width=1000,height=1000'); 
                        w.document.write(`<html><head><title>طباعة طلبات</title>{final_style}</head><body dir="rtl"> {h_content} <script>setTimeout(function() {{ window.print(); window.close(); }}, 800);<\\/script></body></html>`); 
                        w.document.close(); 
                    }}
                    </script>
                    <button onclick="doPrint()" style="width:100%; height:50px; background-color:#28a745; color:white; border:none; border-radius:10px; font-weight:bold; font-size:20px; cursor:pointer;">
                        🖨️ اضغط هنا لفتح صفحة الطباعة (نسختين)
                    </button>
                    """
                    st.components.v1.html(print_html, height=60)

                    
                    # --- التعديل الذكي على التصديق ---
                                        # --- زر التصديق الذكي والمعدل (حل مشكلة المحي) ---
                                        # --- زر التصديق الذكي والمعدل ---
                    if st.button("🚀 تصديق وإغلاق الطلب نهائياً", type="primary", use_container_width=True):
                        header = raw[0]
                        idx_status = header.index('الحالة') + 1
                        idx_item = header.index('اسم الصنف') + 1
                        try: 
                            idx_qty = header.index('الكميه المطلوبه') + 1
                        except: 
                            idx_qty = header.index('العدد') + 1
                        
                        with st.spinner("جاري التحديث..."):
                            for _, r in edited.iterrows():
                                try:
                                    row_idx = int(r['row_no'])
                                    item_name = str(r['اسم الصنف']).strip()
                                    item_qty = str(r['الكميه المطلوبه']).strip()

                                    # إذا انمسح الاسم أو الكمية صارت 0، الحالة بتصير "ملغى"
                                    if item_name in ["", "None", "nan"] or item_qty in ["", "0", "None", "nan"]:
                                        ws.update_cell(row_idx, idx_status, "ملغى")
                                    else:
                                        # تحديث الكمية المعدلة والحالة
                                        ws.update_cell(row_idx, idx_qty, r['الكميه المطلوبه'])
                                        ws.update_cell(row_idx, idx_status, "تم التصديق")
                                    time.sleep(0.3)
                                except: 
                                    continue
                        
                        st.success("✅ تم التصديق وتحديث الطلب!")
                        # تنظيف قائمة الطلبات ليختفي اسم المندوب فوراً
                        st.session_state.orders = [o for o in st.session_state.orders if o['name'] != selected_rep]
                        if 'active_rep' in st.session_state:
                            del st.session_state.active_rep
                        time.sleep(1)
                        st.rerun()
