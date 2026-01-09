import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة والتنسيق الاحترافي للطباعة ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الشاشة الافتراضي للبرنامج */
    .screen-info { color: white; font-size: 18px; text-align: right; }
    .main-title-screen { font-size: 40px !important; font-weight: 900; color: white; text-align: center; margin: 10px 0; }
    
    /* تنسيق الزر ليفتح نافذة الطباعة مباشرة */
    .print-button-real {
        display: block; width: 100%; height: 75px; 
        background-color: #28a745; color: white !important; 
        border: 4px solid #ffffff; border-radius: 15px; cursor: pointer; 
        font-weight: bold; font-size: 30px; margin-top: 20px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
    }
    .print-button-real:hover { background-color: #218838; }

    /* --- إعدادات الطباعة (ما يظهر على الورق فقط) --- */
    @media print {
        /* إخفاء كل العناصر غير الضرورية والصور */
        header, footer, .no-print, [data-testid="stSidebar"], 
        .stButton, .stSelectbox, .stDataEditor, img, .stImage, .main-title-screen { 
            display: none !important; 
        }
        
        /* إظهار حاوية الطباعة وتوسيعها */
        .print-only { 
            display: block !important; 
            direction: rtl !important; 
            width: 100% !important;
            background-color: white !important;
        }

        @page { size: A4; margin: 1cm; }
        
        /* تنسيق اسم المندوب والتاريخ في الورقة */
        .header-print {
            text-align: right !important;
            border-bottom: 10px solid black !important;
            margin-bottom: 30px !important;
            padding-bottom: 10px !important;
        }
        .rep-name-print { font-size: 80px !important; font-weight: 900; line-height: 1.1; }
        .date-print { font-size: 35px !important; margin-top: 10px; }

        /* تنسيق الجدول ليكون عملاق وواضح */
        .main-table-print { 
            width: 100% !important; 
            border-collapse: collapse !important; 
            margin-top: 20px;
        }
        .main-table-print th, .main-table-print td { 
            border: 5px solid black !important; 
            padding: 20px !important; 
            text-align: center; 
        }
        .th-style { background-color: #f0f0f0 !important; font-size: 40px !important; font-weight: bold; }
        .td-qty { font-size: 100px !important; font-weight: 900 !important; width: 25%; } /* رقم الكمية ضخم */
        .td-item { font-size: 60px !important; font-weight: bold !important; text-align: right !important; width: 75%; }
    }
    </style>
""", unsafe_allow_html=True)

def show_full_logo():
    # وسم no-print يضمن عدم ظهور الصورة عند الطباعة حتى لو كانت ظاهرة على الشاشة
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
                # إنشاء محتوى الجدول للطباعة بأحجام كبيرة
                rows_html = "".join([
                    f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td></tr>" 
                    for _, r in edited.iterrows()
                ])
                
                # تخطيط الطباعة المخفي عن الشاشة والظاهر للبرنتر
                print_layout = f"""
                <div class="print-only" style="display:none;">
                    <div class="header-print">
                        <div class="rep-name-print">{selected_rep}</div>
                        <div class="date-print">وقت الطلب: {order_time}</div>
                    </div>
                    <table class="main-table-print">
                        <thead>
                            <tr>
                                <th class="th-style">الكمية</th>
                                <th class="th-style">الصنف</th>
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
