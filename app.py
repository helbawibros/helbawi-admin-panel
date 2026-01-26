import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة والتنسيق الشامل ---
st.set_page_config(page_title="إدارة حلباوي - الكامل", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

# CSS لإخفاء كل شيء وقت الطباعة وتنسيق النسختين
st.markdown("""
    <style>
    /* زر الطباعة الأخضر الواضح */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 22px; 
        margin-top: 20px; text-align: center; line-height: 60px; text-decoration: none;
    }

    @media print {
        /* 1. إخفاء إجباري وشامل لكل شيء (اللوغو، الكبسات، العناوين، القوائم) */
        header, footer, .no-print, 
        [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"],
        .stButton, .stSelectbox, img, h1, h2, h3, .stMarkdownContainer,
        div[class*="st-emotion-cache"] {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            visibility: hidden !important;
        }

        /* 2. تنظيف الورقة وسحب الجداول لأعلى نقطة (0 فراغ) */
        .stApp { 
            position: absolute !important; 
            top: 0 !important; 
            margin: 0 !important; 
            padding: 0 !important; 
        }
        
        .main .block-container { 
            padding: 0 !important; 
            margin: 0 !important; 
            max-width: 100% !important;
        }

        /* 3. إعداد الصفحة بالعرض A4 */
        @page { 
            size: A4 landscape; 
            margin: 5mm !important; 
        }

        /* 4. إظهار حاوية الجداول فقط رغماً عن أي أمر إخفاء */
        .print-container {
            display: flex !important;
            visibility: visible !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            width: 100% !important;
            direction: rtl !important;
            position: relative !important;
            top: 0 !important;
        }

        .invoice-half {
            width: 48% !important;
            padding: 10px !important;
            border: 2px dashed #000 !important;
            visibility: visible !important;
        }

        .thermal-table {
            width: 100% !important;
            border-collapse: collapse !important;
            border: 2px solid black !important;
            visibility: visible !important;
        }
        
        .thermal-table th, .thermal-table td {
            border: 2px solid black !important;
            padding: 8px !important;
            text-align: center !important;
            font-size: 20px !important;
            font-weight: bold !important;
            color: black !important;
            visibility: visible !important;
        }
    }
    </style>
""", unsafe_allow_html=True)


# --- 2. نظام اللوغو ---
def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    found = False
    for name in ["Logo.JPG", "logo.jpg", "Logo.png"]:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            found = True
            break
    if not found:
        st.markdown("<h1 style='text-align:center;'>PRIMUM QUALITY</h1>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. الاتصال بجوجل شيت (مع حل مشكلة API Error) ---
def get_client():
    try:
        # جلب البيانات من Secrets
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"خطأ في الاتصال بجوجل: {e}")
        return None

# --- 4. إدارة الجلسة والدخول ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    show_full_logo()
    col_in = st.columns([1, 2, 1])[1]
    with col_in:
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("كلمة السر خطأ!")
    st.stop()

# --- 5. البرنامج الأساسي ---
client = get_client()

if client:
    try:
        spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
        # استثناء الشيتات الإدارية
        delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
        
        show_full_logo()
        
        st.markdown('<div class="no-print">', unsafe_allow_html=True)
        # كبسة فحص الإشعارات
        if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
            st.session_state.orders = []
            for rep in delegates:
                ws = spreadsheet.worksheet(rep)
                data = ws.get_all_values()
                if len(data) > 1:
                    df_temp = pd.DataFrame(data[1:], columns=data[0])
                    if 'الحالة' in df_temp.columns and not df_temp[df_temp['الحالة'] == "بانتظار التصديق"].empty:
                        st.session_state.orders.append({"name": rep})
        
        # عرض المندوبين الذين لديهم طلبات
        if 'orders' in st.session_state:
            for o in st.session_state.orders:
                if st.button(f"📦 طلب من: {o['name']}", key=f"btn_{o['name']}", use_container_width=True):
                    st.session_state.active_rep = o['name']
                    st.rerun()

        active = st.session_state.get('active_rep', "-- اختر مندوب --")
        selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))
        st.markdown('</div>', unsafe_allow_html=True)

        if selected_rep != "-- اختر مندوب --":
            ws = spreadsheet.worksheet(selected_rep)
            raw_data = ws.get_all_values()
            if len(raw_data) > 1:
                df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                df.columns = df.columns.str.strip()
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending.empty:
                    # تنظيم الوجهة (جردة أو زبون)
                    pending['الوجهة'] = pending['اسم الزبون'].fillna('جردة سيارة').replace('', 'جردة سيارة').str.strip()

                    st.markdown('<div class="no-print">', unsafe_allow_html=True)
                    st.subheader(f"طلبات المندوب: {selected_rep}")
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                        idx_status = raw_data[0].index('الحالة') + 1
                        for _, r in edited.iterrows():
                            ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                        st.success("تم التصديق بنجاح!"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                    # --- 6. عرض الفواتير للطباعة (يمين وشمال) ---
                    unique_targets = edited['الوجهة'].unique()
                    for target in unique_targets:
                        target_df = edited[edited['الوجهة'] == target]
                        print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %I:%M %p')
                        display_title = f"طلب: {target}" if target != "جردة سيارة" else f"جردة: {selected_rep}"
                        
                        rows_html = ""
                        for i, (_, r) in enumerate(target_df.iterrows()):
                            rows_html += f"<tr><td>{i+1}</td><td>{r['الكميه المطلوبه']}</td><td style='text-align:right; padding-right:10px;'>{r['اسم الصنف']}</td></tr>"
                        
                        invoice_html = f"""
                        <div style="text-align:center; border-bottom:2px solid black; margin-bottom:10px;">
                            <h1 style="margin:0; font-size:26px;">{display_title}</h1>
                            <p style="margin:5px 0; font-size:18px;">المندوب: {selected_rep} | {print_time}</p>
                        </div>
                        <table class="thermal-table">
                            <thead><tr><th style="width:10%;">ت</th><th style="width:20%;">العدد</th><th>اسم الصنف والبيان</th></tr></thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                        <div style="margin-top:10px; text-align:center; font-weight:bold;">*** نسخة (تحضير / فواتير) ***</div>
                        """

                        st.markdown(f"""
                        <div class="print-container">
                            <div class="invoice-half">{invoice_html}</div>
                            <div class="invoice-half">{invoice_html}</div>
                        </div>
                        <div class="no-print" style="page-break-after: always; border-bottom: 2px dashed #ccc; margin: 30px 0;"></div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفواتير</button>""", unsafe_allow_html=True)
                else:
                    st.info("لا توجد طلبات بانتظار التصديق لهذا المندوب.")
    except Exception as e:
        st.error(f"حدث خطأ في قراءة البيانات: {e}")

