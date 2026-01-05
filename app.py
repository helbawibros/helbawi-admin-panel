import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. إعدادات الصفحة وكلمة السر ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# CSS خاص لتنسيق الطباعة A4
st.markdown("""
    <style>
    @media print {
        .no-print { display: none !important; }
        .print-only { display: block !important; direction: rtl; }
        @page { size: A4; margin: 2cm; }
        body { background-color: white !important; }
    }
    .print-only { display: none; }
    .print-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }
    .print-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .print-table th, .print-table td { border: 1px solid black; padding: 12px; text-align: center; font-size: 18px; }
    .print-table th { background-color: #f2f2f2 !important; }
    .empty-cell { width: 100px; }
    </style>
""", unsafe_allow_html=True)

ADMIN_PASSWORD = "Hlb_Admin_2024" 

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 تسجيل دخول الإدارة")
    pwd = st.text_input("أدخل كلمة السر الخاصة بالإدارة", type="password")
    if st.button("دخول"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("كلمة السر غير صحيحة")
    st.stop()

# --- 2. إعدادات الربط ---
EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1", "Price List", "Data", "Customers"]

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        raw_json = st.secrets["gcp_service_account"]["json_data"].strip()
        info = json.loads(raw_json, strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except: return None

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates_pages = [name for name in all_worksheets if name not in EXCLUDE_SHEETS]

    st.markdown('<h1 class="no-print">🏭 لوحة تحكم الإدارة</h1>', unsafe_allow_html=True)

    # --- 3. الإشعارات ---
    st.markdown('<div class="no-print"><h3>🔔 إشعارات الطلبيات الجديدة</h3></div>', unsafe_allow_html=True)
    notification_found = False
    for rep in delegates_pages:
        try:
            ws = spreadsheet.worksheet(rep)
            status_col = ws.col_values(4) 
            p_count = status_col.count("بانتظار التصديق")
            if p_count > 0:
                st.warning(f"📢 المندوب **{rep}** لديه ({p_count}) أصناف بانتظار التصديق")
                notification_found = True
        except: continue
    
    if not notification_found:
        st.success("✅ لا توجد طلبات معلقة حالياً.")

    st.divider()

    # --- 4. معالجة الطلبية والطباعة ---
    selected_rep = st.selectbox("اختر المندوب للمراجعة والطباعة:", ["-- اختر مندوباً --"] + delegates_pages, key="rep_sel")
    
    if selected_rep != "-- اختر مندوباً --":
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                full_df = pd.DataFrame(data[1:], columns=data[0])
                full_df['row_no'] = range(2, len(full_df) + 2)
                pending_df = full_df[full_df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending_df.empty:
                    st.markdown(f"#### 🛠️ تعديل طلبية المندوب: {selected_rep}")
                    edited_df = st.data_editor(
                        pending_df[['row_no', 'التاريخ و الوقت', 'اسم الصنف', 'الكميه المطلوبه']],
                        column_config={
                            "row_no": None,
                            "التاريخ و الوقت": st.column_config.Column(disabled=True),
                            "اسم الصنف": st.column_config.TextColumn("الصنف"),
                            "الكميه المطلوبه": st.column_config.TextColumn("الكمية")
                        },
                        hide_index=True, use_container_width=True, key="admin_edit"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🚀 تصديق الطلبية (تحديث الإكسل)", use_container_width=True, type="primary"):
                            for index, row in edited_df.iterrows():
                                r_idx = int(row['row_no'])
                                worksheet.update_cell(r_idx, 2, row['اسم الصنف'])
                                worksheet.update_cell(r_idx, 3, row['الكميه المطلوبه'])
                                worksheet.update_cell(r_idx, 4, "تم التصديق")
                            st.success("✅ تم التصديق!")
                            st.rerun()
                    
                    with col2:
                        if st.button("🖨️ تحضير الفاتورة للطباعة", use_container_width=True):
                            st.session_state.show_print = True

                    # --- قسم الطباعة المخفي (يظهر عند الضغط أو عند الطباعة فقط) ---
                    table_rows = ""
                    for _, r in edited_df.iterrows():
                        table_rows += f"<tr><td>{r['اسم الصنف']}</td><td>{r['الكميه المطلوبه']}</td><td class='empty-cell'></td></tr>"
                    
                    now_str = datetime.now().strftime("%Y-%m-%d | %H:%M")
                    
                    st.markdown(f"""
                        <div class="print-only">
                            <div class="print-header">
                                <div style="font-size: 30px; font-weight: bold;">المندوب: {selected_rep}</div>
                                <div style="font-size: 18px; text-align: left;">التاريخ: {now_str}</div>
                            </div>
                            <h2 style="text-align: center; text-decoration: underline;">طلبية بضاعة للمعمل</h2>
                            <table class="print-table">
                                <thead>
                                    <tr>
                                        <th>اسم الصنف</th>
                                        <th>الكمية</th>
                                        <th>ملاحظات / استلام</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {table_rows}
                                </tbody>
                            </table>
                            <div style="margin-top: 50px; display: flex; justify-content: space-between;">
                                <div>توقيع المستلم: __________</div>
                                <div>توقيع الإدارة: __________</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    if st.session_state.get('show_print'):
                        st.info("الآن اضغط على Ctrl + P (أو Cmd + P) للطباعة")
                        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
                        st.session_state.show_print = False

                else:
                    st.info("لا توجد طلبات معلقة لهذا المندوب.")
            else:
                st.write("الصفحة فارغة.")
        except Exception as e:
            st.error(f"خطأ: {e}")

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.admin_logged_in = False
    st.rerun()
