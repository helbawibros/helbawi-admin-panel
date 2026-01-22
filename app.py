import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة ---
st.set_page_config(page_title="إدارة حلباوي - حراري", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }
    @keyframes blinking_red {
        0% { background-color: #ff4b4b; box-shadow: 0 0 5px #ff0000; }
        50% { background-color: #8b0000; box-shadow: 0 0 20px #ff0000; }
        100% { background-color: #ff4b4b; box-shadow: 0 0 5px #ff0000; }
    }
    div.stButton > button[key^="btn_"] {
        animation: blinking_red 1.2s infinite !important;
        color: white !important;
        border: 2px solid white !important;
    }
    @media print {
        body * { visibility: hidden !important; }
        .print-main-wrapper, .print-main-wrapper * { visibility: visible !important; color: #000000 !important; }
        .print-main-wrapper { position: absolute !important; top: 0 !important; right: 0 !important; width: 100% !important; direction: rtl !important; }
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
        @page { size: 80mm auto; margin: 0mm !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. دالة عرض اللوغو (مع التأكد من المسارات) ---
def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    # جربنا كل الاحتمالات لاسم الملف
    for name in ["Logo.JPG", "Logo .JPG", "logo.jpg", "Logo.jpg"]:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            break
    st.markdown('</div>', unsafe_allow_html=True)

# --- نظام الدخول ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>دخول الإدارة</h1>", unsafe_allow_html=True)
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
                # تنظيف أسماء الأعمدة من الفراغات لمنع الـ KeyError
                df_temp.columns = df_temp.columns.str.strip()
                
                if 'الحالة' in df_temp.columns:
                    pending_orders = df_temp[df_temp['الحالة'] == "بانتظار التصديق"]
                    if not pending_orders.empty:
                        # جلب الوقت من الشيت للزر
                        order_time = pending_orders.iloc[0].get('التاريخ و الوقت', 'غير محدد')
                        st.session_state.orders.append({"name": rep, "time": order_time})
        
        if not st.session_state.orders: st.toast("لا توجد طلبيات جديدة حالياً")

    if 'orders' in st.session_state:
        for order in st.session_state.orders:
            if st.button(f"📦 طلب من: {order['name']} | أرسل في: {order['time']}", key=f"btn_{order['name']}", use_container_width=True):
                st.session_state.active_rep = order['name']
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            df.columns = df.columns.str.strip() # تنظيف الأعمدة
            df['row_no'] = range(2, len(df) + 2)
            
            if 'الحالة' in df.columns:
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                if not pending.empty:
                    st.info(f"عرض طلبات المندوب: {selected_rep}")
                    cols_to_show = [c for c in ['row_no', 'اسم الصنف', 'الكميه المطلوبه'] if c in pending.columns]
                    edited = st.data_editor(pending[cols_to_show], hide_index=True, use_container_width=True)

                    if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                        status_col_idx = data[0].index('الحالة') + 1 if 'الحالة' in data[0] else 4
                        for _, r in edited.iterrows():
                            ws.update_cell(int(r['row_no']), status_col_idx, "تم التصديق")
                        st.success("تم التصديق بنجاح!"); st.rerun()
                    
                    # وقت الطباعة الفعلي (وقت الإدارة)
                    print_time = datetime.now(beirut_tz).strftime('%Y-%m-%d %H:%M:%S')
                    
                    rows_html = "".join([f"<tr><td style='border:1px solid black; text-align:center;'>{i+1}</td><td style='border:1px solid black; text-align:center; font-size:40px; font-weight:bold;'>{r.get('الكميه المطلوبه', '')}</td><td style='border:1px solid black; text-align:right; font-size:30px;'>{r.get('اسم الصنف', '')}</td></tr>" for i, (_, r) in enumerate(edited.iterrows())])
                    
                    thermal_view = f"""
                    <div class="print-main-wrapper">
                        <div style="text-align:center; border-bottom:2px dashed black;">
                            <p style="font-size:50px; font-weight:900; margin:0;">طلب: {selected_rep}</p>
                            <p style="font-size:20px;">وقت الطباعة: {print_time}</p>
                        </div>
                        <table style="width:100%; border-collapse:collapse; margin-top:10px;">
                            {rows_html}
                        </table>
                    </div>
                    """
                    st.markdown(thermal_view, unsafe_allow_html=True)
                    st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفاتورة</button>""", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
