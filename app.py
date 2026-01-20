import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
# --- إضافة مكتبات الوقت الجديدة ---
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة وتنسيق الطباعة والوميض ---
st.set_page_config(page_title="إدارة حلباوي - حراري", layout="wide")

st.markdown("""
    <style>
    /* تنسيق الزر والشاشة العادية */
    .screen-info { color: white; font-size: 18px; text-align: right; }
    
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border: 2px solid #ffffff; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 22px; margin-top: 20px;
    }

    /* --- كود الوميض الأحمر للأزرار الجديدة --- */
    @keyframes blinking_red {
        0% { background-color: #ff4b4b; color: white; box-shadow: 0 0 5px #ff0000; }
        50% { background-color: #8b0000; color: white; box-shadow: 0 0 20px #ff0000; }
        100% { background-color: #ff4b4b; color: white; box-shadow: 0 0 5px #ff0000; }
    }

    div[data-testid="stVerticalBlock"] div:has(button[key^="btn_"]) button {
        animation: blinking_red 1.2s infinite !important;
        border: 2px solid white !important;
        font-weight: bold !important;
    }

    /* --- كود الطباعة المحسن --- */
    @media print {
        body * { visibility: hidden !important; }
        html, body { margin: 0 !important; padding: 0 !important; height: auto !important; }
        .print-main-wrapper, .print-main-wrapper * { visibility: visible !important; color: #000000 !important; }
        .print-main-wrapper { position: fixed !important; top: 0 !important; right: 0 !important; width: 72mm !important; direction: rtl !important; }
        header, footer, .no-print, [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
        @page { size: 80mm auto; margin: 0mm !important; }
        .header-box { border-bottom: 2px dashed #000 !important; text-align: center; }
        .name-txt { font-size: 85px !important; font-weight: 900 !important; margin: 0; }
        .table-style { width: 100%; border-collapse: collapse; border: 1px solid #000 !important; }
        .table-style th, .table-style td { border: 1px solid #000 !important; padding: 6px !important; text-align: center; font-size: 19px !important; font-weight: 900 !important; }
        .col-qty { width: 25%; font-size: 26px !important; background-color: #f0f0f0 !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدوال الأساسية ونظام الدخول ---
def show_full_logo():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    possible_names = ["Logo.JPG", "Logo .JPG", "logo.jpg"]
    found = False
    for name in possible_names:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            found = True
            break
    if not found:
        st.info("⚠️ يرجى التأكد من رفع صورة Logo.JPG")
    st.markdown('</div>', unsafe_allow_html=True)

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
        # 1. جلب النص من Secrets
        raw_json = st.secrets["gcp_service_account"]["json_data"]
        
        # 2. تنظيف النص من أي فراغات أو علامات زائدة في البداية والنهاية
        clean_json = raw_json.strip()
        
        # 3. تحويل النص إلى قاموس (Dictionary)
        info = json.loads(clean_json, strict=False)
        
        # 4. بناء الصلاحيات
        creds = Credentials.from_service_account_info(
            info, 
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        return gspread.authorize(creds)
    except Exception as e:
        # سيظهر لك هذا التنبيه في التطبيق إذا فشلت القراءة
        st.error(f"⚠️ مشكلة فنية في قراءة المفتاح: {e}")
        return None


client = get_client()

# --- 3. معالجة البيانات والطلبات ---
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    show_full_logo()
    
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            # فحص عمود الحالة (الرابع)
            status_vals = ws.col_values(4)
            if "بانتظار التصديق" in status_vals:
                # توليد توقيت بيروت الحالي لحظة الفحص
                beirut_time = datetime.now(pytz.timezone('Asia/Beirut')).strftime('%H:%M')
                st.session_state.orders.append({"name": rep, "time": beirut_time})
        if not st.session_state.orders:
            st.toast("لا توجد طلبيات جديدة حالياً")

    if 'orders' in st.session_state:
        for order in st.session_state.orders:
            # الزر سيومض باللون الأحمر بفضل الـ Key الموحد btn_
            if st.button(f"📦 طلب من: {order['name']} | 🕒 {order['time']}", key=f"btn_{order['name']}", use_container_width=True):
                st.session_state.active_rep = order['name']
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            # استخدام الوقت المولد تلقائياً أو الموجود في الشيت
            order_time_val = pending.iloc[0]['التاريخ و الوقت'] if 'التاريخ و الوقت' in df.columns else datetime.now(pytz.timezone('Asia/Beirut')).strftime('%Y-%m-%d %H:%M')
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True, use_container_width=True)

            if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                for _, r in edited.iterrows(): ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                st.success("تم!"); st.rerun()
    
                        # تعديل السطر الذي ينجح معك دائماً ليحتوي على الترقيم والخط الكبير
            rows_html = "".join([f"<tr><td style='border:1px solid black; text-align:center; width:10%; font-size:25px;'>{i+1}</td><td class='col-qty' style='font-size:45px !important;'>{r['الكميه المطلوبه']}</td><td style='text-align:right; font-size:36px !important; white-space:nowrap;'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(edited.iterrows())])
            
            thermal_view = f"""
            <div class="print-main-wrapper" style="width:100%; direction:rtl;">
                <div class="header-box" style="text-align:center;">
                    <p style="font-size:120px !important; font-weight:900; margin:0;">طلب: {selected_rep}</p>
                    <p style="font-size:35px !important; font-weight:bold; margin-top:5px;">{order_time_val}</p>
                </div>
                <table class="table-style" style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background-color:#eee; font-size:36px;">
                            <th style="width:10%; border:1px solid black;">ت</th>
                            <th style="width:30%; border:1px solid black;">العدد</th>
                            <th style="border:1px solid black;">الصنف</th>
                        </tr>
                    </thead>
                    <tbody style="font-weight:900;">
                        {rows_html}
                    </tbody>
                </table>
                <p style="text-align:center; font-size:25px; font-weight:bold; margin-top:20px; border-top:2px dashed black; padding-top:10px;">*** نهاية الطلب ***</p>
                </div>
                <div style="page-break-after: always; visibility: hidden;">.</div>

            """
            st.markdown(thermal_view, unsafe_allow_html=True)
            st.markdown("""<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفاتورة</button>""", unsafe_allow_html=True)

if st.sidebar.button("خروج"):
    st.session_state.clear(); st.rerun()
