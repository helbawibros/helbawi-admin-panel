import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة ---
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

    /* --- تنسيق الطباعة المعدل (خط 22px وجدول واضح) --- */
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { 
            display: none !important; 
        }
        body * { visibility: hidden; }
        .print-main-wrapper, .print-main-wrapper * { 
            visibility: visible !important; 
            color: black !important;
        }
        .print-main-wrapper { 
            position: absolute !important; 
            top: 0 !important; 
            right: 0 !important; 
            width: 100% !important; 
            direction: rtl !important;
            margin: 0 !important;
        }
        .thermal-table {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid black !important;
        }
        .thermal-table th, .thermal-table td {
            border: 1px solid black !important;
            padding: 4px;
            text-align: center;
            font-size: 22px !important; /* الحجم اللي طلبته تقريباً */
            font-weight: bold;
        }
        @page { size: 80mm auto; margin: 0; }
    }
    </style>
""", unsafe_allow_html=True)

def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    for name in ["Logo.JPG", "logo.jpg", "Logo.png"]:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            return
    st.write("### Primum Quality")
    st.markdown('</div>', unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col2 = st.columns([1, 2, 1])[1]
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

if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    show_full_logo()
    
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            data = ws.get_all_values()
            if len(data) > 1:
                df_temp = pd.DataFrame(data[1:], columns=data[0])
                df_temp.columns = df_temp.columns.str.strip()
                if 'الحالة' in df_temp.columns:
                    pending = df_temp[df_temp['الحالة'] == "بانتظار التصديق"]
                    if not pending.empty:
                        t_col = 'التاريخ و الوقت' if 'التاريخ و الوقت' in df_temp.columns else data[0][0]
                        st.session_state.orders.append({"name": rep, "time": pending.iloc[0].get(t_col, '---')})
    
    if 'orders' in st.session_state:
        for order in st.session_state.orders:
            if st.button(f"📦 طلب من: {order['name']} | أرسل في: {order['time']}", key=f"btn_{order['name']}", use_container_width=True):
                st.session_state.active_rep = order['name']
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        raw_data = ws.get_all_values()
        if len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            df.columns = df.columns.str.strip()
            df['row_no'] = range(2, len(df) + 2)
            
            if 'الحالة' in df.columns:
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                if not pending.empty:
                    st.info(f"عرض طلبات المندوب: {selected_rep}")
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True, use_container_width=True)

                    if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                        idx = raw_data[0].index('الحالة') + 1
                        for _, r in edited.iterrows():
                            ws.update_cell(int(r['row_no']), idx, "تم التصديق")
                        st.success("تم التصديق!"); st.rerun()
                    
                    print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %H:%M:%S')
                    
                    rows_html = "".join([f"<tr><td>{i+1}</td><td>{r.get('الكميه المطلوبه','')}</td><td style='text-align:right;'>{r.get('اسم الصنف','')}</td></tr>" for i, (_, r) in enumerate(edited.iterrows())])
                    
                    thermal_view = f"""
                    <div class="print-main-wrapper">
                        <div style="text-align:center; border-bottom:1px solid black; padding-bottom:5px; margin-bottom:5px;">
                            <p style="font-size:28px; font-weight:bold; margin:0;">طلب: {selected_rep}</p>
                            <p style="font-size:18px; margin:0;">وقت الطباعة: {print_time}</p>
                        </div>
                        <table class="thermal-table">
                            <thead>
                                <tr>
                                    <th style="width:10%;">ت</th>
                                    <th style="width:25%;">العدد</th>
                                    <th>الصنف</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                        <p style="text-align:center; margin-top:5px; font-size:16px;">*** نهاية الطلب ***</p>
                    </div>
                    """
                    st.markdown(thermal_view, unsafe_allow_html=True)
                    st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفاتورة</button>""", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
