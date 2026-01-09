import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة والتنسيق النهائي الموجه للطابعة ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الشاشة الافتراضي */
    .screen-info { color: white; font-size: 18px; text-align: right; }
    .main-title-screen { font-size: 30px !important; font-weight: 900; color: white; text-align: center; }
    
    /* تنسيق زر الطباعة */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: none; border-radius: 10px; cursor: pointer; 
        font-weight: bold; font-size: 24px; margin-top: 20px;
    }

    /* --- كود الطباعة الاحترافي --- */
    @media print {
        /* إخفاء كل شيء في الموقع تماماً */
        body * { visibility: hidden; }
        
        /* إظهار حاوية الطباعة فقط وإلغاء أي إزاحة */
        .print-container, .print-container * { visibility: visible; }
        
        .print-container {
            position: absolute;
            top: 0 !important;
            left: 0;
            width: 100%;
            margin: 0;
            padding: 0;
            direction: rtl !important;
        }

        /* إخفاء الصور والأزرار والجانبيات */
        header, footer, .no-print, [data-testid="stSidebar"], img, .stImage { 
            display: none !important; 
        }

        @page { 
            size: A4; 
            margin: 0.5cm; /* تقليل الهامش لاستغلال المساحة */
        }

        /* تنسيق الاسم والوقت في سطر واحد أو سطرين متقاربين */
        .header-section {
            text-align: right;
            border-bottom: 2px solid #000;
            margin-bottom: 15px;
            padding-bottom: 5px;
        }
        .rep-name { 
            font-size: 32px !important; 
            font-weight: bold; 
            margin: 0; 
        }
        .order-date { 
            font-size: 18px !important; 
            margin: 0;
        }

        /* تنسيق الجدول "الوسط" */
        .print-table {
            width: 100%;
            border-collapse: collapse;
        }
        .print-table th, .print-table td {
            border: 1px solid black;
            padding: 8px;
            text-align: center;
        }
        .print-table th { background-color: #f2f2f2; font-size: 20px; }
        .print-table td { font-size: 22px; }
        .col-qty { width: 15%; font-weight: bold; }
        .col-item { width: 70%; text-align: right; }
        .col-check { width: 15%; }
    }
    </style>
""", unsafe_allow_html=True)

def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    possible_names = ["Logo.JPG", "Logo .JPG", "logo.jpg"]
    found = False
    for name in possible_names:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            found = True
            break
    if not found:
        st.info("⚠️ يرجى التأكد من رفع صورة Logo.JPG")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 2. نظام الدخول ---
if 'admin_logged_in' not in st.session_state: 
    st.session_state.admin_logged_in = False

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

# --- 3. الاتصال بقاعدة البيانات ---
def get_client():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        return None

client = get_client()

if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]

    show_full_logo()
    st.markdown('<div class="main-title-screen no-print">طلبيات المندوبين</div>', unsafe_allow_html=True)

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
            st.markdown(f'<div class="screen-info no-print">المندوب: {selected_rep} | التاريخ: {order_time}</div>', unsafe_allow_html=True)
            
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
                # محتوى الجدول للطباعة
                rows_html = "".join([
                    f"<tr><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-item'>{r['اسم الصنف']}</td><td class='col-check'></td></tr>" 
                    for _, r in edited.iterrows()
                ])
                
                # بناء هيكل الطباعة الجديد والمحكم
                print_content = f"""
                <div class="print-container">
                    <div class="header-section">
                        <p class="rep-name">{selected_rep}</p>
                        <p class="order-date">وقت الطلب: {order_time}</p>
                    </div>
                    <table class="print-table">
                        <thead>
                            <tr>
                                <th style="width:15%">العدد</th>
                                <th style="width:70%">الصنف</th>
                                <th style="width:15%">تأكيد</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                
                <button onclick="window.print()" class="print-button-real no-print">
                   🖨️ طباعة الطلب
                </button>
                """
                st.markdown(print_content, unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear()
    st.rerun()
