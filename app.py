import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة المزدوجة النظيف ---
st.set_page_config(page_title="إدارة حلباوي - A4 Double", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    /* تنسيق الأزرار العادية */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }
    @keyframes blinking_red {
        0% { background-color: #ff4b4b; }
        50% { background-color: #8b0000; }
        100% { background-color: #ff4b4b; }
    }
    div.stButton > button[key^="btn_"] {
        animation: blinking_red 1.2s infinite !important;
        color: white !important;
    }

    /* --- كود الطباعة الاحترافي لـ A4 --- */
    @media print {
        /* إخفاء كل شي بالصفحة */
        body * { visibility: hidden !important; }
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stNotification"], .stSelectbox { 
            display: none !important; 
        }
        
        /* إظهار حاوية الطباعة فقط */
        .print-container, .print-container * { 
            visibility: visible !important; 
        }
        
        .print-container {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-around !important;
            direction: rtl !important;
        }

        .invoice-half {
            width: 48% !important;
            padding: 20px !important;
            border: 1px dashed #000 !important; /* خط خفيف للقص */
        }

        .thermal-table {
            width: 100% !important;
            border-collapse: collapse !important;
            border: 2px solid black !important;
        }
        .thermal-table th, .thermal-table td {
            border: 2px solid black !important;
            padding: 10px !important;
            text-align: center !important;
            font-size: 30px !important; /* خط كبير للـ A4 */
            font-weight: bold !important;
            color: black !important;
        }
        @page { size: A4 landscape; margin: 0; }
    }
    </style>
""", unsafe_allow_html=True)

# --- الدوال الأساسية ---
def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if os.path.exists("Logo.JPG"): st.image("Logo.JPG", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
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
    
    # قسم الإشعارات (مخفي عند الطباعة)
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
                        t_val = pending.iloc[0].get('التاريخ و الوقت', '---')
                        st.session_state.orders.append({"name": rep, "time": t_val})
    
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
            
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
            if not pending.empty:
                # محرر البيانات (مخفي عند الطباعة)
                st.markdown('<div class="no-print">', unsafe_allow_html=True)
                edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True, use_container_width=True)
                if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                    idx = raw_data[0].index('الحالة') + 1
                    for _, r in edited.iterrows(): ws.update_cell(int(r['row_no']), idx, "تم التصديق")
                    st.success("تم التصديق!"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                # --- تجهيز الفاتورة للطباعة ---
                print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %H:%M:%S')
                rows_html = "".join([f"<tr><td>{i+1}</td><td>{r.get('الكميه المطلوبه','')}</td><td style='text-align:right;'>{r.get('اسم الصنف','')}</td></tr>" for i, (_, r) in enumerate(edited.iterrows())])
                
                invoice_html = f"""
                <div style="text-align:center; border-bottom:3px solid black; padding-bottom:10px; margin-bottom:15px;">
                    <h1 style="font-size:50px; margin:0;">طلب: {selected_rep}</h1>
                    <p style="font-size:22px; margin:5px;">وقت الطباعة: {print_time}</p>
                </div>
                <table class="thermal-table">
                    <thead><tr><th style="width:10%;">ت</th><th style="width:20%;">العدد</th><th>الصنف</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
                <p style="text-align:center; margin-top:20px; font-size:20px; font-weight:bold;">*** نهاية الطلب ***</p>
                """

                # عرض النسختين المكررتين
                st.markdown(f"""
                <div class="print-container">
                    <div class="invoice-half">{invoice_html}</div>
                    <div class="invoice-half">{invoice_html}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة النسخة المزدوجة A4</button>""", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
