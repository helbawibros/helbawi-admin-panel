import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# أسماء الصفحات التي نريد إخفاءها (لأنها ليست مناديب)
EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        raw_json = st.secrets["gcp_service_account"]["json_data"].strip()
        info = json.loads(raw_json, strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except: return None

st.title("🛠️ نظام إدارة الطلبيات المركزي")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # جلب كل الصفحات وفلترة الصفحات الإدارية
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates_pages = [name for name in all_worksheets if name not in EXCLUDE_SHEETS]
    
    # --- تعديل: وضع الاختيار في منتصف الصفحة بدلاً من الجانب ---
    st.markdown("### 👤 اختر المندوب من القائمة أدناه:")
    selected_rep = st.selectbox("قائمة المناديب:", delegates_pages)
    
    if selected_rep:
        st.divider()
        st.header(f"📋 طلبات المندوب: {selected_rep}")
        
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                
                # فحص الطلبات المعلقة
                mask = df.apply(lambda row: row.astype(str).str.contains('بانتظار التصديق').any(), axis=1)
                pending = df[mask]
                
                if not pending.empty:
                    st.success(f"📦 يوجد {len(pending)} طلبات معلقة")
                    st.table(pending)
                    
                    if st.button(f"✅ تصديق كل طلبات {selected_rep}", use_container_width=True):
                        # تحديث الحالة مباشرة في الإكسل
                        for i, row in enumerate(data):
                            if i == 0: continue
                            for j, cell_value in enumerate(row):
                                if "بانتظار التصديق" in cell_value:
                                    worksheet.update_cell(i + 1, j + 1, "تم التصديق")
                        st.success("✅ تم التصديق بنجاح!")
                        st.rerun()
                else:
                    st.info(f"لا توجد طلبات معلقة حالياً لـ {selected_rep}")
                
                # أرشيف الطلبات
                with st.expander("📄 أرشيف آخر الطلبات المصدقة"):
                    done_mask = df.apply(lambda row: row.astype(str).str.contains('تم التصديق').any(), axis=1)
                    st.table(df[done_mask].tail(15))
            else:
                st.warning("هذه الصفحة لا تحتوي على بيانات بعد.")
                
        except Exception as e:
            st.error(f"حدث خطأ: {e}")

if st.button("🔄 تحديث البيانات"):
    st.rerun()
