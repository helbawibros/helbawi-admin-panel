import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 1. إعدادات الصفحة والتنسيق المزدوج فائق الوضوح ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    .screen-info { color: white; font-size: 18px; text-align: right; }
    
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

    /* --- كود الطباعة فائق الوضوح للأرقام والحدود --- */
    @media print {
        body * { visibility: hidden !important; }
        
        .print-main-wrapper, .print-main-wrapper * { 
            visibility: visible !important; 
            color: #000000 !important; /* أسود فاحم */
            -webkit-print-color-adjust: exact;
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

        .print-half {
            width: 49% !important;
            padding: 15px !important;
            box-sizing: border-box !important;
            border-left: 2px dashed #000 !important; /* خط القص أوضح */
        }

        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { 
            display: none !important; 
        }

        @page { size: A4 portrait; margin: 0; }

        .header-box {
            border-bottom: 4px solid #000 !important; /* خط عريض جداً تحت الاسم */
            padding-bottom: 5px;
            margin-bottom: 15px;
            text-align: right;
        }

        .name-txt { 
            font-size: 24px !important; 
            font-weight: 900 !important; 
            margin: 0; 
        }
        
        .date-txt { 
            font-size: 14px !important; 
            font-weight: 900 !important; 
            margin: 0; 
        }

        .table-style { 
            width: 100%; 
            border-collapse: collapse; 
            border: 3px solid #000 !important; /* حدود الجدول عريضة */
        }
        
        /* تنسيق الأرقام والكلمات ليكون عريض جداً */
        .table-style th, .table-style td {
            border: 2px solid #000 !important; 
            padding: 8px !important;
            text-align: center;
            font-size: 17px !important;
            font-weight: 900 !important; /* أقصى سمك للخط */
            /* تقنية لتقوية ظهور الرقم الباهت */
            text-shadow: 0.5px 0px 0px #000; 
        }
        
        .th-bg { 
            background-color: #cccccc !important; 
            font-weight: 900 !important; 
        }
        
        /* عمود العدد: تكبير إضافي للأرقام لضمان وضوحها */
        .col-qty { 
            width: 20%; 
            font-size: 24px !important; 
            font-weight: 900 !important; 
            color: #000000 !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- نظام الدخول والاتصال وقاعدة البيانات ---
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
    
    # واجهة الشاشة
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    possible_names = ["Logo.JPG", "Logo .JPG", "logo.jpg"]
    for name in possible_names:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            break
    st.markdown('</div>', unsafe_allow_html=True)

    # بقية كود Streamlit
    if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
    if not st.session_state.admin_logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h1 style='text-align: center;'>دخول الإدارة</h1>", unsafe_allow_html=True)
            pwd = st.text_input("كلمة السر", type="password")
            if st.button("دخول", use_container_width=True):
                if pwd == "Hlb_Admin_2024":
                    st.session_state.admin_logged_in = True
                    st.rerun()
        st.stop()

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
            
            # محتوى النصف الواحد للطباعة مع Bold فائق
            rows_html = "".join([f"<tr><td class='col-qty'>{r['الكميه المطلوبه']}</td><td style='text-align:right;'>{r['اسم الصنف']}</td><td style='width:12%'></td></tr>" for _, r in edited.iterrows()])
            
            half_view = f"""
            <div class="header-box">
                <p class="name-txt">{selected_rep}</p>
                <p class="date-txt">وقت الطلب: {order_time}</p>
            </div>
            <table class="table-style">
                <thead><tr><th class="th-bg">العدد</th><th class="th-bg">الصنف</th><th class="th-bg">✓</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            """

            st.markdown(f"""
                <div class="print-main-wrapper">
                    <div class="print-half">{half_view}</div>
                    <div class="print-half">{half_view}</div>
                </div>
                <button onclick="window.print()" class="print-button-real no-print">
                   🖨️ طباعة الطلب (أرقام واضحة جداً)
                </button>
            """, unsafe_allow_html=True)
