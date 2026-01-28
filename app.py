import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time

# --- 1. إعدادات الصفحة والستايل ---
st.set_page_config(page_title="إدارة حلباوي - النسخة الاحترافية", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    /* كبسة فحص الإشعارات الحمراء المضواية */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); font-weight: bold; height: 50px;
    }
    /* كبسات المندوبين الخضراء الكبيرة */
    div[data-testid="column"] button {
        background-color: #28a745 !important; color: white !important;
        height: 100px !important; border: 2px solid #1e7e34 !important;
        font-size: 20px !important; white-space: pre-wrap !important;
    }
    /* تنسيق اسم الشركة */
    .company-title {
        font-family: 'Arial Black', sans-serif;
        color: #D4AF37; text-align: center; font-size: 50px;
        text-shadow: 2px 2px 4px #000000; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# تهيئة الذاكرة
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'orders' not in st.session_state: st.session_state.orders = []

# --- دالة الاتصال بجوجل (تعريفها قبل الاستخدام) ---
@st.cache_resource
def get_sh():
    try:
        # تأكد من أن secrets مضبوطة في Streamlit Cloud
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        # استبدل المعرف باللي عندك
        return gspread.authorize(creds).open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال بجوجل: {e}")
        return None

# دالة ذكية لإيجاد اللوغو
def show_logo(use_width=True):
    possible_names = ["Logo .JPG", "Logo.JPG", "logo.jpg", "Logo .png", "Logo.png"]
    for name in possible_names:
        if os.path.exists(name):
            st.image(name, use_container_width=use_width)
            return True
    return False

# --- 2. نظام الدخول ---
if not st.session_state.admin_logged_in:
    show_logo(use_width=True)
    col_l = st.columns([1, 2, 1])[1]
    with col_l:
        st.markdown("<h2 style='text-align:center;'>تسجيل الدخول</h2>", unsafe_allow_html=True)
        pwd = st.text_input("كلمة السر الخاصة بالإدارة", type="password")
        if st.button("دخول النظام", use_container_width=True):
            if pwd == "Hlb_Admin_2024": 
                st.session_state.admin_logged_in = True
                st.rerun()
            else: 
                st.error("كلمة السر خطأ")
    st.stop()

# --- 3. عرض الرادار واللمبات (نسخة سريعة ولا تؤثر على الطلبات) ---
# --- رادار المندوبين المتطور (سريع ولا يسبب أخطاء) ---
# --- رادار المندوبين (النسخة المضيئة) ---
st.markdown('<div style="text-align:center; font-size:28px; font-weight:bold; color:#B8860B; margin-bottom:10px;">Helbawi Bros</div>', unsafe_allow_html=True)

try:
    # 1. جلب البيانات (استخدام الرابط السريع لمنع الـ API Error)
    SHEET_ID = "1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Status"
    df_status = pd.read_csv(url)
    
    beirut_tz = pytz.timezone('Asia/Beirut')
    now = datetime.now(beirut_tz)
    
    # 2. بناء شكل اللمبات بالعرض
    lumps_html = '<div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 20px;">'
    
    for index, row in df_status.head(8).iterrows():
        is_online = False
        try:
            last_seen_str = str(row.iloc[1]).strip()
            # فحص إذا الخلية فيها تاريخ
            if last_seen_str and last_seen_str != "nan":
                last_seen = datetime.strptime(last_seen_str, "%Y-%m-%d %H:%M:%S")
                last_seen = beirut_tz.localize(last_seen)
                # إذا المندوب ظهر بآخر 10 دقائق بكون أخضر
                if (now - last_seen).total_seconds() / 60 < 10:
                    is_online = True
        except: pass
        
        # 🟢 للأونلاين و 🔴 للأوفلاين (استخدام الإيموجي مباشرة أضمن)
        icon = "🟢" if is_online else "🔴"
        lumps_html += f'<span title="{row.iloc[0]}" style="font-size: 30px;">{icon}</span>'
    
    lumps_html += '</div>'
    st.markdown(lumps_html, unsafe_allow_html=True)
    st.divider()
except Exception as e:
    st.write("📡 جاري تحديث الرادار...")


# --- 4. نظام الطلبات (هون بيرجع يشتغل طبيعي) ---
# كودك الأساسي لجلب الطلبات وفحص الإشعارات بيكمل هون...



# --- نهاية كود الرادار ---

@st.cache_resource
def get_sh():
   
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال بجوجل: {e}"); return None

sh = get_sh()

if sh:
    delegates = [ws.title for ws in sh.worksheets() if ws.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]
    
    # زر الفحص الأحمر
    if st.button("🔔 فحص الإشعارات الجديدة (الطلبات المنتظرة)", use_container_width=True, type="secondary"):
        st.session_state.orders = []
        with st.spinner("جاري فحص ملفات المندوبين..."):
            for rep in delegates:
                try:
                    data = sh.worksheet(rep).get_all_values()
                    if len(data) > 1:
                        header = data[0]
                        idx_status = header.index('الحالة')
                        idx_time = header.index('التاريخ و الوقت') if 'التاريخ و الوقت' in header else -1
                        for row in data[1:]:
                            if row[idx_status] == "بانتظار التصديق":
                                st.session_state.orders.append({"name": rep, "time": row[idx_time] if idx_time != -1 else "---"})
                                break
                except: continue

    # عرض الطلبات كأزرار خضراء كبيرة
    if st.session_state.orders:
        st.markdown("### 📦 طلبات جديدة جاهزة للتجهيز:")
        cols = st.columns(2) # توزيع الكبسات على عمودين
        for i, o in enumerate(st.session_state.orders):
            btn_text = f"المندوب: {o['name']}\n🕒 وقت الإرسال: {o['time']}"
            if cols[i % 2].button(btn_text, key=f"btn_{o['name']}", use_container_width=True):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("اختر المندوب لمراجعة تفاصيل الطلب:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw = ws.get_all_values()
        if len(raw) > 1:
            df = pd.DataFrame(raw[1:], columns=raw[0])
            df.columns = df.columns.str.strip()
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    st.success(f"📂 عرض طلبات المندوب: {selected_rep}")
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    # --- كود الطباعة المحمي (يمين وشمال) ---
                    p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    h_content = ""
                    for tg in edited['الوجهة'].unique():
                        rows = "".join([f"<tr><td>{i+1}</td><td>{r['الكميه المطلوبه']}</td><td style='text-align:right;'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(edited[edited['الوجهة'] == tg].iterrows())])
                        invoice = f'<div style="width: 48%; border: 3px solid black; padding: 10px; box-sizing: border-box;"><h2 style="text-align:center; border-bottom:2px solid black; margin:0 0 5px 0; font-size:20px;">{tg}</h2><div style="display:flex; justify-content:space-between; font-weight:bold; font-size:13px;"><span>المندوب: {selected_rep}</span><span>{p_now}</span></div><table style="width:100%; border-collapse:collapse; margin-top:5px;"><thead><tr><th>ت</th><th>العدد</th><th style="width:60%;">الصنف</th></tr></thead><tbody>{rows}</tbody></table></div>'
                        h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:20px; page-break-inside:avoid;">{invoice}{invoice}</div>'

                    print_html = f"""
                    <script>
                    function doPrint() {{
                        var w = window.open('', '', 'width=1000,height=1000');
                        w.document.write(`<html><head><style>body {{ font-family: Arial; direction: rtl; padding: 5mm; }} th, td {{ border: 2px solid black; padding: 4px; text-align: center; font-size: 16px; font-weight: bold; }} @media print {{ @page {{ size: A4 portrait; margin: 5mm; }} }} </style></head><body>{h_content}<script>setTimeout(function(){{window.print();window.close();}},800);<\\/script></body></html>`);
                        w.document.close();
                    }}
                    </script>
                    <button onclick="doPrint()" style="width:100%; height:60px; background-color:#28a745; color:white; border:none; border-radius:10px; font-weight:bold; font-size:22px; cursor:pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">🖨️ طباعة الفواتير للمراجعة (نسختين)</button>
                    """
                    st.components.v1.html(print_html, height=80)
                    
                    if st.button("🚀 تصديق وإغلاق الطلب نهائياً", type="primary", use_container_width=True):
                        idx = raw[0].index('الحالة') + 1
                        with st.spinner("جاري تصديق الطلب في جوجل شيت..."):
                            for _, r in edited.iterrows():
                                try: ws.update_cell(int(r['row_no']), idx, "تم التصديق"); time.sleep(0.3)
                                except: pass
                        st.success("✅ تم التصديق بنجاح!"); time.sleep(1); st.session_state.orders = []; st.rerun()
