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
    .main-title-screen { font-size: 35px !important; font-weight: 900; color: white; text-align: center; margin: 10px 0; }
    
    /* تنسيق الزر ليصبح حقيقي وقابل للتفاعل */
    .print-button-real {
        display: block; width: 100%; height: 65px; 
        background-color: #28a745; color: white !important; 
        border: 4px solid #ffffff; border-radius: 12px; 
        cursor: pointer; font-weight: bold; font-size: 26px;
        text-align: center; margin-top: 20px;
    }

    /* --- كود الطباعة الحاسم لإلغاء الفراغ العلوي --- */
    @media print {
        /* إخفاء كل شيء يخص الموقع */
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"],
        .stButton, .stSelectbox, .stDataEditor, img, .stImage, .main-title-screen { 
            display: none !important; 
            height: 0 !important;
            margin: 0 !important;
        }

        /* إجبار محتوى الطباعة على الالتصاق برأس الصفحة */
        .print-container {
            display: block !important;
            position: absolute !important;
            top: -120px !important; /* إزاحة سالبة لإلغاء فراغ المتصفح الأبيض */
            left: 0;
            width: 100% !important;
            direction: rtl !important;
            background-color: white !important;
        }

        @page { size: A4; margin: 0.5cm; }
        
        /* تنسيق الاسم والوقت (وسط) */
        .header-print {
            text-align: right !important;
            border-bottom: 3px solid black !important;
            margin-bottom: 15px !important;
            padding-bottom: 5px !important;
        }
        .rep-name-print { font-size: 35px !important; font-weight: bold; }
        .date-print { font-size: 18px !important; }

        /* تنسيق الجدول المرتب */
        .main-table-print { 
            width: 100% !important; 
            border-collapse: collapse !important; 
        }
        .main-table-print th, .main-table-print td { 
            border: 2px solid black !important; 
            padding: 8px !important; 
            text-align: center; 
        }
        .th-style { background-color: #f2f2f2 !important; font-size: 22px !important; }
        .td-qty { font-size: 32px !important; font-weight: bold; width: 15%; }
        .td-item { font-size: 24px !important; text-align: right !important; width: 70%; }
        .td-check { width: 15%; }
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
        # التأكد من وجود أسرار الاتصال بجوجل
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"خطأ في الاتصال بالقاعدة: {e}")
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
                # تجهيز محتوى الجدول
                rows_html = "".join([
                    f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td class='td-check'></td></tr>" 
                    for _, r in edited.iterrows()
                ])
                
                # حاوية الطباعة النهائية المحمية بـ JavaScript لفتح النافذة
                print_layout = f"""
                <div class="print-container">
                    <div class="header-print">
                        <div class="rep-name-print">{selected_rep}</div>
                        <div class="date-print">وقت الطلب: {order_time}</div>
                    </div>
                    <table class="main-table-print">
                        <thead>
                            <tr>
                                <th class="th-style">العدد</th>
                                <th class="th-style">الصنف</th>
                                <th class="th-style">تأكيد</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                
                <button onclick="window.print()" class="print-button-real no-print">
                   🖨️ طباعة الطلبية (Canon)
                </button>
                """
                st.markdown(print_layout, unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear()
    st.rerun()
