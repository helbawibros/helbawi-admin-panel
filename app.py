import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة وجدول الطباعة "القسري" ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# هذا الجزء هو المسؤول عن جعل الطباعة تطابق الشاشة 100%
st.markdown("""
    <style>
    /* تنسيق الشاشة العادي */
    .report-header { display: none; }

    @media print {
        /* إخفاء كل شيء غير الطلبية */
        header, footer, .no-print, [data-testid="stSidebar"], .stButton, .stSelectbox { 
            display: none !important; 
        }
        
        /* إظهار حاوية الطباعة فقط */
        .print-only { 
            display: block !important; 
            direction: rtl !important; 
            width: 100% !important;
        }

        /* تثبيت الورقة A4 */
        @page { size: A4; margin: 0.5cm; }
        body { background-color: white !important; color: black !important; }

        /* الهيدر: الاسم يمين بخط عملاق - التاريخ يسار */
        .header-print {
            display: flex !important;
            flex-direction: row !important;
            justify-content: space-between !important;
            align-items: baseline !important;
            border-bottom: 10px solid black !important;
            margin-bottom: 30px !important;
            padding-bottom: 10px !important;
            width: 100% !important;
        }
        
        .rep-name-big { 
            font-size: 65px !important; 
            font-weight: 900 !important; 
            margin: 0 !important;
            text-align: right !important;
        }
        
        .date-time-left { 
            font-size: 28px !important; 
            font-weight: bold !important; 
            text-align: left !important;
        }

        /* الجدول الضخم جداً */
        .main-table-print { 
            width: 100% !important; 
            border-collapse: collapse !important; 
            border: 6px solid black !important; 
        }
        
        .main-table-print th, .main-table-print td { 
            border: 6px solid black !important; 
            padding: 15px !important; 
            font-weight: 900 !important; 
            color: black !important;
        }
        
        .th-style { background-color: #ddd !important; font-size: 35px !important; text-align: center !important; }
        .td-qty { font-size: 55px !important; width: 15%; text-align: center !important; }
        .td-item { font-size: 50px !important; width: 60%; text-align: right !important; padding-right: 20px !important; }
        .td-check { width: 25%; } /* خانة التأكيس */
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. الدخول والربط ---
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if not st.session_state.admin_logged_in:
    st.title("🔐 دخول الإدارة")
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == "Hlb_Admin_2024":
            st.session_state.admin_logged_in = True
            st.rerun()
    st.stop()

def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
    creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]]

    # --- الإشعارات ---
    st.markdown('<div class="no-print"><h1>🏭 لوحة الإدارة</h1></div>', unsafe_allow_html=True)
    if st.button("🔔 فحص الإشعارات", use_container_width=True):
        st.session_state.new_orders = []
        for rep in delegates:
            ws = spreadsheet.worksheet(rep)
            data = ws.get_all_values()
            for row in data:
                if len(row) > 3 and row[3] == "بانتظار التصديق":
                    st.session_state.new_orders.append({"name": rep, "time": row[0]})
                    break
            time.sleep(0.1)

    if 'new_orders' in st.session_state:
        for order in st.session_state.new_orders:
            c1, c2 = st.columns([4, 1])
            c1.warning(f"📦 {order['name']} - وصل: {order['time']}")
            if c2.button(f"فتح {order['name']}", key=order['name']):
                st.session_state.active_rep = order['name']
                st.rerun()

    st.divider()

    # --- اختيار المندوب ---
    active = st.session_state.get('active_rep', "-- اختر --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر --"] + delegates, 
                                index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        df = pd.DataFrame(ws.get_all_values())
        df.columns = df.iloc[0]
        df = df[1:].copy()
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            st.write("### تعديل الطلبية الحالية:")
            edited = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], hide_index=True)

            if st.button("🖨️ اضغط هنا للطباعة فوراً", use_container_width=True):
                order_time = pending.iloc[0]['التاريخ و الوقت']
                rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td class='td-check'></td></tr>" for _, r in edited.iterrows()])
                
                # هذا هو الهيكل الذي سيظهر في الطباعة فقط
                st.markdown(f"""
                    <div class="print-only">
                        <div class="header-print">
                            <div class="rep-name-big">{selected_rep}</div>
                            <div class="date-time-left">{order_time}</div>
                        </div>
                        <h1 style="text-align:center; font-size:50px; margin:20px 0;">طلب بضاعة للمعمل</h1>
                        <table class="main-table-print">
                            <thead>
                                <tr>
                                    <th class="th-style" style="width:15%">العدد</th>
                                    <th class="th-style" style="width:60%">اسم الصنف</th>
                                    <th class="th-style" style="width:25%">تأكيس</th>
                                </tr>
                            </thead>
                            <tbody>{rows_html}</tbody>
                        </table>
                        <div style="margin-top:100px; font-size:35px; font-weight:bold; border-top: 4px solid black; display:inline-block; padding-top:10px;">توقيع المستلم</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
        else:
            st.info("لا يوجد طلبات جديدة.")
