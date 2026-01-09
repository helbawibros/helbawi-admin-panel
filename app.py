import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة والتنسيق (حل مشكلة النقص وتعدد الصفحات) ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

    @media print {
        body * { visibility: hidden !important; }
        
        .print-main-wrapper, .print-main-wrapper * { 
            visibility: visible !important; 
            color: #000000 !important;
            -webkit-print-color-adjust: exact;
        }

        .print-main-wrapper {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            display: block !important; 
            direction: rtl !important;
        }

        /* النسخة تأخذ كامل العرض لضمان عدم نقص أي سطر */
        .order-copy {
            width: 100% !important;
            margin-bottom: 50px !important;
            page-break-after: auto !important;
        }

        .copy-label {
            text-align: center;
            font-size: 20px;
            font-weight: bold;
            border: 2px solid #000;
            margin-bottom: 10px;
            padding: 5px;
            background-color: #eee !important;
        }

        @page { 
            size: A4 portrait; 
            margin: 1cm !important; 
        }

        .header-box {
            border-bottom: 4px solid #000 !important; 
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        .name-txt { font-size: 28px !important; font-weight: 900 !important; margin:0; }
        
        .table-style { 
            width: 100%; 
            border-collapse: collapse; 
            border: 3px solid #000 !important;
        }
        
        .table-style th, .table-style td {
            border: 2px solid #000 !important; 
            padding: 12px !important;
            font-size: 20px !important; 
            font-weight: 950 !important; 
            -webkit-text-stroke: 0.8px black;
        }
        
        .col-qty { 
            width: 15%;
            font-size: 30px !important; 
            -webkit-text-stroke: 1.2px black; 
        }

        /* منع انقسام السطر الواحد */
        tr { page-break-inside: avoid !important; }

        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { 
            display: none !important; 
        }
    }
    </style>
""", unsafe_allow_html=True)

def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if os.path.exists("Logo.JPG"):
        st.image("Logo.JPG", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- نظام الدخول والاتصال ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
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
            if "بانتظار التصديق" in ws.col_values(4): st.session_state.orders.append(rep)

    if 'orders' in st.session_state:
        for name in st.session_state.orders:
            if st.button(f"📦 طلبية جديدة من: {name}", key=f"btn_{name}"):
                st.session_state.active_rep = name
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            order_time = pending.iloc[0]['التاريخ و الوقت']
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True, use_container_width=True)

            if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                for _, r in edited.iterrows(): ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                st.success("تم التصديق بنجاح!"); st.rerun()
            
            rows_html = "".join([f"<tr><td class='col-qty'>{r['الكميه المطلوبه']}</td><td>{r['اسم الصنف']}</td><td style='width:10%'></td></tr>" for _, r in edited.iterrows()])
            
            order_content = f"""
            <div class="header-box">
                <p class="name-txt">{selected_rep}</p>
                <p style="font-size:16px; margin:0;">وقت الطلب: {order_time}</p>
            </div>
            <table class="table-style">
                <thead><tr><th style="background:#eee;">العدد</th><th style="background:#eee;">الصنف</th><th style="background:#eee;">✓</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            """

            st.markdown(f"""
                <div class="print-main-wrapper">
                    <div class="order-copy">
                        <div class="copy-label">النسخة الأولى (للمستودع)</div>
                        {order_content}
                    </div>
                    <div style="border-top: 3px dashed #000; margin: 40px 0;"></div>
                    <div class="order-copy">
                        <div class="copy-label">النسخة الثانية (للإدارة)</div>
                        {order_content}
                    </div>
                </div>
                <button onclick="window.print()" class="print-button-real no-print">
                   🖨️ طباعة الطلب كاملاً (الحل النهائي للنقص)
                </button>
            """, unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
