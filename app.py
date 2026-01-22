import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة والوميض ---
st.set_page_config(page_title="إدارة حلباوي - حراري", layout="wide")

beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

    @keyframes blinking_red {
        0% { background-color: #ff4b4b; box-shadow: 0 0 5px #ff0000; }
        50% { background-color: #8b0000; box-shadow: 0 0 20px #ff0000; }
        100% { background-color: #ff4b4b; box-shadow: 0 0 5px #ff0000; }
    }

    div.stButton > button[key^="btn_"] {
        animation: blinking_red 1.2s infinite !important;
        color: white !important;
        border: 2px solid white !important;
    }

    @media print {
        body * { visibility: hidden !important; }
        .print-main-wrapper, .print-main-wrapper * { visibility: visible !important; color: #000000 !important; }
        .print-main-wrapper { position: absolute !important; top: 0 !important; right: 0 !important; width: 100% !important; direction: rtl !important; }
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
        @page { size: 80mm auto; margin: 0mm !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدوال الأساسية ---
def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if os.path.exists("Logo.JPG"):
        st.image("Logo.JPG", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>دخول الإدارة</h1>", unsafe_allow_html=True)
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True
                st.rerun()
    st.stop()

def get_client():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

client = get_client()

# --- 3. معالجة البيانات والطلبات ---
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    show_full_logo()
    
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            # استبدال get_all_records بـ get_all_values لتجنب الخطأ
            data = ws.get_all_values()
            if len(data) > 1: # إذا كان هناك بيانات غير الـ Header
                df_temp = pd.DataFrame(data[1:], columns=data[0])
                pending_orders = df_temp[df_temp['الحالة'] == "بانتظار التصديق"]
                
                if not pending_orders.empty:
                    order_time = pending_orders.iloc[0]['التاريخ و الوقت'] if 'التاريخ و الوقت' in pending_orders.columns else "غير محدد"
                    st.session_state.orders.append({"name": rep, "time": order_time})
        
        if not st.session_state.orders:
            st.toast("لا توجد طلبيات جديدة حالياً")

    if 'orders' in st.session_state:
        for order in st.session_state.orders:
            if st.button(f"📦 طلب من: {order['name']} | أرسل في: {order['time']}", key=f"btn_{order['name']}", use_container_width=True):
                st.session_state.active_rep = order['name']
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['row_no'] = range(2, len(df) + 2)
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

            if not pending.empty:
                st.info(f"عرض طلبات المندوب: {selected_rep}")
                edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True, use_container_width=True)

                if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                    for _, r in edited.iterrows():
                        ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                    st.success("تم التصديق بنجاح!")
                    st.rerun()
                
                # وقت الطباعة الفعلي (الآن)
                print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %H:%M:%S')
                
                rows_html = "".join([
                    f"<tr>"
                    f"<td style='border:1px solid black; text-align:center; font-size:25px;'>{i+1}</td>"
                    f"<td style='border:1px solid black; text-align:center; font-size:45px; font-weight:bold; background-color:#f0f0f0;'>{r['الكميه المطلوبه']}</td>"
                    f"<td style='border:1px solid black; text-align:right; font-size:36px; padding-right:10px;'>{r['اسم الصنف']}</td>"
                    f"</tr>" 
                    for i, (_, r) in enumerate(edited.iterrows())
                ])
                
                thermal_view = f"""
                <div class="print-main-wrapper">
                    <div style="text-align:center; border-bottom:2px dashed black; padding-bottom:10px; margin-bottom:10px;">
                        <p style="font-size:60px; font-weight:900; margin:0;">طلب: {selected_rep}</p>
                        <p style="font-size:28px; font-weight:bold; margin:5px 0;">وقت الطباعة: {print_time}</p>
                    </div>
                    <table style="width:100%; border-collapse:collapse;">
                        <thead>
                            <tr style="background-color:#eee;">
                                <th style="width:10%; border:1px solid black; font-size:20px;">ت</th>
                                <th style="width:25%; border:1px solid black; font-size:20px;">العدد</th>
                                <th style="border:1px solid black; font-size:20px;">الصنف</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                """
                st.markdown(thermal_view, unsafe_allow_html=True)
                st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفاتورة</button>""", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
