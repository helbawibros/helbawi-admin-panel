import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        raw_json = st.secrets["gcp_service_account"]["json_data"].strip()
        info = json.loads(raw_json, strict=False)
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except: return None

st.title("🛠️ نظام إدارة وتعديل الطلبيات")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates_pages = [name for name in all_worksheets if name not in EXCLUDE_SHEETS]
    
    selected_rep = st.selectbox("اختر المندوب لمراجعة أو تعديل طلبيته:", delegates_pages)
    
    if selected_rep:
        st.divider()
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                df = pd.DataFrame(data[1:], columns=data[0])
                # إضافة عمود لرقم السطر الحقيقي في الإكسل (مهم جداً للحذف)
                df['row_idx'] = range(2, len(df) + 2) 
                
                # فلترة الطلبات المعلقة فقط
                pending = df[df.apply(lambda row: 'بانتظار التصديق' in str(row['الحالة']), axis=1)]
                
                if not pending.empty:
                    st.subheader(f"📦 طلبات معلقة لـ {selected_rep}")
                    
                    # عرض الطلبات مع خيار الحذف لكل سطر
                    for index, row in pending.iterrows():
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        with col1: st.write(f"🔹 **{row['اسم الصنف']}**")
                        with col2: st.write(f"الكمية: {row['الكميه المطلوبه']}")
                        with col3:
                            # زر الحذف الفردي
                            if st.button(f"شطب 🗑️", key=f"del_{row['row_idx']}"):
                                worksheet.delete_rows(int(row['row_idx']))
                                st.warning(f"تم حذف {row['اسم الصنف']}")
                                st.rerun()
                        with col4:
                            # زر تصديق فردي (اختياري)
                            if st.button(f"موافقة ✅", key=f"app_{row['row_idx']}"):
                                # تحديث خلية الحالة في العمود D (الرابع)
                                worksheet.update_cell(int(row['row_idx']), 4, "تم التصديق")
                                st.success("تم!")
                                st.rerun()
                    
                    st.divider()
                    if st.button(f"✅ تصديق جميع طلبات {selected_rep} المتبقية", use_container_width=True):
                        # تحديث الكل كما كان سابقاً
                        data_refresh = worksheet.get_all_values()
                        for i, r in enumerate(data_refresh):
                            if i == 0: continue
                            if "بانتظار التصديق" in r[3]: # نعتبر الحالة في العمود الرابع
                                worksheet.update_cell(i + 1, 4, "تم التصديق")
                        st.success("تم تصديق الكل")
                        st.rerun()
                else:
                    st.info("لا توجد طلبات معلقة حالياً.")
            else:
                st.write("الصفحة فارغة.")
        except Exception as e:
            st.error(f"حدث خطأ: {e}")

if st.button("🔄 تحديث"):
    st.rerun()
