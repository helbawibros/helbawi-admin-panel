import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة الإجباري ---
st.set_page_config(page_title="إدارة حلباوي - A4 Double", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

            @media print {
        /* 1. إخفاء شامل ومطلق لكل زوائد ستريمليت والجدول العلوي */
        header, footer, .no-print, [data-testid="stHeader"], 
        [data-testid="stSidebar"], [data-testid="stToolbar"],
        [data-testid="stDataEditor"], /* إخفاء الجدول العلوي */
        .stImage, h1, h2, h3, .stMarkdown p {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 2. تصفير هوامش التطبيق بالكامل */
        .stApp {
            position: absolute !important;
            top: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }

        /* 3. إجبار الصفحة على البدء من الصفر المطلق */
        @page { 
            size: A4 landscape; 
            margin: 0 !important; 
        }

        /* 4. تنسيق الفواتير (يمين وشمال) في أعلى الورقة */
        .print-container {
            visibility: visible !important;
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            width: 100% !important;
            position: fixed !important; /* تثبيت في أعلى الورقة */
            top: 0 !important;
            left: 0 !important;
            direction: rtl !important;
        }

        .invoice-half {
            width: 48% !important;
            border: 2px dashed black !important;
            padding: 5px !important;
            box-sizing: border-box !important;
        }

        /* تكبير الخط للتوضيح */
        .thermal-table th, .thermal-table td {
            font-size: 22px !important; 
            border: 2px solid black !important;
        }
    }

    </style>
""", unsafe_allow_html=True)


# --- 2. دالة اللوغو (استرجاع الصورة الأساسية) ---
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

# --- نظام الدخول ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col2 = st.columns([1, 2, 1])[1]
    with col2:
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True
                st.rerun()
    st.stop()

def get_client():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except: return None

client = get_client()

if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    show_full_logo()
    
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            data = ws.get_all_values()
            if len(data) > 1:
                df_temp = pd.DataFrame(data[1:], columns=data[0])
                df_temp.columns = df_temp.columns.str.strip()
                if 'الحالة' in df_temp.columns:
                    p = df_temp[df_temp['الحالة'] == "بانتظار التصديق"]
                    if not p.empty:
                        st.session_state.orders.append({"name": rep, "time": p.iloc[0].get('التاريخ و الوقت', '---')})
    
    if 'orders' in st.session_state:
        for o in st.session_state.orders:
            if st.button(f"📦 طلب من: {o['name']} | {o['time']}", key=f"btn_{o['name']}", use_container_width=True):
                st.session_state.active_rep = o['name']
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        raw_data = ws.get_all_values()
        if len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            df.columns = df.columns.str.strip()
            df['row_no'] = range(2, len(df) + 2)
            
                        # 1. جلب البيانات والتأكد من وجود الأعمدة
            pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
            
            if not pending.empty:
                # 1. تنظيف البيانات وجلب اسم الزبون بطريقة ذكية
                if 'اسم الزبون' in pending.columns:
                    # تحويل القيم إلى نص وتنظيفها من الـ nan والمسافات
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                else:
                    # إذا المندوب ما بعت عمود الاسم أصلاً
                    pending['الوجهة'] = "جردة سيارة"

                st.markdown('<div class="no-print">', unsafe_allow_html=True)
                # 2. عرض المحرر للإدارة (تأكد من ترتيب الأعمدة)
                # عرضنا 'الوجهة' بدل 'اسم الزبون' لأننا نظفناها فوق
                edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)

                
                if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                    idx_status = raw_data[0].index('الحالة') + 1
                    for _, r in edited.iterrows():
                        ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                    st.success("تم التصديق بنجاح!"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                # --- 2. منطق الفرز التلقائي للطباعة ---
                unique_targets = edited['الوجهة'].unique()
                
                for target in unique_targets:
                    target_df = edited[edited['الوجهة'] == target]
                    print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # عنوان الفاتورة بناءً على الوجهة
                    display_title = f"طلب خاص: {target}" if target != "جردة سيارة" else f"طلب سيارة: {selected_rep}"
                    
                    rows_html = "".join([f"<tr><td>{i+1}</td><td>{r.get('الكميه المطلوبه','')}</td><td style='text-align:right; padding-right:5px;'>{r.get('اسم الصنف','')}</td></tr>" for i, (_, r) in enumerate(target_df.iterrows())])
                    
                    invoice_html = f"""
                    <div style="text-align:center; border-bottom:2px solid black; margin-bottom:5px;">
                        <h2 style="margin:0; font-size:24px;">{display_title}</h2>
                        <p style="margin:0; font-size:14px;">المندوب: {selected_rep} | الوقت: {print_time}</p>
                    </div>
                    <table class="thermal-table">
                        <thead><tr><th style="width:10%;">ت</th><th style="width:20%;">العدد</th><th>الصنف</th></tr></thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                    <p style="text-align:center; font-size:12px; margin-top:5px;">*** نهاية طلب ({target}) ***</p>
                    """

                    st.markdown(f"""
                    <div class="print-container">
                        <div class="invoice-half">{invoice_html}</div>
                        <div class="invoice-half">{invoice_html}</div>
                    </div>
                    <div class="no-print" style="margin-bottom:30px; border-bottom: 2px dashed #ccc; padding-top:20px;"></div>
                    """, unsafe_allow_html=True)
                
                st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة كل الطلبيات المفرزة</button>""", unsafe_allow_html=True)

