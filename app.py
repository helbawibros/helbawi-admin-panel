import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة وتنسيق الطباعة الحرارية النهائي ---
st.set_page_config(page_title="إدارة حلباوي - حراري", layout="wide")

st.markdown("""
    <style>
    .screen-info { color: white; font-size: 18px; text-align: right; }
    
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

    /* --- كود الطباعة المخصص للطابعة الحرارية 80mm --- */
    @media print {
        body * { visibility: hidden !important; }
        
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            height: auto !important;
            background-color: white !important;
        }

        .print-main-wrapper, .print-main-wrapper * { 
            visibility: visible !important; 
            color: #000000 !important; 
            /* تسميك الخط ليكون Bold فاحم */
            font-weight: 950 !important;
            -webkit-text-stroke: 0.8px black;
        }

        .print-main-wrapper {
            position: absolute !important;
            top: -45px !important; /* سحب للأعلى لإلغاء الفراغ العلوي */
            left: 50% !important;
            transform: translateX(-50%) !important; /* التوسيط في نص الورقة */
            width: 76mm !important; 
            direction: rtl !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* إخفاء عناصر ستريمليت الزائدة */
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { 
            display: none !important; 
        }

        @page { 
            size: 80mm auto; 
            margin: 0 !important; 
        }

        .header-box {
            border-bottom: 3px solid #000 !important; 
            padding-bottom: 5px;
            margin-bottom: 8px;
            text-align: center;
        }

        .name-txt { 
            font-size: 30px !important; 
            margin: 0; 
        }
        
        .date-txt { 
            font-size: 16px !important; 
            margin: 5px 0; 
        }

        .table-style { 
            width: 100%; 
            border-collapse: collapse; 
            border: 3px solid #000 !important;
        }
        
        .table-style th, .table-style td {
            border: 2px solid #000 !important; 
            padding: 5px 2px !important;
            text-align: center;
            font-size: 22px !important; 
        }
        
        /* عمود العدد: Bold فاحم وبدون خلفية رمادية */
        .col-qty { 
            width: 25%; 
            font-size: 38px !important; 
            background-color: transparent !important;
            -webkit-text-stroke: 1.5px black;
        }

        .footer-space {
            height: 10px;
            margin-top: 10px;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدوال الأساسية ---

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

# --- 3. معالجة البيانات والطباعة ---

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
        if not st.session_state.orders:
            st.toast("لا توجد طلبيات جديدة حالياً")

    if 'orders' in st.session_state:
        for name in st.session_state.orders:
            if st.button(f"📦 طلبية جديدة من: {name}", key=f"btn_{name}", use_container_width=True):
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
                st.success("تم!"); st.rerun()
            
            # بناء صفوف الجدول للطباعة
            rows_html = "".join([f"<tr><td class='col-qty'>{r['الكميه المطلوبه']}</td><td style='text-align:right;'>{r['اسم الصنف']}</td></tr>" for _, r in edited.iterrows()])
            
            # الحاوية النهائية المخصصة للـ 80mm
            thermal_view = f"""
            <div class="print-main-wrapper">
                <div class="header-box">
                    <p class="name-txt">طلب: {selected_rep}</p>
                    <p class="date-txt">{order_time}</p>
                </div>
                <table class="table-style">
                    <thead>
                        <tr>
                            <th style="width:25%">العدد</th>
                            <th>الصنف</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
                <div class="footer-space"></div>
                <p style="text-align:center; font-size:16px; font-weight:bold;">*** نهاية الطلب ***</p>
            </div>
            """

            st.markdown(thermal_view, unsafe_allow_html=True)
            
            st.markdown("""
                <button onclick="window.print()" class="print-button-real no-print">
                   🖨️ طباعة الفاتورة (Fix 80mm)
                </button>
            """, unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
