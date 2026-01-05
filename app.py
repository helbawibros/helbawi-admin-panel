import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة والهوية ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# CSS للطباعة وتنسيق A4
st.markdown("""
    <style>
    @media print {
        .no-print { display: none !important; }
        .print-only { display: block !important; direction: rtl; }
        @page { size: A4; margin: 1.5cm; }
        body { background-color: white !important; color: black !important; }
    }
    .print-only { display: none; }
    .print-header { display: flex; justify-content: space-between; border-bottom: 3px solid black; padding-bottom: 10px; }
    .print-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .print-table th, .print-table td { border: 1px solid black; padding: 10px; text-align: center; font-size: 18px; }
    .print-table th { background-color: #eee !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. نظام الدخول ---
ADMIN_PASSWORD = "Hlb_Admin_2024" 
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 تسجيل دخول الإدارة")
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else: st.error("خطأ في كلمة السر")
    st.stop()

# --- 3. الربط مع Google Sheets ---
EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except: return None

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # حل مشكلة Quota: فحص أسماء الصفحات فقط أولاً
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates = [n for n in all_worksheets if n not in EXCLUDE_SHEETS]

    st.markdown('<h1 class="no-print">🏭 لوحة تحكم الإدارة</h1>', unsafe_allow_html=True)

    # زر لتحديث الإشعارات يدوياً لتجنب ضغط الـ API
    if st.button("🔔 فحص الطلبات الجديدة"):
        notifications = []
        with st.spinner("جاري الفحص..."):
            for rep in delegates:
                try:
                    ws = spreadsheet.worksheet(rep)
                    # نجلب فقط آخر 20 سطر لتوفير البيانات والوقت
                    data = ws.get_all_values()
                    count = sum(1 for row in data if len(row) > 3 and row[3] == "بانتظار التصديق")
                    if count > 0:
                        notifications.append(f"📢 **{rep}**: لديه {count} أصناف جديدة")
                    time.sleep(0.5) # تأخير بسيط لتجنب الحظر
                except: continue
        
        if notifications:
            for n in notifications: st.warning(n)
        else: st.success("لا توجد طلبات معلقة.")

    st.divider()

    # --- اختيار المندوب والمعالجة ---
    selected_rep = st.selectbox("اختر المندوب للمراجعة والطباعة:", ["-- اختر --"] + delegates)
    
    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['row_no'] = range(2, len(df) + 2)
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
            
            if not pending.empty:
                st.write(f"### طلبية قيد الانتظار: {selected_rep}")
                edited_df = st.data_editor(
                    pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']],
                    column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "الكمية"},
                    hide_index=True, use_container_width=True
                )

                col_save, col_print = st.columns(2)
                
                with col_save:
                    if st.button("🚀 تصديق وحفظ", use_container_width=True, type="primary"):
                        for _, row in edited_df.iterrows():
                            r_idx = int(row['row_no'])
                            ws.update_cell(r_idx, 2, row['اسم الصنف'])
                            ws.update_cell(r_idx, 3, row['الكميه المطلوبه'])
                            ws.update_cell(r_idx, 4, "تم التصديق")
                        st.success("تم الحفظ بنجاح!")
                        st.rerun()

                with col_print:
                    if st.button("🖨️ طباعة الطلبية", use_container_width=True):
                        # إنشاء جدول الطباعة
                        rows_html = "".join([f"<tr><td>{r['اسم الصنف']}</td><td>{r['الكميه المطلوبه']}</td><td></td></tr>" for _, r in edited_df.iterrows()])
                        now = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        st.markdown(f"""
                            <div class="print-only">
                                <div class="print-header">
                                    <div style="font-size: 28px; font-weight: bold;">المندوب: {selected_rep}</div>
                                    <div style="font-size: 18px;">التاريخ: {now}</div>
                                </div>
                                <h2 style="text-align:center; margin-top:20px;">طلبية بضاعة للمعمل</h2>
                                <table class="print-table">
                                    <thead>
                                        <tr><th>الصنف</th><th>الكمية</th><th>ملاحظات</th></tr>
                                    </thead>
                                    <tbody>{rows_html}</tbody>
                                </table>
                                <div style="margin-top: 50px;">توقيع الإدارة: ..........................</div>
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
            else:
                st.info("لا توجد طلبات بانتظار التصديق.")

# خروج
if st.sidebar.button("تسجيل خروج"):
    st.session_state.admin_logged_in = False
    st.rerun()
