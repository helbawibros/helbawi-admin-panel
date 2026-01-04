import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# --- قائمة المندوبين المعتمدين ---
REPS_LIST = [
    "عبد الكريم حوراني", "محمد الحسيني", "علي دوغان", 
    "عزات حلاوي", "علي حسين حلباوي", "محمد حسين حلباوي", 
    "احمد حسين حلباوي", "علي محمد حلباوي"
]

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        raw_json = st.secrets["gcp_service_account"]["json_data"].strip()
        info = json.loads(raw_json, strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except:
        return None

st.title("🛠️ نظام إدارة الطلبيات المركزي")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # جلب جميع أسماء الصفحات في الملف
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    
    # فلترة الصفحات لتظهر فقط المندوبين الموجودين فعلياً في الإكسل
    delegates_pages = [rep for rep in REPS_LIST if rep in all_worksheets]
    
    # القائمة الجانبية لاختيار المندوب
    st.sidebar.markdown("### 👤 قائمة المندوبين")
    selected_rep = st.sidebar.selectbox("اختر اسم المندوب لعرض طلبياته", delegates_pages)
    
    if selected_rep:
        st.header(f"📋 طلبات المندوب: {selected_rep}")
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                
                # البحث عن الحالات التي تحتاج تصديق
                mask = df.apply(lambda row: row.astype(str).str.contains('بانتظار التصديق').any(), axis=1)
                pending = df[mask]
                
                if not pending.empty:
                    st.success(f"📦 يوجد {len(pending)} طلبات جديدة معلقة")
                    st.table(pending)
                    
                    if st.button(f"✅ تصديق كل طلبات {selected_rep}", use_container_width=True):
                        # تحديث الحالة في الإكسل
                        for i, row in enumerate(data):
                            if i == 0: continue
                            for j, cell_value in enumerate(row):
                                if "بانتظار التصديق" in cell_value:
                                    worksheet.update_cell(i + 1, j + 1, "تم التصديق")
                        st.success("✅ تم التصديق وتحديث البيانات!")
                        st.rerun()
                else:
                    st.info(f"لا توجد طلبات معلقة حالياً لـ {selected_rep}")
                    
                # عرض أرشيف الطلبات الأخيرة
                with st.expander("📄 عرض أرشيف الطلبات المصدقة"):
                    done_mask = df.apply(lambda row: row.astype(str).str.contains('تم التصديق').any(), axis=1)
                    st.table(df[done_mask].tail(10))
                    
            else:
                st.write("الصفحة فارغة حالياً.")
        except Exception as e:
            st.error(f"خطأ: تأكد من وجود صفحة باسم '{selected_rep}' في ملف الإكسل.")

# زر تحديث يدوي
if st.sidebar.button("🔄 تحديث القائمة"):
    st.rerun()
