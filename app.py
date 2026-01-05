import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# --- 1. إعدادات الصفحة وكلمة السر ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# كلمة سر الأدمن (يمكنك تغييرها)
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

# --- 2. إعدادات الربط والقوائم المستثناة ---
# أضفت "الأسعار" و "البيانات" و "الزبائن" وغيرها لكي لا تظهر في قائمة المناديب
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
    
    # قائمة المندوبين الحقيقية فقط
    delegates_pages = [name for name in all_worksheets if name not in EXCLUDE_SHEETS]

    st.title("🏭 لوحة تحكم الإدارة - شركة حلباوي")

    # --- 3. نظام الإشعارات (Notification Hub) ---
    st.markdown("### 🔔 إشعارات الطلبيات الجديدة")
    notification_found = False
    
    with st.spinner("جاري فحص الطلبات الجديدة لدى جميع المندوبين..."):
        for rep in delegates_pages:
            try:
                ws = spreadsheet.worksheet(rep)
                # جلب عمود الحالة فقط (العمود الرابع) لتسريع الفحص
                status_col = ws.col_values(4) 
                pending_count = status_col.count("بانتظار التصديق")
                
                if pending_count > 0:
                    st.warning(f"📢 المندوب **{rep}** أرسل طلبية جديدة ({pending_count} أصناف بانتظار التصديق)")
                    notification_found = True
            except:
                continue
    
    if not notification_found:
        st.success("✅ لا توجد طلبات معلقة حالياً لدى جميع المندوبين.")

    st.divider()

    # --- 4. معالجة طلبية مندوب محدد ---
    st.subheader("🛠️ معالجة طلبية مندوب")
    selected_rep = st.selectbox("اختر المندوب للمراجعة والتصديق:", ["-- اختر مندوباً --"] + delegates_pages)
    
    if selected_rep != "-- اختر مندوباً --":
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                full_df = pd.DataFrame(data[1:], columns=data[0])
                full_df['row_no'] = range(2, len(full_df) + 2)
                
                # تصفية الطلبات المعلقة
                pending_mask = full_df['الحالة'] == "بانتظار التصديق"
                pending_df = full_df[pending_mask].copy()
                
                if not pending_df.empty:
                    st.info(f"تعديل وتصديق طلبية: {selected_rep}")
                    
                    edited_df = st.data_editor(
                        pending_df[['row_no', 'التاريخ و الوقت', 'اسم الصنف', 'الكميه المطلوبه']],
                        column_config={
                            "row_no": None,
                            "التاريخ و الوقت": st.column_config.Column(disabled=True),
                            "اسم الصنف": st.column_config.TextColumn("الصنف"),
                            "الكميه المطلوبه": st.column_config.TextColumn("الكمية")
                        },
                        hide_index=True,
                        use_container_width=True,
                        key="admin_editor"
                    )
                    
                    if st.button("🚀 اعتماد التعديلات وتصديق هذه الطلبية", use_container_width=True, type="primary"):
                        with st.spinner("جاري التحديث..."):
                            for index, row in edited_df.iterrows():
                                r_idx = int(row['row_no'])
                                worksheet.update_cell(r_idx, 2, row['اسم الصنف'])
                                worksheet.update_cell(r_idx, 3, row['الكميه المطلوبه'])
                                worksheet.update_cell(r_idx, 4, "تم التصديق")
                            
                            st.success(f"✅ تم تصديق طلبية {selected_rep} بنجاح!")
                            st.rerun()
                else:
                    st.info(f"المندوب {selected_rep} ليس لديه طلبات معلقة.")
            else:
                st.write("الصفحة فارغة.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء تحميل البيانات: {e}")

# زر الخروج
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.admin_logged_in = False
    st.rerun()

if st.button("🔄 تحديث الإشعارات"):
    st.rerun()
