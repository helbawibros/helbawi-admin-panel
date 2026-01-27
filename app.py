import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time

# --- 1. إعدادات الصفحة والـ CSS الاحترافي (نسخة إنهاء الأشباح) ---
st.set_page_config(page_title="إدارة حلباوي - النسخة النهائية", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

# تهيئة المتغيرات لضمان عدم ظهور AttributeError
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

st.markdown("""
    <style>
    /* 1. إخفاء محتوى الطباعة عن الشاشة العادية */
    .printable-content { display: none; }
    
    /* 2. تصميم كبسة (فحص الإشعارات) باللون الأحمر */
    div.stButton > button:first-child {
        background-color: #d32f2f !important;
        color: white !important;
        border-radius: 10px !important;
        height: 55px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border: none !important;
    }

    /* 3. زر الطباعة الأخضر */
    .print-button-real {
        display: block; width: 100%; height: 60px; 
        background-color: #28a745; color: white !important; 
        border-radius: 10px; cursor: pointer; font-weight: bold; font-size: 22px; 
        margin-top: 20px; text-align: center; line-height: 60px; border: none;
    }

        @media print {
        /* 1. إخفاء كل شيء في الصفحة بدون استثناء */
        html, body, div, section, header, footer, button, img {
            visibility: hidden !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 2. إظهار منطقة الفواتير ومحتوياتها فقط بقوة z-index */
        .printable-content, .printable-content * {
            visibility: visible !important;
            display: block !important;
        }

        /* 3. تثبيت الفواتير في أعلى الصفحة وإلغاء أي إزاحة */
        .printable-content {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            z-index: 999999 !important;
            background-color: white !important;
        }

        /* 4. إعداد الورقة بالعرض Landscape */
        @page {
            size: A4 landscape;
            margin: 0 !important;
        }

        /* 5. توزيع المربعين جنب بعض */
        .print-row {
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-around !important;
            width: 100% !important;
            padding-top: 15mm !important; /* مسافة بسيطة من حافة الورقة */
        }

        .invoice-box {
            width: 46% !important;
            border: 3px solid black !important;
            padding: 15px !important;
            box-sizing: border-box !important;
        }

        /* 6. تنسيق الجدول ليكون واضح جداً */
        table { width: 100% !important; border-collapse: collapse !important; }
        th, td { 
            border: 2px solid black !important; 
            padding: 8px !important; 
            font-size: 18px !important; 
            font-weight: bold !important;
            color: black !important;
            text-align: center !important;
        }
        h2 { border-bottom: 2px solid black; margin-bottom: 10px; }
    }
    </style>
""", unsafe_allow_html=True)

# تأكد من وجود المتغيرات لتفادي AttributeError (صورة 7)
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

    
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
                                # --- تعديل قسم التصديق والطباعة معاً ---
                    if st.button("🚀 تصديق، طباعة وإرسال النهائي", type="primary", use_container_width=True):
                        # 1. أولاً: تحضير محتوى الطباعة (النافذة الجديدة)
                        print_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                        all_invoices_html = ""
                        
                        for target in edited['الوجهة'].unique():
                            t_df = edited[edited['الوجهة'] == target]
                            rows_html = "".join([
                                f"<tr><td class='col-t'>{i+1}</td><td class='col-qty'>{r['الكميه المطلوبه']}</td><td class='col-name'>{r['اسم الصنف']}</td></tr>" 
                                for i, (_, r) in enumerate(t_df.iterrows())
                            ])
                            
                            # قالب الفاتورة النظيفة
                            inv = f"""
                            <div class="invoice-box">
                                <h2>HELBAWI BROS</h2>
                                <div style='display:flex; justify-content:space-between; font-weight:bold;'>
                                    <span>المندوب: {selected_rep}</span>
                                    <span>الوجهة: {target}</span>
                                </div>
                                <div style='text-align:center; font-size:14px; margin:5px 0;'>{print_now}</div>
                                <table>
                                    <thead><tr><th class='col-t'>ت</th><th class='col-qty'>العدد</th><th class='col-name'>اسم الصنف</th></tr></thead>
                                    <tbody>{rows_html}</tbody>
                                </table>
                            </div>"""
                            # نسختين جنب بعض
                            all_invoices_html += f"<div class='print-row'>{inv} {inv}</div><div style='page-break-after:always;'></div>"

                        # 2. إطلاق نافذة الطباعة (التزكاية)
                        open_print_window(all_invoices_html)
                        
                        # 3. تحديث جوجل شيت (بعد الطباعة)
                        with st.spinner("جاري تصديق البيانات في جوجل شيت..."):
                            idx_status = raw_data[0].index('الحالة') + 1
                            success_count = 0
                            for _, r in edited.iterrows():
                                try:
                                    ws.update_cell(int(r['row_no']), idx_status, "تم التصديق")
                                    success_count += 1
                                    time.sleep(0.3)
                                except Exception as e:
                                    st.error(f"خطأ في السطر {r['row_no']}: {e}")
                            
                            if success_count > 0:
                                st.success(f"✅ تم الطباعة والتصديق بنجاح!")
                                time.sleep(2) # نترك وقت للمستخدم يشوف الرسالة
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
