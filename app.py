import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة والتنسيق الاحترافي ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

st.markdown("""
    <style>
    @media print {
        .no-print { display: none !important; }
        .print-only { display: block !important; direction: rtl; text-align: right; }
        @page { size: A4; margin: 1cm; }
        body { background-color: white !important; color: black !important; font-family: 'Arial', sans-serif; }
        
        /* ترويسة الصفحة */
        .print-header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 4px solid black; padding-bottom: 10px; margin-bottom: 30px; }
        .rep-name { font-size: 45px !important; font-weight: bold; }
        .date-time { font-size: 25px !important; }

        /* الجدول العريض */
        .print-table { width: 100%; border-collapse: collapse; border: 3px solid black; }
        .print-table th, .print-table td { border: 3px solid black; padding: 15px; text-align: center; font-size: 35px !important; font-weight: bold; }
        .print-table th { background-color: #e0e0e0 !important; }
        
        /* أحجام الخانات */
        .col-qty { width: 15%; } /* خانة العدد صغيرة */
        .col-item { width: 60%; } /* الصنف وسط */
        .col-check { width: 25%; } /* خانة التأكيس */
    }
    .print-only { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدخول والربط ---
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

EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]

def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
    creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in EXCLUDE_SHEETS]

    st.markdown('<h1 class="no-print">🏭 إدارة طلبيات حلباوي</h1>', unsafe_allow_html=True)

    # --- 3. نظام الإشعارات مع زر الانتقال السريع ---
    if st.button("🔔 فحص الطلبات الجديدة"):
        found = False
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            if "بانتظار التصديق" in ws.col_values(4):
                st.warning(f"📦 مندوب لديه طلبية: **{rep}**")
                if st.button(f"👈 اضغط هنا لمعالجة طلب {rep}", key=f"btn_{rep}"):
                    st.session_state.selected_rep_auto = rep
                    st.rerun()
                found = True
            time.sleep(0.2)
        if not found: st.success("لا يوجد طلبات حالياً.")

    st.divider()

    # اختيار المندوب
    default_index = 0
    if 'selected_rep_auto' in st.session_state:
        if st.session_state.selected_rep_auto in delegates:
            default_index = delegates.index(st.session_state.selected_rep_auto) + 1
            del st.session_state.selected_rep_auto

    selected_rep = st.selectbox("اختر المندوب:", ["-- اختر --"] + delegates, index=default_index)

    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            st.write(f"### تعديل طلبية: {selected_rep}")
            edited_df = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                      column_config={"row_no": None}, hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 حفظ وتصديق", type="primary", use_container_width=True):
                    for _, r in edited_df.iterrows():
                        idx = int(r['row_no'])
                        ws.update_cell(idx, 2, r['اسم الصنف'])
                        ws.update_cell(idx, 3, r['الكميه المطلوبه'])
                        ws.update_cell(idx, 4, "تم التصديق")
                    st.success("تم!")
                    st.rerun()
            
            with c2:
                if st.button("🖨️ طباعة الفاتورة A4", use_container_width=True):
                    now = datetime.now().strftime("%Y-%m-%d | %H:%M")
                    rows_html = "".join([f"<tr><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-item'>{r['اسم الصنف']}</td><td class='col-check'></td></tr>" for _, r in edited_df.iterrows()])
                    
                    st.markdown(f"""
                        <div class="print-only">
                            <div class="print-header">
                                <div class="rep-name">المندوب: {selected_rep}</div>
                                <div class="date-time">التاريخ: {now}</div>
                            </div>
                            <h1 style="text-align:center; font-size:40px;">طلبية بضاعة للمعمل</h1>
                            <table class="print-table">
                                <thead>
                                    <tr>
                                        <th class="col-qty">العدد</th>
                                        <th class="col-item">الصنف</th>
                                        <th class="col-check">تأكيس (V)</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                            <div style="margin-top:50px; font-size:25px; font-weight:bold;">توقيع الإدارة: ..........................</div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
        else:
            st.info("لا يوجد طلبات معلقة.")

# تسجيل خروج
if st.sidebar.button("خروج"):
    st.session_state.admin_logged_in = False
    st.rerun()
