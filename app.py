import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة والتنسيق ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الشاشة */
    .screen-info { color: white; font-size: 18px; text-align: right; }
    .main-title-screen { font-size: 40px !important; font-weight: 900; color: white; text-align: center; margin: 10px 0; }
    
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"], .stButton, .stSelectbox { display: none !important; }
        .print-only { display: block !important; direction: rtl !important; }
        @page { size: A4; margin: 1cm; }
        
        .header-print {
            text-align: right !important;
            border-bottom: 5px solid black !important;
            margin-bottom: 20px !important;
            padding-bottom: 10px !important;
            width: 100% !important;
        }
        .rep-name-print { font-size: 60px !important; font-weight: 900; line-height: 1.1; }
        .date-print { font-size: 25px !important; font-weight: bold; margin-top: 5px; }

        .main-table-print { width: 100% !important; border-collapse: collapse !important; border: 6px solid black !important; }
        .main-table-print th, .main-table-print td { border: 6px solid black !important; padding: 20px !important; font-weight: 900 !important; text-align: center; }
        .th-style { background-color: #eee !important; font-size: 35px !important; }
        .td-qty { font-size: 65px !important; width: 15%; }
        .td-item { font-size: 50px !important; width: 60%; text-align: right !important; }
        .td-check { width: 25%; }
    }
    </style>
""", unsafe_allow_html=True)

# دالة لعرض اللوغو بأمان لمنع الشاشة الحمراء
def show_full_logo():
    # حاولنا تغطية كل احتمالات كتابة الاسم (بمسافة أو بدون)
    possible_names = ["Logo.JPG", "Logo .JPG", "logo.jpg"]
    found = False
    for name in possible_names:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            found = True
            break
    if not found:
        st.info("⚠️ اللوغو غير موجود في المجلد، يرجى رفعه باسم Logo.JPG")

# --- 2. صفحة الدخول ---
if 'admin_logged_in' not in st.session_state: 
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    show_full_logo()  # اللوغو بعرض الشاشة قبل كلمة السر
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>دخول الإدارة</h1>", unsafe_allow_html=True)
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True
                st.rerun()
    st.stop()

# --- 3. الربط مع البيانات ---
def get_client():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error("خطأ في الربط مع جوجل: تأكد من ملف secrets")
        return None

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]

    # اللوغو بعرض الشاشة بعد الدخول
    show_full_logo()
    st.markdown('<div class="main-title-screen no-print">طلبيات المندوبين</div>', unsafe_allow_html=True)

    # فحص الإشعارات
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            if "بانتظار التصديق" in ws.col_values(4):
                st.session_state.orders.append(rep)

    if 'orders' in st.session_state:
        for name in st.session_state.orders:
            if st.button(f"📦 طلبية جديدة من: {name}", key=f"btn_{name}", use_container_width=True):
                st.session_state.active_rep = name
                st.rerun()

    st.divider()

    # معالجة الطلب
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
            st.markdown(f'<div class="screen-info">المندوب: {selected_rep}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="screen-info">التاريخ: {order_time}</div>', unsafe_allow_html=True)
            
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                    column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "العدد"}, 
                                    hide_index=True, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 تصديق وإرسال", type="primary", use_container_width=True):
                    for _, r in edited.iterrows():
                        ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                    st.success("تم!")
                    st.rerun()
            
            with c2:
                if st.button("🖨️ طباعة (طلب مبيعات)", use_container_width=True):
                    rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td class='td-check'></td></tr>" for _, r in edited.iterrows()])
                    st.markdown(f"""
                        <div class="print-only">
                            <div class="header-print">
                                <div class="rep-name-print">{selected_rep}</div>
                                <div class="date-print">تاريخ الطلب: {order_time}</div>
                            </div>
                            <h2 style="text-align:center; font-size:45px; margin:10px 0;">طلب مبيعات</h2>
                            <table class="main-table-print">
                                <thead>
                                    <tr>
                                        <th class="th-style">العدد</th>
                                        <th class="th-style">اسم الصنف</th>
                                        <th class="th-style">تأكيس</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear()
    st.rerun()

