import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة الاحترافي ---
st.set_page_config(page_title="إدارة حلباوي - A4 Double", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    /* تنسيق البرنامج الأساسي */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }
    
    /* --- حل مشكلة كعب الصفحة والخط --- */
    @media print {
        /* إخفاء كل شيء تماماً */
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"], .stApp { 
            display: none !important; 
        }
        
        /* إظهار حاوية الطباعة فقط في أعلى الصفحة */
        .print-container {
            visibility: visible !important;
            position: fixed !important; /* تجبر المحتوى يطلع فوق */
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            direction: rtl !important;
            background-color: white !important;
            padding-top: 5mm !important;
        }

        .invoice-half {
            width: 48% !important;
            padding: 5px !important;
            border-left: 1px dashed #000 !important; /* خط وهمي للقص */
        }

        .thermal-table {
            width: 100% !important;
            border-collapse: collapse !important;
            border: 1.5px solid black !important;
        }
        
        .thermal-table th, .thermal-table td {
            border: 1.5px solid black !important;
            padding: 3px 5px !important;
            text-align: center !important;
            font-size: 19px !important; /* خط مقروء ويساع 30 صنف */
            font-weight: bold !important;
            color: black !important;
        }
        
        .invoice-title { font-size: 26px !important; margin: 0 !important; padding: 0 !important; }
        .invoice-time { font-size: 16px !important; margin-bottom: 5px !important; }

        @page { size: A4 landscape; margin: 0; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. دالة اللوغو الأساسية ---
def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if os.path.exists("Logo.JPG"):
        st.image("Logo.JPG", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align:center;'>Primum Quality</h1>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- نظام الدخول ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col2 = st.columns([1, 2, 1])[1]
    with col2:
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
                    p = df_temp[df_temp['الحالة'] == "بانتظار التصديق"]
                    if not p.empty:
                        st.session_state.orders.append({"name": rep, "time": p.iloc[0].get('التاريخ و الوقت', '---')})
    
    if 'orders' in st.session_state:
        for o in st.session_state.orders:
            if st.button(f"📦 طلب من: {o['name']} | {o['time']}", key=f"btn_{o['name']}", use_container_width=True):
                st.session_state.active_rep = o['name']
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
                st.markdown('<div class="no-print">', unsafe_allow_html=True)
                edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True, use_container_width=True)
                if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                    idx = raw_data[0].index('الحالة') + 1
                    for _, r in edited.iterrows(): ws.update_cell(int(r['row_no']), idx, "تم التصديق")
                    st.success("تم التصديق!"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                # --- محتوى الفاتورة المزدوجة ---
                print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %H:%M:%S')
                rows_html = "".join([f"<tr><td>{i+1}</td><td>{r.get('الكميه المطلوبه','')}</td><td style='text-align:right;'>{r.get('اسم الصنف','')}</td></tr>" for i, (_, r) in enumerate(edited.iterrows())])
                
                invoice_html = f"""
                <div style="text-align:center; border-bottom:2px solid black; margin-bottom:5px;">
                    <h2 class="invoice-title">طلب: {selected_rep}</h2>
                    <p class="invoice-time">وقت الطباعة: {print_time}</p>
                </div>
                <table class="thermal-table">
                    <thead><tr><th style="width:10%;">ت</th><th style="width:20%;">العدد</th><th>الصنف</th></tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
                """

                # كود عرض الحاوية للطباعة
                st.markdown(f"""
                <div class="print-container">
                    <div class="invoice-half">{invoice_html}</div>
                    <div class="invoice-half">{invoice_html}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة النسخة المزدوجة A4</button>""", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
