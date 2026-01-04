import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

# إعدادات الصفحة
st.set_page_config(page_title="لوحة تحكم إدارة حلباوي", layout="wide")

# دالة الاتصال بجوجل شيت
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

# العنوان الرئيسي
st.title("🛠️ نظام إدارة الطلبيات المركزي")

client = get_gspread_client()
if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    
    # قائمة بأسماء المناديب (الصفحات في الإكسل)
    delegates = ["عبد الكريم حوراني", "محمد الحسيني", "علي دوغان", "عزات حلاوي"]
    
    selected_rep = st.sidebar.selectbox("اختر المندوب للمراجعة", delegates)
    
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(selected_rep)
        data = sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            # عرض الطلبات التي لم يتم تصديقها فقط
            pending_orders = df[df['الحالة'] == 'بانتظار التصديق']
            
            if not pending_orders.empty:
                st.success(f"يوجد {len(pending_orders)} طلبات جديدة لـ {selected_rep}")
                st.table(pending_orders)
                
                if st.button(f"✅ تصديق جميع طلبات {selected_rep}"):
                    # هنا سنضيف لاحقاً كود خصم الستوك الفعلي
                    st.warning("جاري معالجة التصديق وتحديث المخزون...")
            else:
                st.info("لا توجد طلبات جديدة معلقة لهذا المندوب.")
        else:
            st.write("الصفحة فارغة حالياً.")
    except:
        st.error(f"لا توجد صفحة باسم '{selected_rep}' في ملف الإكسل.")

