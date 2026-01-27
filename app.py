import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time

# --- 1. إعدادات الصفحة والـ CSS الاحترافي (تنظيف كامل) ---
st.set_page_config(page_title="إدارة حلباوي - نسخة المقاسات الدقيقة", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    /* 1. إخفاء محتوى الطباعة عن الشاشة العادية */
    .printable-content { display: none; }
    
    /* 2. صبغ كبسة (فحص الإشعارات) باللون الأحمر القوي */
    div.stButton > button:first-child {
        background-color: #d32f2f !important;
        color: white !important;
        border-radius: 10px !important;
        height: 55px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border: none !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2) !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #b71c1c !important;
        color: white !important;
    }

    /* 3. زر الطباعة الأخضر */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 22px; 
        margin-top: 20px; text-align: center; line-height: 60px; border: none;
    }

        @media print {
        /* 1. إخفاء مطلق لكل عناصر الموقع والشاشة والـ Editor */
        [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"],
        footer, header, .no-print, .stButton, .stDataEditor, 
        [data-testid="stVerticalBlock"] > div:not(.printable-content), 
        img, h2, h1, h3 {
            display: none !important;
        }
        
        /* 2. إظهار المحتوى المخصص للطباعة فقط وتثبيته فوق كل شيء */
        .printable-content { 
            display: block !important; 
            visibility: visible !important;
            position: fixed !important; /* تثبيت فوق كل "الأشباح" */
            top: 0 !important; 
            left: 0 !important; 
            width: 100% !important;
            height: 100% !important;
            background-color: white !important;
            z-index: 9999999 !important;
        }

        /* 3. إعداد الصفحة بالعرض (Landscape) - هيدا سر النجاح */
        @page { 
            size: A4 landscape; 
            margin: 0 !important; 
        }
        
        /* 4. توزيع النسختين جنب بعض */
        .print-row {
            display: flex !important; 
            flex-direction: row !important;
            justify-content: space-around !important; 
            width: 100% !important;
            padding-top: 15mm !important;
            gap: 10px !important;
        }

        .invoice-box {
            width: 47% !important;
            border: 3px solid black !important; 
            padding: 10px !important;
            background-color: white !important;
        }

        table { width: 100% !important; border-collapse: collapse !important; }
        th, td { 
            border: 2px solid black !important; 
            padding: 8px !important; 
            font-size: 18px !important; 
            font-weight: bold !important;
            color: black !important;
        }
    }
    </style>
""", unsafe_allow_html=True)




# --- 2. الدخول واللوغو ---
def show_full_logo():
    # قائمة بأسماء الملفات المحتملة مع مراعاة الفراغ اللي عندك
    possible_names = ["Logo .JPG", "Logo.JPG", "logo.jpg", "Logo .png", "Logo.png"]
    found = False
    for name in possible_names:
        if os.path.exists(name):
            try:
                with open(name, "rb") as f:
                    image_data = f.read()
                st.image(image_data, use_container_width=True)
                found = True
                break
            except:
                continue
    
    if not found:
        # إذا ما لقى الصورة بيعرض النص الاحتياطي
        st.markdown("<h1 style='text-align:center; color:#d32f2f;'>PRIMUM QUALITY</h1>", unsafe_allow_html=True)


if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    show_full_logo()
    col = st.columns([1, 2, 1])[1]
    with col:
        pwd = st.text_input("كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Hlb_Admin_2024":
                st.session_state.admin_logged_in = True; st.rerun()
    st.stop()

# --- 3. الربط مع جوجل شيت ---
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
    
    # --- التعديل الجوهري هون ---
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    
    # هون بنقله: إذا كنت داخل (يعني admin_logged_in = True) اعرض النص فقط
    if st.session_state.admin_logged_in:
        st.markdown("<h2 style='text-align:center; color:#1a5f7a; margin-top:-30px;'>🏢 HELBAWI BROS</h2>", unsafe_allow_html=True)
    # --------------------------

    if st.button("🔔 فحص الإشعارات الجديدة", use_container_width=True):
         
        st.session_state.orders = []
        for rep in delegates:
            try:
                ws = spreadsheet.worksheet(rep)
                data = ws.get_all_values()
                if len(data) > 1:
                    df_t = pd.DataFrame(data[1:], columns=data[0])
                    df_t.columns = df_t.columns.str.strip()
                    if 'الحالة' in df_t.columns:
                        p = df_t[df_t['الحالة'] == "بانتظار التصديق"]
                        if not p.empty:
                            st.session_state.orders.append({"name": rep, "time": p.iloc[0].get('التاريخ و الوقت', '---')})
            except: continue

        # استكمالاً للقسم السابق: عرض المندوبين والطلبات
    if 'orders' in st.session_state and st.session_state.orders:
        for o in st.session_state.orders:
            # كبسات حمراء للطلبات الجديدة
            if st.button(f"📦 طلب من: {o['name']} | 🕒 أرسل: {o['time']}", key=f"btn_{o['name']}", use_container_width=True):
                st.session_state.active_rep = o['name']; st.rerun()
    
    # اختيار المندوب يدوياً
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, 
                                index=(delegates.index(st.session_state.get('active_rep', ""))+1 
    if st.session_state.get('active_rep', "") in delegates else 0))
    st.markdown('</div>', unsafe_allow_html=True) # نهاية منطقة الـ no-print

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
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    
                    st.markdown('<div class="no-print">', unsafe_allow_html=True)
                    # تعديل الكميات قبل التصديق
                    edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']], hide_index=True, use_container_width=True)
                    
                    if st.button("🚀 تصديق وإرسال النهائي", type="primary", use_container_width=True):
                        with st.spinner("جاري تحديث البيانات في جوجل شيت..."):
                            idx_status = raw_data[0].index('الحالة') + 1
                            success_count = 0
                            
                            for _, r in edited.iterrows():
                                try:
                                    # تحديث الحالة إلى "تم التصديق" لكل سطر تم اختياره
                                    ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                                    success_count += 1
                                    time.sleep(0.3) # تأخير بسيط لتجنب حظر جوجل (API Limit)
                                except Exception as e:
                                    st.error(f"خطأ في السطر {r['row_no']}: {e}")
                            
                            if success_count > 0:
                                st.success(f"✅ تم تصديق {success_count} صنف بنجاح!")
                                time.sleep(1)
                                # مسح الذاكرة المؤقتة وإعادة التشغيل لتحديث القائمة
                                st.session_state.orders = [] 
                                st.rerun()


                    # --- هندسة الطباعة (النسختين جنب بعض) ---
                    print_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    all_invoices_html = ""
                    for target in edited['الوجهة'].unique():
                        t_df = edited[edited['الوجهة'] == target]
                        # بناء الأسطر مع الترقيم اللي عملناه i+1
                        rows = "".join([f"<tr><td class='col-id'>{i+1}</td><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-name'>{r['اسم الصنف']}</td></tr>" for i, (_, r) in enumerate(t_df.iterrows())])
                        
                        # تصميم الفاتورة (النسخة الواحدة)
                        inv = f"""
                        <div class="invoice-box">
                            <h2 style='text-align:center; border-bottom:1px solid black;'>HELBAWI BROS</h2>
                            <h3 style='text-align:center; margin:5px 0;'>{"طلب: " + target if target != "جردة سيارة" else "جردة: " + selected_rep}</h3>
                            <div class="info-bar"><span>المندوب: {selected_rep}</span><span>{print_now}</span></div>
                            <table>
                                <thead><tr><th class="col-id">ت</th><th class="col-qty">العدد</th><th class="col-name">اسم الصنف</th></tr></thead>
                                <tbody>{rows}</tbody>
                            </table>
                        </div>"""
                        # وضع النسختين جنب بعض في سطر واحد للطباعة
                        all_invoices_html += f'<div class="print-row">{inv}{inv}</div>'
                    
                    # عرض المحتوى المخفي المخصص للطباعة فقط
                    st.markdown(f'<div class="printable-content">{all_invoices_html}</div>', unsafe_allow_html=True)
                    # زر الطباعة الذي يظهر على الشاشة فقط
                    st.markdown('<button onclick="window.print()" class="print-button-real no-print">🖨️ طباعة الفواتير (A4 Landscape)</button>', unsafe_allow_html=True)
