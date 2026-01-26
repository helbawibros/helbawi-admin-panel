import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time

# --- 1. إعدادات الصفحة والـ CSS بمقاسات السنتيمتر ---
st.set_page_config(page_title="إدارة حلباوي - مقاسات دقيقة", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 22px; 
        margin-top: 20px; text-align: center; line-height: 60px; border: none;
    }
    @media screen { .printable-content { display: none; } }
    @media print {
        [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"],
        footer, header, .no-print, .stButton, [data-testid="stDataEditor"], .stSelectbox {
            display: none !important;
        }
        .printable-content {
            display: block !important; visibility: visible !important;
            position: absolute !important; top: 0 !important; left: 0 !important;
            width: 100% !important; margin: 0 !important; padding: 0 !important;
        }
        @page { size: A4 landscape; margin: 5mm !important; }
        
        .print-row {
            display: flex !important; flex-direction: row !important;
            justify-content: space-around !important; width: 100% !important;
            direction: rtl !important;
        }

        .invoice-box {
            width: 10.5cm !important; /* نصف عرض الـ A4 تقريباً */
            border: 1px dashed #000 !important;
            padding: 5px !important;
            box-sizing: border-box !important;
        }

        table { width: 10cm !important; border-collapse: collapse; margin: auto; }
        
        /* المقاسات اللي طلبتها بالظبط */
        .col-id { width: 2cm !important; }
        .col-qty { width: 2cm !important; }
        .col-name { width: 6cm !important; }

        th, td { 
            border: 1.5px solid black !important; 
            padding: 3px !important; 
            text-align: center !important; 
            font-size: 16px !important; 
            font-weight: bold !important;
            overflow: hidden;
            white-space: nowrap;
        }
        h2 { font-size: 20px; margin: 2px 0; text-align: center; }
        .info-bar { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدخول واللوغو ---
def show_full_logo():
    found = False
    for name in ["Logo.JPG", "logo.jpg", "Logo.png"]:
        if os.path.exists(name):
            st.image(name, use_container_width=True)
            found = True; break
    if not found: st.markdown("<h1 style='text-align:center;' class='no-print'>PRIMUM QUALITY</h1>", unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col2 = st.columns([1, 2, 1])[1]
    with col2:
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True; st.rerun()
    st.stop()

# --- 3. الربط الذكي ---
@st.cache_resource
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
    
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    show_full_logo()
    
    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
        st.session_state.orders = []
        for rep in delegates:
            try:
                ws = spreadsheet.worksheet(rep)
                data = ws.get_all_values()
                if len(data) > 1:
                    df_temp = pd.DataFrame(data[1:], columns=data[0])
                    df_temp.columns = df_temp.columns.str.strip()
                    if 'الحالة' in df_temp.columns:
                        p = df_temp[df_temp['الحالة'] == "بانتظار التصديق"]
                        if not p.empty:
                            st.session_state.orders.append({"name": rep, "time": p.iloc[0].get('التاريخ و الوقت', '---')})
            except: continue

    if 'orders' in st.session_state and st.session_state.orders:
        for o in st.session_state.orders:
            if st.button(f"📦 طلب من: {o['name']} | 🕒 أرسل: {o['time']}", key=f"btn_{o['name']}", use_container_width=True):
                st.session_state.active_rep = o['name']; st.rerun()
    
    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))
    st.markdown('</div>', unsafe_allow_html=True)

    if selected_rep != "-- اختر مندوب --":
        ws = spreadsheet.worksheet(selected_rep)
        raw_data = ws.get_all_values()
        if len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            df.columns = df.columns.str.strip()
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip() if 'اسم الزبون' in pending.columns else "جردة سيارة"

                    st.markdown('<div class="no-print">', unsafe_allow_html=True)
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                        idx_status = raw_data[0].index('الحالة') + 1
                        for _, r in edited.iterrows():
                            try:
                                ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                                time.sleep(0.2)
                            except: st.error(f"خطأ في سطر {r['row_no']}")
                        st.success("تم التصديق!"); time.sleep(1); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                    # --- منطقة الطباعة بالقياسات المطلوبة ---
                    st.markdown('<div class="printable-content">', unsafe_allow_html=True)
                    print_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    
                    for target in edited['الوجهة'].unique():
                        target_df = edited[edited['الوجهة'] == target]
                        display_title = f"طلب: {target}" if target != "جردة سيارة" else f"جردة: {selected_rep}"
                        
                        # بناء الأسطر مع الكلاسات للتحكم بالمقاسات
                        rows_html = "".join([
                            f"<tr><td class='col-id'>{i+1}</td><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-name' style='text-align:right;'>{r['اسم الصنف']}</td></tr>" 
                            for i, (_, r) in enumerate(target_df.iterrows())
                        ])
                        
                        invoice_html = f"""
                        <div class="invoice-box">
                            <h2>{display_title}</h2>
                            <div class="info-bar">
                                <span>المندوب: {selected_rep}</span><span>{print_now}</span>
                            </div>
                            <table>
                                <thead>
                                    <tr><th class="col-id">ت</th><th class="col-qty">العدد</th><th class="col-name">اسم الصنف</th></tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                        """
                        # وضع الفاتورتين جنب بعض
                        st.markdown(f'<div class="print-row">{invoice_html}{invoice_html}</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة بمقاسات (2+2+6 سم)</button>', unsafe_allow_html=True)
