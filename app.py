import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة والتنسيق ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# تنسيق CSS احترافي للطباعة A4 وللواجهة
st.markdown("""
    <style>
    @media print {
        .no-print { display: none !important; }
        .print-only { display: block !important; direction: rtl; text-align: right; }
        @page { size: A4; margin: 1.5cm; }
        body { background-color: white !important; color: black !important; font-family: 'Arial', sans-serif; }
        .print-header { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 3px solid black; padding-bottom: 5px; margin-bottom: 20px; }
        .print-table { width: 100%; border-collapse: collapse; }
        .print-table th, .print-table td { border: 1px solid black; padding: 12px; text-align: center; font-size: 20px; }
        .print-table th { background-color: #f0f0f0 !important; }
        .check-box-cell { width: 80px; } /* خانة التأكيس */
    }
    .print-only { display: none; }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. نظام الدخول ---
ADMIN_PASSWORD = "Hlb_Admin_2024" 
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 تسجيل دخول الإدارة")
    pwd = st.text_input("أدخل كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else: st.error("كلمة السر غير صحيحة")
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
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates = [n for n in all_worksheets if n not in EXCLUDE_SHEETS]

    st.markdown('<h1 class="no-print">🏭 لوحة تحكم الإدارة</h1>', unsafe_allow_html=True)

    # فحص الإشعارات (يدوياً لتجنب ضغط الـ API)
    if st.button("🔔 فحص الإشعارات (طلبات جديدة)"):
        notifications = []
        with st.spinner("جاري فحص جميع الصفحات..."):
            for rep in delegates:
                try:
                    ws = spreadsheet.worksheet(rep)
                    all_data = ws.get_all_values()
                    count = sum(1 for row in all_data if len(row) > 3 and row[3] == "بانتظار التصديق")
                    if count > 0:
                        notifications.append(f"📦 المندوب **{rep}**: لديه {count} أصناف جديدة")
                    time.sleep(0.3) 
                except: continue
        
        if notifications:
            for n in notifications: st.warning(n)
        else: st.success("لا توجد طلبات جديدة حالياً.")

    st.divider()

    # --- اختيار المندوب والمعالجة ---
    selected_rep = st.selectbox("اختر المندوب لمراجعة طلبيته:", ["-- اختر --"] + delegates)
    
    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df['row_no'] = range(2, len(df) + 2)
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
            
            if not pending.empty:
                st.write(f"### طلبية قيد المراجعة: {selected_rep}")
                edited_df = st.data_editor(
                    pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']],
                    column_config={
                        "row_no": None, 
                        "اسم الصنف": st.column_config.TextColumn("الصنف"),
                        "الكميه المطلوبه": st.column_config.TextColumn("العدد")
                    },
                    hide_index=True, use_container_width=True
                )

                col_save, col_print = st.columns(2)
                
                with col_save:
                    if st.button("🚀 تصديق الطلبية (حفظ)", type="primary"):
                        for _, row in edited_df.iterrows():
                            r_idx = int(row['row_no'])
                            ws.update_cell(r_idx, 2, row['اسم الصنف'])
                            ws.update_cell(r_idx, 3, row['الكميه المطلوبه'])
                            ws.update_cell(r_idx, 4, "تم التصديق")
                        st.success("✅ تم تحديث البيانات في الإكسل وتصديق الطلبية!")
                        time.sleep(1)
                        st.rerun()

                with col_print:
                    if st.button("🖨️ طباعة الطلبية (A4)"):
                        # تجهيز بيانات الجدول للطباعة
                        rows_html = ""
                        for _, r in edited_df.iterrows():
                            rows_html += f"<tr><td>{r['اسم الصنف']}</td><td>{r['الكميه المطلوبه']}</td><td class='check-box-cell'></td></tr>"
                        
                        now_str = datetime.now().strftime("%Y-%m-%d | %H:%M")
                        
                        # قالب الطباعة
                        st.markdown(f"""
                            <div class="print-only">
                                <div class="print-header">
                                    <div style="font-size: 32px; font-weight: bold;">المندوب: {selected_rep}</div>
                                    <div style="font-size: 20px; font-weight: bold;">{now_str}</div>
                                </div>
                                <h2 style="text-align: center; text-decoration: underline; margin: 20px 0;">طلبية بضاعة للمعمل</h2>
                                <table class="print-table">
                                    <thead>
                                        <tr>
                                            <th>الصنف</th>
                                            <th>العدد</th>
                                            <th>تأكيس (V)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows_html}
                                    </tbody>
                                </table>
                                <div style="margin-top: 40px; font-size: 18px;">ملاحظات: .....................................................................................</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # أمر الطباعة
                        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
            else:
                st.info(f"المندوب {selected_rep} ليس لديه طلبات بانتظار التصديق.")

# تسجيل الخروج
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.admin_logged_in = False
    st.rerun()
