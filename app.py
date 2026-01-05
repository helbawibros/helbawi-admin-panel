import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة وتنسيق الطباعة ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

st.markdown("""
    <style>
    /* التنسيق على الشاشة */
    .screen-date { color: #ff4b4b; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
    
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"], .stButton, .stSelectbox { display: none !important; }
        .print-only { display: block !important; direction: rtl !important; }
        @page { size: A4; margin: 1cm; }
        body { background-color: white !important; color: black !important; font-family: 'Arial', sans-serif; }
        
        .header-print {
            display: flex !important;
            justify-content: space-between !important;
            align-items: baseline !important;
            border-bottom: 8px solid black !important;
            margin-bottom: 30px !important;
            width: 100% !important;
        }
        .rep-name-big { font-size: 55px !important; font-weight: 900; text-align: right; }
        .date-time-left { font-size: 28px !important; font-weight: bold; text-align: left; }

        .main-table-print { width: 100% !important; border-collapse: collapse !important; border: 6px solid black !important; }
        .main-table-print th, .main-table-print td { border: 6px solid black !important; padding: 15px !important; font-weight: 900 !important; }
        .td-qty { font-size: 50px !important; width: 15%; text-align: center !important; }
        .td-item { font-size: 45px !important; width: 60%; text-align: right !important; }
    }
    .print-only { display: none; }
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
    if st.button("🔔 فحص الإشعارات"):
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

    # --- 4. العرض (هنا التعديل المهم) ---
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
            # إظهار التاريخ على الشاشة فوراً
            order_time = pending.iloc[0]['التاريخ و الوقت']
            st.markdown(f'<div class="screen-date">📅 تاريخ الطلب: {order_time}</div>', unsafe_allow_html=True)
            st.header(f"طلبية المندوب: {selected_rep}")
            
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                    column_config={"row_no": None}, hide_index=True)

            if st.button("🚀 تصديق وإرسال", type="primary", use_container_width=True):
                for _, r in edited.iterrows():
                    ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                st.success("تم!")
                st.rerun()
            
            if st.button("🖨️ طباعة الطلبية", use_container_width=True):
                rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td></td></tr>" for _, r in edited.iterrows()])
                st.markdown(f"""
                    <div class="print-only">
                        <div class="header-print">
                            <div class="rep-name-big">المندوب: {selected_rep}</div>
                            <div class="date-time-left">{order_time}</div>
                        </div>
                        <h1 style="text-align:center;">طلب بضاعة للمعمل</h1>
                        <table class="main-table-print">
                            <thead><tr><th>العدد</th><th>الصنف</th><th>تأكيس</th></tr></thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

# خروج
if st.sidebar.button("خروج"):
    st.session_state.clear()
    st.rerun()
