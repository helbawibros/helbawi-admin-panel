import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة وتنسيق الخط العملاق ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    /* التنسيق على الشاشة */
    .screen-date { color: #ff4b4b; font-size: 30px; font-weight: bold; margin-bottom: 10px; text-align: right; }
    .rep-title-screen { font-size: 45px !important; font-weight: 900; color: #1E1E1E; text-align: right; margin-top: -20px; }
    
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"], .stButton, .stSelectbox { display: none !important; }
        .print-only { display: block !important; direction: rtl !important; }
        @page { size: A4; margin: 0.5cm; }
        
        /* ترويسة الطباعة: الاسم يمين - التاريخ يسار */
        .header-print {
            display: flex !important;
            justify-content: space-between !important;
            align-items: baseline !important;
            border-bottom: 10px solid black !important;
            margin-bottom: 30px !important;
            padding-bottom: 10px !important;
            width: 100% !important;
        }
        .rep-name-print { font-size: 70px !important; font-weight: 900; text-align: right; }
        .date-print { font-size: 30px !important; font-weight: bold; text-align: left; }

        /* الجدول ضخم جداً وعريض */
        .main-table-print { width: 100% !important; border-collapse: collapse !important; border: 8px solid black !important; }
        .main-table-print th, .main-table-print td { border: 8px solid black !important; padding: 20px !important; font-weight: 900 !important; }
        .th-style { background-color: #ddd !important; font-size: 40px !important; }
        .td-qty { font-size: 65px !important; width: 15%; text-align: center !important; }
        .td-item { font-size: 55px !important; width: 60%; text-align: right !important; }
        .td-check { width: 25%; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدخول والربط ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == "Hlb_Admin_2024":
            st.session_state.admin_logged_in = True
            st.rerun()
    st.stop()

def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
    creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]

    # --- 3. الإشعارات ---
    if st.button("🔔 فحص الإشعارات", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            data = ws.get_all_values()
            for row in data:
                if len(row) > 3 and row[3] == "بانتظار التصديق":
                    st.session_state.orders.append({"name": rep, "time": row[0]})
                    break

    if 'orders' in st.session_state:
        for order in st.session_state.orders:
            if st.button(f"📦 {order['name']} - {order['time']}", key=order['name']):
                st.session_state.active_rep = order['name']
                st.rerun()

    st.divider()

    # --- 4. العرض الصافي ---
    active = st.session_state.get('active_rep', "-- اختر --")
    selected_rep = st.selectbox("المندوب:", ["-- اختر --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            order_time = pending.iloc[0]['التاريخ و الوقت']
            # الاسم والتاريخ فوق بعض على الشاشة للتوضيح
            st.markdown(f'<div class="screen-date">📅 التاريخ: {order_time}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rep-title-screen">{selected_rep}</div>', unsafe_allow_html=True)
            
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                    column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "العدد"}, 
                                    hide_index=True, use_container_width=True)

            if st.button("🚀 تصديق وإرسال للإكسل", type="primary", use_container_width=True):
                for _, r in edited.iterrows():
                    ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                st.success("تم الحفظ!")
                st.rerun()
            
            if st.button("🖨️ طباعة الطلبية (خط عملاق)", use_container_width=True):
                rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td class='td-check'></td></tr>" for _, r in edited.iterrows()])
                st.markdown(f"""
                    <div class="print-only">
                        <div class="header-print">
                            <div class="rep-name-print">{selected_rep}</div>
                            <div class="date-print">{order_time}</div>
                        </div>
                        <table class="main-table-print">
                            <thead>
                                <tr>
                                    <th class="th-style">العدد</th>
                                    <th class="th-style">الصنف</th>
                                    <th class="th-style">تأكيس</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

# خروج
if st.sidebar.button("خروج"):
    st.session_state.clear()
    st.rerun()
