import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# دالة الاتصال
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
    
    # 1. جلب كل أسماء الصفحات وتجاهل أول 4 صفحات إدارية
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates_pages = all_worksheets[4:] # يبدأ القراءة من الصفحة الخامسة وما بعد
    
    if not delegates_pages:
        st.warning("لم يتم العثور على صفحات للمناديب بعد الصفحات الأربع الأولى.")
    else:
        # 2. اختيار المندوب من القائمة
        selected_rep = st.sidebar.selectbox("اختر المندوب للمراجعة", delegates_pages)
        
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                # عرض الطلبات "بانتظار التصديق" فقط
                if 'الحالة' in df.columns:
                    pending = df[df['الحالة'] == 'بانتظار التصديق']
                    if not pending.empty:
                        st.success(f"📦 طلبات جديدة لـ {selected_rep}")
                        st.table(pending)
                        
                        if st.button(f"✅ تصديق طلبات {selected_rep}"):
                            # تحديث الحالة في الإكسل إلى "تم التصديق"
                            for i, row in df.iterrows():
                                if row['الحالة'] == 'بانتظار التصديق':
                                    worksheet.update_cell(i + 2, 4, "تم التصديق") # تحديث العمود الرابع
                            st.balloons()
                            st.success("تم تحديث الحالة في الإكسل!")
                    else:
                        st.info(f"لا توجد طلبات معلقة لـ {selected_rep}")
                else:
                    st.error("تأكد من وجود رأس عمود باسم 'الحالة' في صفحة المندوب")
            else:
                st.write("لا توجد بيانات في صفحة هذا المندوب.")
        except Exception as e:
            st.error(f"حدث خطأ أثناء قراءة صفحة {selected_rep}: {e}")
