import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة والتنسيق المزدوج الصارم ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الشاشة الافتراضي */
    .screen-info { color: white; font-size: 18px; text-align: right; }
    
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

    /* --- كود الطباعة الاحترافي للتقسيم الطولي --- */
    @media print {
        /* إخفاء شامل لكل شيء في المتصفح لمنع النصوص الزائدة */
        body * { visibility: hidden !important; }
        
        /* إظهار حاوية الطباعة فقط وتثبيتها في قمة الورقة */
        .print-main-wrapper, .print-main-wrapper * { 
            visibility: visible !important; 
        }

        .print-main-wrapper {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            background-color: white !important;
            direction: rtl !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* تنسيق النصف الواحد (يغطي نصف الورقة طولياً) */
        .print-half {
            width: 49% !important;
            padding: 10px !important;
            box-sizing: border-box !important;
            border-left: 1px dashed #eee; /* خط خفيف جداً لمكان القص */
        }

        /* إغلاق كل فجوات Streamlit */
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { 
            display: none !important; 
        }

        @page { size: A4 portrait; margin: 0; }

        /* تنسيق الرأس المصغر جداً */
        .header-box {
            border-bottom: 2px solid black;
            padding-bottom: 5px;
            margin-bottom: 10px;
            text-align: right;
        }
        /* تصغير الخطوط بناءً على طلبك (40% أصغر) */
        .name-txt { font-size: 20px !important; font-weight: bold; margin: 0; }
        .date-txt { font-size: 12px !important; margin: 0; color: #333; }

        /* تنسيق الجدول ليناسب نصف الورقة */
        .table-style { width: 100%; border-collapse: collapse; }
        .table-style th, .table-style td {
            border: 1px solid black !important;
            padding: 4px !important;
            text-align: center;
            font-size: 14px !important; /* خط صغير وواضح */
        }
        .th-bg { background-color: #f0f0f0 !important; font-size: 13px !important; }
        .col-qty { width: 15%; font-weight: bold; font-size: 18px !important; }
        .col-check { width: 12%; }
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

# --- نظام الدخول والاتصال (لا تغيير) ---
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

if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    show_full_logo()
    
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            if "بانتظار التصديق" in ws.col_values(4): st.session_state.orders.append(rep)

    if 'orders' in st.session_state:
        for name in st.session_state.orders:
            if st.button(f"📦 طلبية جديدة من: {name}", key=f"btn_{name}", use_container_width=True):
                st.session_state.active_rep = name
                st.rerun()

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
                st.success("تم!"); st.rerun()
            
            # محتوى النصف الواحد للطباعة
            rows_html = "".join([f"<tr><td class='col-qty'>{r['الكميه المطلوبه']}</td><td>{r['اسم الصنف']}</td><td class='col-check'></td></tr>" for _, r in edited.iterrows()])
            
            half_view = f"""
            <div class="header-box">
                <p class="name-txt">{selected_rep}</p>
                <p class="date-txt">وقت الطلب: {order_time}</p>
            </div>
            <table class="table-style">
                <thead><tr><th class="th-bg">العدد</th><th class="th-bg">الصنف</th><th class="th-bg">تأكيد</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            """

            # دمج النسختين يمين ويسار
            st.markdown(f"""
                <div class="print-main-wrapper">
                    <div class="print-half">{half_view}</div>
                    <div class="print-half">{half_view}</div>
                </div>
                <button onclick="window.print()" class="print-button-real no-print">
                   🖨️ طباعة (نسخة تحضير + نسخة فلترة)
                </button>
            """, unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
