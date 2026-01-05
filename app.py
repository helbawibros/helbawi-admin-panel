import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import time

# --- 1. إعدادات الصفحة والتنسيق الاحترافي ---
st.set_page_config(page_title="إدارة حلباوي", layout="wide")

st.markdown("""
    <style>
    /* التنسيق على الشاشة - خطوط عادية ولون أبيض */
    .screen-info { color: white; font-size: 18px; text-align: right; margin-bottom: 5px; }
    .main-title-screen { font-size: 40px !important; font-weight: 900; color: white; text-align: center; margin-bottom: 30px; border-bottom: 2px solid white; padding-bottom: 10px; }
    
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"], .stButton, .stSelectbox { display: none !important; }
        .print-only { display: block !important; direction: rtl !important; }
        @page { size: A4; margin: 0.5cm; }
        
        /* ترويسة الطباعة: اللوغو والاسم يمين - التاريخ يسار */
        .header-print {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            border-bottom: 10px solid black !important;
            margin-bottom: 20px !important;
            padding-bottom: 10px !important;
            width: 100% !important;
        }
        .logo-box { width: 120px; height: auto; }
        .rep-name-print { font-size: 70px !important; font-weight: 900; text-align: right; flex-grow: 1; margin-right: 20px; }
        .date-print { font-size: 25px !important; font-weight: bold; text-align: left; }

        /* الجدول ضخم جداً للمحضرين (كبار السن) */
        .main-table-print { width: 100% !important; border-collapse: collapse !important; border: 8px solid black !important; }
        .main-table-print th, .main-table-print td { border: 8px solid black !important; padding: 25px !important; font-weight: 900 !important; }
        .th-style { background-color: #ddd !important; font-size: 40px !important; }
        .td-qty { font-size: 75px !important; width: 15%; text-align: center !important; } /* العدد ضخم جداً */
        .td-item { font-size: 60px !important; width: 60%; text-align: right !important; } /* الصنف ضخم جداً */
        .td-check { width: 25%; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدخول والربط ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    pwd = st.text_input("كلمة السر الإدارية", type="password")
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

    # العنوان الرئيسي على الشاشة
    st.markdown('<div class="main-title-screen no-print">طلبيات المندوبين</div>', unsafe_allow_html=True)

    # --- 3. فحص الإشعارات ---
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
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
            if st.button(f"📦 {order['name']} (وصلت: {order['time']})", key=order['name']):
                st.session_state.active_rep = order['name']
                st.rerun()

    st.divider()

    # --- 4. عرض ومعالجة الطلبية ---
    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("اختر من القائمة:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            order_time = pending.iloc[0]['التاريخ و الوقت']
            
            # معلومات المندوب على الشاشة (لون أبيض وخط عادي)
            st.markdown(f'<div class="screen-info">المندوب: {selected_rep}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="screen-info">وقت الطلب: {order_time}</div>', unsafe_allow_html=True)
            
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                    column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "العدد"}, 
                                    hide_index=True, use_container_width=True)

            if st.button("🚀 تصديق وإرسال نهائي", type="primary", use_container_width=True):
                for _, r in edited.iterrows():
                    ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                st.success("تم تصديق الطلب!")
                st.rerun()
            
            if st.button("🖨️ طباعة الطلب للمعمل", use_container_width=True):
                rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td class='td-check'></td></tr>" for _, r in edited.iterrows()])
                
                # تصميم الطباعة النهائي (لوغو + اسم ضخم يمين + تاريخ يسار)
                st.markdown(f"""
                    <div class="print-only">
                        <div class="header-print">
                            <img src="https://cdn-icons-png.flaticon.com/512/4080/4080032.png" class="logo-box"> <div class="rep-name-print">{selected_rep}</div>
                            <div class="date-print">{order_time}</div>
                        </div>
                        <h2 style="text-align:center; font-size:40px; margin-top:0;">طلبية معمل</h2>
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
                        <div style="margin-top:80px; font-size:35px; font-weight:bold;">توقيع المستلم: .....................</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

# خروج
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.clear()
    st.rerun()
