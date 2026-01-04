import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# قائمة المندوبين المعتمدين (نفس الموجودة في تطبيق المندوب)
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
    except Exception as e:
        st.error(f"خطأ في الاتصال بجوجل: {e}")
        return None

st.title("🛠️ نظام إدارة الطلبيات المركزي")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # جلب كل عناوين الصفحات الموجودة في الإكسل
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    
    # تعديل جوهري: اختيار الصفحات التي تطابق أسماء المندوبين فقط
    delegates_pages = [name for name in REPS_LIST if name in all_worksheets]
    
    if not delegates_pages:
        st.warning("لم يتم العثور على صفحات للمندوبين المحددين في ملف الإكسل.")
    else:
        selected_rep = st.sidebar.selectbox("اختر المندوب", delegates_pages)
        st.header(f"📋 طلبات المندوب: {selected_rep}")
        
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                
                # البحث عن الطلبات المعلقة
                mask = df.apply(lambda row: row.astype(str).str.contains('بانتظار التصديق').any(), axis=1)
                pending = df[mask]
                
                if not pending.empty:
                    st.success(f"📦 يوجد {len(pending)} طلبات معلقة لـ {selected_rep}")
                    st.table(pending)
                    
                    if st.button(f"✅ تصديق كل طلبات {selected_rep}", use_container_width=True):
                        with st.spinner("جاري التحديث..."):
                            # جلب البيانات من جديد لضمان الدقة قبل التحديث
                            current_data = worksheet.get_all_values()
                            for i, row in enumerate(current_data):
                                if i == 0: continue # تخطي العنوان
                                for j, cell_value in enumerate(row):
                                    if "بانتظار التصديق" in cell_value:
                                        worksheet.update_cell(i + 1, j + 1, "تم التصديق")
                            
                        st.success("✅ تم التصديق وتحديث الإكسل!")
                        st.rerun()
                else:
                    st.info(f"لا توجد طلبات معلقة حالياً لـ {selected_rep}")
                    # عرض آخر 5 طلبات تمت المصادقة عليها للشفافية
                    st.write("آخر الطلبات التي تم تصديقها:")
                    st.table(df[df.apply(lambda row: row.astype(str).str.contains('تم التصديق').any(), axis=1)].tail(5))
            else:
                st.write("الصفحة فارغة ولا تحتوي على بيانات.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء جلب بيانات {selected_rep}: {e}")

# إضافة زر لتحديث الصفحة يدوياً في القائمة الجانبية
if st.sidebar.button("🔄 تحديث البيانات"):
    st.rerun()
