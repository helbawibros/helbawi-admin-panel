import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import time

# --- 1. إعدادات الصفحة وتنسيق الطباعة "الاسم يمين وبدون تاريخ" ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

st.markdown("""
    <style>
    @media print {
        /* إخفاء كل شيء غير الطلبية */
        header, footer, .no-print, [data-testid="stSidebar"], .stButton, .stSelectbox { 
            display: none !important; 
        }
        
        .print-only { 
            display: block !important; 
            direction: rtl !important; 
            width: 100% !important;
        }

        @page { size: A4; margin: 1cm; }
        body { background-color: white !important; color: black !important; }

        /* الاسم يمين بخط عملاق - وبدون أي تاريخ على اليسار */
        .header-print {
            display: flex !important;
            justify-content: flex-start !important; /* الاسم أقصى اليمين */
            border-bottom: 8px solid black !important;
            margin-bottom: 40px !important;
            padding-bottom: 10px !important;
            width: 100% !important;
        }
        
        .rep-name-big { 
            font-size: 70px !important; /* خط عملاق */
            font-weight: 900 !important; 
            text-align: right !important;
        }

        /* الجدول الضخم */
        .main-table-print { 
            width: 100% !important; 
            border-collapse: collapse !important; 
            border: 6px solid black !important; 
        }
        
        .main-table-print th, .main-table-print td { 
            border: 6px solid black !important; 
            padding: 20px !important; 
            font-weight: 900 !important; 
            color: black !important;
        }
        
        .th-style { background-color: #eee !important; font-size: 40px !important; text-align: center !important; }
        .td-qty { font-size: 60px !important; width: 15%; text-align: center !important; } /* العدد */
        .td-item { font-size: 55px !important; width: 60%; text-align: right !important; } /* الصنف */
        .td-check { width: 25%; } /* خانة التأكيس */
    }
    .print-only { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدخول والربط ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    st.title("🔐 دخول الإدارة")
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

    st.markdown('<div class="no-print"><h1>🏭 لوحة إدارة حلباوي</h1></div>', unsafe_allow_html=True)

    # فحص الطلبات
    if st.button("🔔 فحص الإشعارات", use_container_width=True):
        st.session_state.orders_list = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            if "بانتظار التصديق" in ws.col_values(4):
                st.session_state.orders_list.append(rep)
            time.sleep(0.1)

    if 'orders_list' in st.session_state:
        for name in st.session_state.orders_list:
            c1, c2 = st.columns([4, 1])
            c1.warning(f"📦 طلبية جديدة: {name}")
            if c2.button(f"فتح {name}", key=name):
                st.session_state.active_rep = name
                st.rerun()

    st.divider()

    # معالجة الطلب
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
            st.write(f"### طلبية {selected_rep}")
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                    column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "العدد"},
                                    hide_index=True, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 إرسال وتصديق", type="primary", use_container_width=True):
                    for _, r in edited.iterrows():
                        ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                    st.success("تم الحفظ!")
                    st.rerun()
            
            with col2:
                if st.button("🖨️ طباعة (A4)", use_container_width=True):
                    rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td class='td-check'></td></tr>" for _, r in edited.iterrows()])
                    
                    st.markdown(f"""
                        <div class="print-only">
                            <div class="header-print">
                                <div class="rep-name-big">المندوب: {selected_rep}</div>
                            </div>
                            <h1 style="text-align:center; font-size:55px; margin:20px 0; text-decoration: underline;">طلب بضاعة للمعمل</h1>
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
                            <div style="margin-top:100px; font-size:40px; font-weight:bold;">توقيع المستلم: .....................</div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

