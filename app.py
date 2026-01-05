import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة وتنسيق الطباعة الحاد ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الطباعة - سيطبق فقط عند الضغط على زر الطباعة */
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"], .stButton { display: none !important; }
        .print-only { display: block !important; direction: rtl !important; }
        @page { size: A4; margin: 1cm; }
        body { background-color: white !important; color: black !important; font-family: 'Arial Black', sans-serif; }
        
        /* ترويسة الصفحة: المندوب يمين - التاريخ يسار */
        .header-container { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-bottom: 8px solid black; 
            padding-bottom: 15px; 
            margin-bottom: 40px; 
            width: 100%;
        }
        .rep-name-print { font-size: 55px !important; font-weight: 900; text-align: right; }
        .date-time-print { font-size: 30px !important; font-weight: bold; text-align: left; }

        /* الجدول الضخم */
        .print-table { width: 100%; border-collapse: collapse; border: 5px solid black; }
        .print-table th, .print-table td { 
            border: 5px solid black; 
            padding: 20px; 
            text-align: center; 
            font-weight: 900 !important; 
        }
        
        /* أحجام الخانات والخطوط (دوبل) */
        .col-num { width: 12%; font-size: 45px !important; } /* العدد صغير */
        .col-item { width: 63%; font-size: 50px !important; text-align: right; } /* الصنف ضخم */
        .col-check { width: 25%; font-size: 30px !important; } /* التأكيس */
        
        th { background-color: #ddd !important; font-size: 35px !important; }
    }
    .print-only { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. نظام الدخول والربط ---
ADMIN_PASSWORD = "Hlb_Admin_2024" 
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 تسجيل دخول الإدارة")
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else: st.error("خطأ")
    st.stop()

def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
    creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in EXCLUDE_SHEETS]

    st.markdown('<h1 class="no-print">🏭 لوحة الإدارة</h1>', unsafe_allow_html=True)

    # --- 3. نظام الإشعارات ---
    if st.button("🔔 فحص الطلبات الجديدة", use_container_width=True):
        st.session_state.notifs = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            data = ws.get_all_values()
            for row in data:
                if len(row) > 3 and row[3] == "بانتظار التصديق":
                    st.session_state.notifs.append({"name": rep, "time": row[0]})
                    break
            time.sleep(0.1)

    if 'notifs' in st.session_state:
        for n in st.session_state.notifs:
            c_n, c_g = st.columns([3, 1])
            c_n.warning(f"📦 {n['name']} أرسل طلبية بتاريخ: {n['time']}")
            if c_g.button(f"فتح {n['name']}", key=f"g_{n['name']}"):
                st.session_state.active_rep = n['name']
                st.rerun()

    st.divider()

    # --- 4. المعالجة والطباعة ---
    current_rep = st.session_state.get('active_rep', "-- اختر --")
    selected_rep = st.selectbox("المندوب:", ["-- اختر --"] + delegates, 
                                index=(delegates.index(current_rep)+1 if current_rep in delegates else 0))

    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], use_container_width=True)

            if st.button("🖨️ طباعة الطلبية (تنسيق A4 النهائي)", use_container_width=True):
                # جلب تاريخ الطلب من البيانات
                order_dt = pending.iloc[0]['التاريخ و الوقت']
                rows_html = "".join([f"<tr><td class='col-num'>{r['الكميه المطلوبه']}</td><td class='col-item'>{r['اسم الصنف']}</td><td class='col-check'></td></tr>" for _, r in pending.iterrows()])
                
                # بناء صفحة الطباعة
                st.markdown(f"""
                    <div class="print-only" dir="rtl">
                        <div class="header-container">
                            <div class="rep-name-print">المندوب: {selected_rep}</div>
                            <div class="date-time-print">التاريخ: {order_dt}</div>
                        </div>
                        <h1 style="text-align:center; font-size:50px; text-decoration:underline;">طلب بضاعة للمعمل</h1>
                        <table class="print-table">
                            <thead>
                                <tr>
                                    <th class="col-num">العدد</th>
                                    <th class="col-item">اسم الصنف</th>
                                    <th class="col-check">تأكيس (V)</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                        <div style="margin-top:70px; font-size:35px; font-weight:bold;">توقيع المستلم: ..........................</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
