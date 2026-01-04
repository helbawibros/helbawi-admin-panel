import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        raw_json = st.secrets["gcp_service_account"]["json_data"].strip()
        service_account_info = json.loads(raw_json, strict=False)
        creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return None

st.title("🛠️ نظام إدارة الطلبيات المركزي")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    # نبدأ القراءة من بعد أول 4 صفحات
    delegates_pages = all_worksheets[4:] 
    
    if not delegates_pages:
        st.warning("لم يتم العثور على صفحات مناديب.")
    else:
        selected_rep = st.sidebar.selectbox("اختر المندوب", delegates_pages)
        
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            # جلب البيانات كقائمة صفوف لتجنب مشاكل العناوين
            rows = worksheet.get_all_values()
            
            if len(rows) > 1:
                # تحويل البيانات إلى DataFrame وتسمية الأعمدة يدوياً لضمان الدقة
                df = pd.DataFrame(rows[1:], columns=rows[0])
                
                # تنظيف أسماء الأعمدة من المسافات المخفية
                df.columns = [c.strip() for c in df.columns]
                
                if 'الحالة' in df.columns:
                    # فلترة الطلبات التي تحتوي على "بانتظار التصديق"
                    pending = df[df['الحالة'].str.contains("بانتظار التصديق", na=False)]
                    
                    if not pending.empty:
                        st.success(f"📦 يوجد {len(pending)} طلبات معلقة لـ {selected_rep}")
                        st.table(pending)
                        
                        if st.button(f"✅ تصديق طلبات {selected_rep}"):
                            # البحث عن كل صف حالته "بانتظار التصديق" وتحديثه
                            all_data = worksheet.get_all_values()
                            for i, row in enumerate(all_data):
                                if i == 0: continue # تخطي العنوان
                                # إذا كان العمود الرابع (D) هو الحالة
                                if "بانتظار التصديق" in row[3]: 
                                    worksheet.update_cell(i + 1, 4, "تم التصديق")
                            
                            st.success("تم التصديق بنجاح!")
                            st.rerun()
                    else:
                        st.info(f"لا توجد طلبات معلقة حالياً لـ {selected_rep}")
                else:
                    st.error("لم أجد عمود باسم 'الحالة'. تأكد أن الخانة D1 مكتوب فيها كلمة: الحالة")
            else:
                st.write("الصفحة فارغة.")
        except Exception as e:
            st.error(f"حدث خطأ: {e}")
