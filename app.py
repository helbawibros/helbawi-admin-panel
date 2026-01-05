import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 1. إعدادات الصفحة والتنسيق الفائق للطباعة ---
st.set_page_config(page_title="إدارة حلباوي إخوان", layout="wide")

# تصميم الطباعة A4 (الاسم يمين، التاريخ يسار، خطوط ضخمة)
st.markdown("""
    <style>
    @media print {
        header, footer, .no-print, [data-testid="stSidebar"] { display: none !important; }
        .print-only { display: block !important; direction: rtl !important; }
        @page { size: A4; margin: 1cm; }
        body { background-color: white !important; font-family: 'Arial', sans-serif; }
        
        .header-box { display: flex; justify-content: space-between; align-items: center; border-bottom: 5px solid black; padding-bottom: 10px; margin-bottom: 30px; }
        .rep-title { font-size: 50px !important; font-weight: bold; text-align: right; }
        .date-title { font-size: 25px !important; text-align: left; }

        .main-table { width: 100%; border-collapse: collapse; border: 4px solid black; }
        .main-table th, .main-table td { border: 4px solid black; padding: 15px; text-align: center; font-weight: bold; }
        
        /* أحجام الخانات المطلوبة */
        .th-qty { width: 80px; font-size: 35px !important; } /* العدد صغير */
        .th-item { font-size: 40px !important; } /* الصنف كبير بالوسط */
        .th-check { width: 120px; font-size: 30px !important; } /* التأكيس */
        
        .td-qty { font-size: 45px !important; }
        .td-item { font-size: 45px !important; text-align: right; padding-right: 20px; }
    }
    .print-only { display: none; }
    </style>
""", unsafe_allow_html=True)

# --- 2. نظام الدخول والربط ---
ADMIN_PASSWORD = "Hlb_Admin_2024" 
if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    st.title("🔐 تسجيل دخول الإدارة")
    pwd = st.text_input("كلمة السر", type="password")
    if st.button("دخول"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else: st.error("خطأ")
    st.stop()

def get_client():
    info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
    creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

client = get_client()
if client:
    spreadsheet = client.open_by_key("1-Abj-Kvbe02az8KYZfQL0eal2arKw_wgjVQdJX06IA0")
    EXCLUDE_SHEETS = ["طلبات", "الأسعار", "البيانات", "الزبائن", "Sheet1"]
    delegates = [sh.title for sh in spreadsheet.worksheets() if sh.title not in EXCLUDE_SHEETS]

    st.markdown('<h1 class="no-print">🏭 لوحة تحكم الإدارة - شركة حلباوي</h1>', unsafe_allow_html=True)

    # --- 3. نظام الإشعارات الذكي (بدون صفحة سوداء) ---
    if st.button("🔔 فحص الطلبات الجديدة", use_container_width=True):
        st.session_state.notifications = []
        with st.spinner("جاري الفحص..."):
            for rep in delegates:
                ws = spreadsheet.worksheet(rep)
                if "بانتظار التصديق" in ws.col_values(4):
                    st.session_state.notifications.append(rep)
                time.sleep(0.1)

    if 'notifications' in st.session_state and st.session_state.notifications:
        for rep_name in st.session_state.notifications:
            col_notif, col_go = st.columns([3, 1])
            col_notif.warning(f"📦 المندوب **{rep_name}** أرسل طلبية جديدة!")
            if col_go.button(f"فتح طلب {rep_name}", key=f"go_{rep_name}"):
                st.session_state.active_rep = rep_name
                st.rerun()

    st.divider()

    # اختيار المندوب
    current_rep = st.session_state.get('active_rep', "-- اختر --")
    selected_rep = st.selectbox("اختر المندوب لمراجعة طلبيته:", ["-- اختر --"] + delegates, 
                                index=(delegates.index(current_rep) + 1 if current_rep in delegates else 0))

    if selected_rep != "-- اختر --":
        ws = spreadsheet.worksheet(selected_rep)
        data = ws.get_all_values()
        df = pd.DataFrame(data[1:], columns=data[0])
        df['row_no'] = range(2, len(df) + 2)
        pending = df[df['الحالة'] == "بانتظار التصديق"].copy()

        if not pending.empty:
            st.markdown(f"### 📑 معالجة طلبية: {selected_rep}")
            edited_df = st.data_editor(pending[['row_no', 'اسم الصنف', 'الكميه المطلوبه']], 
                                      column_config={"row_no": None, "اسم الصنف": "الصنف", "الكميه المطلوبه": "العدد"}, 
                                      hide_index=True, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚀 تصديق وحفظ في الإكسل", type="primary", use_container_width=True):
                    for _, r in edited_df.iterrows():
                        ws.update_cell(int(r['row_no']), 2, r['اسم الصنف'])
                        ws.update_cell(int(r['row_no']), 3, r['الكميه المطلوبه'])
                        ws.update_cell(int(r['row_no']), 4, "تم التصديق")
                    st.success("✅ تم التصديق!")
                    if 'active_rep' in st.session_state: del st.session_state.active_rep
                    st.rerun()
            
            with c2:
                if st.button("🖨️ طباعة فورية A4", use_container_width=True):
                    now = datetime.now().strftime("%Y-%m-%d | %H:%M")
                    rows_html = "".join([f"<tr><td class='td-qty'>{r['الكميه المطلوبه']}</td><td class='td-item'>{r['اسم الصنف']}</td><td></td></tr>" for _, r in edited_df.iterrows()])
                    
                    # قالب الطباعة النهائي
                    st.markdown(f"""
                        <div class="print-only" dir="rtl">
                            <div class="header-box">
                                <div class="rep-title">المندوب: {selected_rep}</div>
                                <div class="date-title">التاريخ: {now}</div>
                            </div>
                            <h1 style="text-align:center; font-size:45px; text-decoration: underline;">طلبية بضاعة للمعمل</h1>
                            <table class="main-table">
                                <thead>
                                    <tr>
                                        <th class="th-qty">العدد</th>
                                        <th class="th-item">اسم الصنف</th>
                                        <th class="th-check">تأكيس</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                            <div style="margin-top:60px; font-size:30px; font-weight:bold;">توقيع الإدارة: ..........................</div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
        else:
            st.info("لا توجد طلبات جديدة لهذا المندوب.")

# خروج
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.clear()
    st.rerun()
