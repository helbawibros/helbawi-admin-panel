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
        info = json.loads(raw_json, strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except: return None

st.title("🛠️ نظام إدارة الطلبيات المركزي")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates_pages = all_worksheets[4:] 
    
    selected_rep = st.sidebar.selectbox("اختر المندوب", delegates_pages)
    
    try:
        worksheet = spreadsheet.worksheet(selected_rep)
        data = worksheet.get_all_values()
        
        if len(data) > 1:
            # تحويل البيانات لجدول
            df = pd.DataFrame(data[1:], columns=data[0])
            
            # ميزة البحث الشامل: ابحث عن كلمة "بانتظار التصديق" في كل الخلايا
            mask = df.apply(lambda row: row.astype(str).str.contains('بانتظار التصديق').any(), axis=1)
            pending = df[mask]
            
            if not pending.empty:
                st.success(f"📦 يوجد {len(pending)} طلبات معلقة لـ {selected_rep}")
                st.table(pending)
                
                if st.button(f"✅ تصديق طلبات {selected_rep}"):
                    # تحديث الحالة: سنبحث في كل صف وكل عمود عن الكلمة ونغيرها
                    for i, row in enumerate(data):
                        if i == 0: continue
                        for j, cell_value in enumerate(row):
                            if "بانتظار التصديق" in cell_value:
                                worksheet.update_cell(i + 1, j + 1, "تم التصديق")
                    
                    st.success("✅ تم التصديق وتحديث الإكسل!")
                    st.rerun()
            else:
                st.info(f"لا توجد طلبات معلقة حالياً لـ {selected_rep}")
        else:
            st.write("الصفحة فارغة.")
    except Exception as e:
        st.error(f"حدث خطأ: {e}")
