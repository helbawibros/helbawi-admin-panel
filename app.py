import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 

# --- 1. إعدادات الصفحة والـ CSS للطباعة الاحترافية ---
st.set_page_config(page_title="إدارة حلباوي - النسخة النهائية المستقرة", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 22px; 
        margin-top: 20px; text-align: center; line-height: 60px; text-decoration: none; border: none;
    }
    @media screen { .printable-content { display: none; } }
    @media print {
        [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"],
        footer, header, .no-print, .stButton, [data-testid="stDataEditor"], .stSelectbox, .stAlert {
            display: none !important;
        }
        .printable-content {
            display: block !important; visibility: visible !important;
            position: absolute !important; top: 0 !important; left: 0 !important;
            width: 100% !important; margin: 0 !important; padding: 0 !important;
        }
        .stApp { background: white !important; }
        @page { size: A4 landscape; margin: 0 !important; }
        .print-row {
            display: flex !important; flex-direction: row !important;
            justify-content: space-between !important; width: 100% !important;
            page-break-inside: avoid !important; margin-bottom: 20px !important; direction: rtl !important;
        }
        .invoice-box {
            width: 48% !important; border: 2px dashed black !important;
            padding: 10px !important; box-sizing: border-box !important;
        }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 2px solid black; padding: 5px; text-align: center; font-size: 18px; font-weight: bold; color: black !important; }
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
                            # حطيت لك التاريخ والوقت هون عشان يظهروا بالكبسات
                            st.session_state.orders.append({"name": rep, "time": p.iloc[0].get('التاريخ و الوقت', '---')})
            except: continue # تخطي أي ورقة فيها مشكلة

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
                        for _, r in edited.iterrows(): ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                        st.success("تم التصديق!"); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                    st.markdown('<div class="printable-content">', unsafe_allow_html=True)
                    print_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    for target in edited['الوجهة'].unique():
                        target_df = edited[edited['الوجهة'] == target]
                        display_title = f"طلب: {target}" if target != "جردة سيارة" else f"جردة: {selected_rep}"
                        rows_html = "".join([f"<tr><td>{i+1}</td><td>{r['الكميه المطلوبه']}</td><td style='text-align:right;'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(target_df.iterrows())])
                        invoice = f"""
                        <div class="invoice-box">
                            <h2 style="text-align:center; margin:0;">{display_title}</h2>
                            <div style="display:flex; justify-content:space-between; font-weight:bold; direction:rtl; margin-top:5px;">
                                <span>المندوب: {selected_rep}</span><span>{print_now}</span>
                            </div>
                            <table><thead><tr><th>ت</th><th>العدد</th><th>اسم الصنف</th></tr></thead><tbody>{rows_html}</tbody></table>
                        </div>"""
                        st.markdown(f'<div class="print-row">{invoice}{invoice}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفواتير المفرزة</button>', unsafe_allow_html=True)
