import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# --- 2. نظام الدخول ---
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 دخول الإدارة")
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == "Hlb_Admin_2024":
            st.session_state.admin_logged_in = True
            st.rerun()
    st.stop()

# --- 3. الربط مع Google Sheets ---
def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
    creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    # استثناء الصفحات غير المطلوبة
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]

    st.title("🏭 لوحة تحكم الإدارة")

    # --- 4. فحص الطلبات الجديدة ---
    if st.button("🔔 فحص الطلبات الجديدة", use_container_width=True):
        st.session_state.new_orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            data = ws.get_all_values()
            for row in data:
                if len(row) > 3 and row[3] == "بانتظار التصديق":
                    st.session_state.new_orders.append(rep)
                    break
            time.sleep(0.1)

    if 'new_orders' in st.session_state and st.session_state.new_orders:
        for name in st.session_state.new_orders:
            col_txt, col_btn = st.columns([3, 1])
            col_txt.warning(f"📦 طلب جديد من المندوب: {name}")
            if col_btn.button(f"فتح {name}", key=f"open_{name}"):
                st.session_state.active_rep = name
                st.rerun()

    st.divider()

    # --- 5. عرض ومعالجة الطلبية (الزر الأساسي موجود هنا) ---
    active = st.session_state.get('active_rep', "-- اختر --")
    selected_rep = st.selectbox("اختر المندوب للمراجعة:", ["-- اختر --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            st.subheader(f"📑 طلبية المندوب: {selected_rep}")
            
            # عرض الجدول للتعديل (بدون خانات الأرقام الزائدة)
            edited_df = st.data_editor(
                pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']],
                column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "العدد"},
                hide_index=True, use_container_width=True
            )

            # الكبسة الأهم: إرسال (تصديق)
            if st.button("🚀 تصديق وحفظ الطلبية (إرسال)", type="primary", use_container_width=True):
                with st.spinner("جاري الحفظ..."):
                    for _, row in edited_df.iterrows():
                        # تحديث الحالة إلى "تم التصديق" في الشيت
                        ws.update_cell(int(row['row_no']), 4, "تم التصديق")
                    st.success("✅ تم حفظ الطلبية وتصديقها بنجاح!")
                    if 'active_rep' in st.session_state: del st.session_state.active_rep
                    time.sleep(1)
                    st.rerun()
            
            # زر الطباعة البسيط
            if st.button("🖨️ طباعة الورقة"):
                st.write("استخدم متصفحك للطباعة (Ctrl+P)")
        else:
            st.info("لا توجد أصناف بانتظار التصديق لهذا المندوب.")

# خروج
if st.sidebar.button("خروج"):
    st.session_state.clear()
    st.rerun()
