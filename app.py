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

st.title("🏭 إدارة طلبيات المعمل - تعديل سريع")

client = get_gspread_client()

if client:
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    spreadsheet = client.open_by_key(SHEET_ID)
    all_worksheets = [sh.title for sh in spreadsheet.worksheets()]
    delegates_pages = [name for name in all_worksheets if name not in EXCLUDE_SHEETS]
    
    selected_rep = st.selectbox("اختر المندوب:", delegates_pages)
    
    if selected_rep:
        try:
            worksheet = spreadsheet.worksheet(selected_rep)
            data = worksheet.get_all_values()
            
            if len(data) > 1:
                full_df = pd.DataFrame(data[1:], columns=data[0])
                # إضافة عمود لرقم السطر الأصلي للرجوع إليه عند الحفظ
                full_df['row_no'] = range(2, len(full_df) + 2)
                
                # تصفية الطلبات التي بانتظار التصديق فقط
                pending_mask = full_df['الحالة'] == "بانتظار التصديق"
                pending_df = full_df[pending_mask].copy()
                
                if not pending_df.empty:
                    st.warning(f"ملاحظة: يمكنك تعديل 'الكمية' أو 'اسم الصنف' مباشرة من الجدول أدناه.")
                    
                    # --- الجدول التفاعلي السريع ---
                    # نعرض فقط الأعمدة المهمة للتعديل
                    edited_df = st.data_editor(
                        pending_df[['row_no', 'التاريخ و الوقت', 'اسم الصنف', 'الكميه المطلوبه']],
                        column_config={
                            "row_no": None, # إخفاء رقم السطر عن المستخدم
                            "التاريخ و الوقت": st.column_config.Column(disabled=True),
                            "اسم الصنف": st.column_config.TextColumn("الصنف"),
                            "الكميه المطلوبه": st.column_config.TextColumn("الكمية")
                        },
                        hide_index=True,
                        use_container_width=True,
                        key="editor"
                    )
                    
                    st.divider()
                    
                    if st.button("🚀 اعتماد التعديلات وتصديق الطلبية", use_container_width=True, type="primary"):
                        with st.spinner("جاري تحديث البيانات في الإكسل..."):
                            # 1. تحديث الأسطر المعدلة (الكمية أو الصنف) وتغيير الحالة
                            for index, row in edited_df.iterrows():
                                r_idx = int(row['row_no'])
                                # تحديث اسم الصنف (العمود B) والكمية (العمود C) والحالة (العمود D)
                                worksheet.update_cell(r_idx, 2, row['اسم الصنف'])
                                worksheet.update_cell(r_idx, 3, row['الكميه المطلوبه'])
                                worksheet.update_cell(r_idx, 4, "تم التصديق")
                            
                            st.success("✅ تم تعديل وتصديق الطلبية بنجاح!")
                            st.rerun()
                else:
                    st.info("لا توجد طلبات معلقة حالياً.")
            else:
                st.write("الصفحة فارغة.")
        except Exception as e:
            st.error(f"خطأ: {e}")

if st.button("🔄 تحديث الصفحة"):
    st.rerun()
