import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import pytz 
import time
import urllib.parse

# --- 1. إعدادات الصفحة والستايل ---
st.set_page_config(page_title="Helbawi Admin", layout="wide")
beirut_tz = pytz.timezone('Asia/Beirut')

st.markdown("""
    <style>
    /* تنسيق الأزرار */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #ff4b4b; color: white; border: none;
        box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); font-weight: bold; height: 50px;
    }
    div[data-testid="column"] button {
        background-color: #28a745 !important; color: white !important;
        height: 100px !important; border: 2px solid #1e7e34 !important;
        font-size: 18px !important; white-space: pre-wrap !important;
    }
    .company-title {
        font-family: 'Arial Black', sans-serif;
        color: #D4AF37; text-align: center; font-size: 40px;
        text-shadow: 2px 2px 4px #000000; margin-bottom: 5px;
    }
    
    /* --- ستايل اللمبات الجديد (3D Bubble) --- */
    .status-bar {
        display: flex; justify-content: center; gap: 12px; margin-bottom: 20px;
        background: #161b26; padding: 12px; border-radius: 50px; border: 1px solid #333;
        width: fit-content; margin-left: auto; margin-right: auto;
    }
    .bulb {
        width: 22px; height: 22px; border-radius: 50%;
        box-shadow: inset -2px -2px 5px rgba(0,0,0,0.5), inset 2px 2px 5px rgba(255,255,255,0.5);
        cursor: help; transition: all 0.3s ease;
        border: 1px solid rgba(0,0,0,0.5);
    }
    .bulb:hover { transform: scale(1.3); }
    
    .bulb-on { background: radial-gradient(circle at 30% 30%, #4bff88, #00e676); box-shadow: 0 0 15px #00e676; }
    .bulb-off { background: radial-gradient(circle at 30% 30%, #ff6b6b, #b71c1c); opacity: 0.6; }
    
    /* زر الواتساب الجديد */
    .wa-btn {
        background-color: #25D366; color: white; padding: 15px; text-align: center;
        border-radius: 12px; text-decoration: none; display: block; font-weight: bold; margin-top: 10px;
        font-size: 18px; border: 2px solid #128c7e; transition: 0.3s; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .wa-btn:hover { background-color: #128c7e; transform: scale(1.02); color: white; text-decoration: none; }
    
    </style>
""", unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
if 'orders' not in st.session_state: st.session_state.orders = []

@st.cache_resource
def get_sh():
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"].strip(), strict=False)
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open_by_key("1flePWR4hlSMjVToZfkselaf0M95fcFMtcn_G-KCK3yQ")
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال بجوجل: {e}")
        return None

# --- دوال المساعدة ---

def get_delegate_phone(_sh, name):
    try:
        # 1. يفتح شيت "البيانات"
        ws = _sh.worksheet("البيانات")
        # 2. يبحث عن اسم المندوب في العمود الأول
        cell = ws.find(name.strip())
        if cell: 
            # 3. يعيد القيمة الموجودة في العمود الثاني (B) بجانب الاسم
            return ws.cell(cell.row, 2).value 
        return None
    except: return None

def get_active_status(_sh):
    try:
        ws = _sh.worksheet("Active_Users")
        data = ws.get_all_records()
        status = {}
        now = datetime.now()
        for row in data:
            name = row.get('المندوب') or row.get('User')
            last_time = row.get('آخر_ظهور') or row.get('time')
            try:
                t = datetime.strptime(str(last_time), "%Y-%m-%d %H:%M")
                if (now - t).total_seconds() < 900: 
                    status[str(name).strip()] = True
            except: continue
        return status
    except: return {}

# --- 2. نظام الدخول ---
if not st.session_state.admin_logged_in:
    col_l = st.columns([1, 2, 1])[1]
    with col_l:
        st.markdown("<h2 style='text-align:center;'>تسجيل الدخول</h2>", unsafe_allow_html=True)
        pwd = st.text_input("كلمة السر الخاصة بالإدارة", type="password")
        if st.button("دخول النظام", use_container_width=True):
            if pwd == "Hlb_Admin_2024": 
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("كلمة السر خطأ")
    st.stop()

st.markdown('<div class="company-title">Helbawi Bros</div>', unsafe_allow_html=True)

sh = get_sh()

BLACKLIST = [
    "طلبات", "الأسعار", "الاسعار", "البيانات", "الزبائن", "Sheet1", "Status", 
    "رقم الطلب", "بيانات المندوبين", "المبيعات", "الذمم", "عاجل", 
    "Active_Users", "Item", "Products", "أرشيف"
]

@st.cache_data(ttl=600)
def fetch_delegates(_sh):
    try:
        all_worksheets = _sh.worksheets()
        return [ws.title for ws in all_worksheets if ws.title.strip() not in BLACKLIST]
    except Exception as e:
        return []

if sh:
    delegates = fetch_delegates(sh)
    if not delegates:
        time.sleep(2); st.cache_data.clear(); delegates = fetch_delegates(sh)

    # --- 1. رادار اللمبات ---
    if delegates:
        status_map = get_active_status(sh)
        lights_html = '<div class="status-bar">'
        for rep in delegates:
            is_on = status_map.get(rep.strip())
            state = "bulb-on" if is_on else "bulb-off"
            lights_html += f'<div class="bulb {state}" title="{rep}"></div>'
        lights_html += '</div>'
        st.markdown(lights_html, unsafe_allow_html=True)
    
    st.divider()

    # --- 2. زر الإشعارات ---
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
                                order_time = row[idx_time] if idx_time != -1 else "---"
                                st.session_state.orders.append({"name": rep, "time": order_time})
                                break
                except: continue

    if st.session_state.orders:
        cols = st.columns(len(st.session_state.orders))
        for i, o in enumerate(st.session_state.orders):
            if cols[i].button(f"📦 {o['name']}\n🕒 {o['time']}", key=f"o_{o['name']}"):
                st.session_state.active_rep = o['name']
                st.rerun()

    active = st.session_state.get('active_rep', "-- اختر مندوب --")
    selected_rep = st.selectbox("المندوب المختار:", ["-- اختر مندوب --"] + delegates, index=(delegates.index(active)+1 if active in delegates else 0))

    if selected_rep != "-- اختر مندوب --":
        ws = sh.worksheet(selected_rep)
        raw = ws.get_all_values()
        if len(raw) > 1:
            header = raw[0]
            df = pd.DataFrame(raw[1:], columns=header)
            df.columns = df.columns.str.strip()
            
            if len(df.columns) >= 6:
                df.columns.values[5] = "رقم الطلب"
            
            if 'الحالة' in df.columns:
                df['row_no'] = range(2, len(df) + 2)
                pending = df[df['الحالة'] == "بانتظار التصديق"].copy()
                
                if not pending.empty:
                    pending['الوجهة'] = pending['اسم الزبون'].astype(str).replace(['nan', '', 'None'], 'جردة سيارة').str.strip()
                    
                    cols_to_show = ['row_no', 'رقم الطلب', 'اسم الصنف', 'الكميه المطلوبه', 'الوجهة']
                    display_df = pending[[c for c in cols_to_show if c in pending.columns]]
                    
                    # تعديل الجدول
                    edited = st.data_editor(display_df, hide_index=True, use_container_width=True)
                    
                    # ========================================================
                    # 🔥 كود التقرير الذكي المبوب حسب الوجهة 🔥
                    # ========================================================
                    
                    # 1. تحويل الكميات لأرقام
                    edited['الكميه المطلوبه'] = pd.to_numeric(edited['الكميه المطلوبه'], errors='coerce').fillna(0)

                    # 2. فصل المقبول عن الملغى
                    approved_items = edited[edited['الكميه المطلوبه'] > 0]
                    cancelled_items = edited[edited['الكميه المطلوبه'] <= 0]
                    
                    # 3. بناء نص الرسالة
                    msg_lines = []
                    msg_lines.append(f"📦 *تقرير تحميل: {selected_rep}*")
                    msg_lines.append(f"📅 {datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')}")
                    msg_lines.append("------------------")
                    
                    if not approved_items.empty:
                        msg_lines.append("✅ *تم الموافقة والتحميل:*")
                        
                        # 🔥 التجميع حسب الوجهة 🔥
                        # نأخذ قائمة الوجهات الفريدة (جردة سيارة، Test 2، إلخ)
                        destinations = approved_items['الوجهة'].unique()
                        
                        for dest in destinations:
                            # تصفية الأصناف لهذه الوجهة فقط
                            dest_items = approved_items[approved_items['الوجهة'] == dest]
                            
                            # إضافة عنوان الوجهة
                            msg_lines.append(f"\n*{dest}*")
                            
                            # إضافة الأصناف تحتها
                            for _, row in dest_items.iterrows():
                                line = f"▪️ {row['اسم الصنف']}: *{int(row['الكميه المطلوبه'])}*"
                                msg_lines.append(line)
                    
                    if not cancelled_items.empty:
                        msg_lines.append("\n❌ *ملغى / غير متوفر:*")
                        for _, row in cancelled_items.iterrows():
                            # نظهر الاسم والوجهة في الملغى للتوضيح
                            line = f"▫️ ~{row['اسم الصنف']}~ ({row['الوجهة']})"
                            msg_lines.append(line)
                            
                    msg_lines.append("\n⚠️ *يرجى التأكد من البضاعة قبل الانطلاق*")
                    
                    # دمج الرسالة وتشفيرها
                    final_msg = "\n".join(msg_lines)
                    encoded_msg = urllib.parse.quote(final_msg)
                    
                    # جلب رقم الهاتف
                    phone = get_delegate_phone(sh, selected_rep)
                    
                    # ========================================================

                    # --- HTML Print (الزر الأخضر) ---
                    # (كود الطباعة للمكتب يبقى كما هو)
                    p_now = datetime.now(beirut_tz).strftime('%Y-%m-%d | %I:%M %p')
                    h_content = ""
                    for tg in edited['الوجهة'].unique():
                        curr_rows = edited[edited['الوجهة'] == tg]
                        curr_rows_print = curr_rows[pd.to_numeric(curr_rows['الكميه المطلوبه'], errors='coerce') > 0]
                        if curr_rows_print.empty: continue

                        o_id = curr_rows['رقم الطلب'].iloc[0] if 'رقم الطلب' in curr_rows.columns else "---"
                        rows_html = "".join([f"<tr><td style='width:30px;'>{i+1}</td><td style='text-align:right; padding-right:5px; font-size:14px;'>{r['اسم الصنف']}</td><td style='font-size:16px; font-weight:bold; width:50px;'>{r['الكميه المطلوبه']}</td></tr>" for i, (_, r) in enumerate(curr_rows_print.iterrows())])
                        
                        single_table = f"""
                        <div style="width: 49%; border: 1.5px solid black; padding: 5px; box-sizing: border-box; background-color: white; color: black;">
                            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid black; padding-bottom: 3px; margin-bottom: 5px;">
                                <div style="text-align: right; font-size: 14px; font-weight: bold; width: 33%;">🔢 طلب: {o_id}</div>
                                <div style="text-align: center; font-size: 16px; font-weight: bold; width: 34%;">{tg}</div>
                                <div style="text-align: left; font-size: 11px; width: 33%;">{p_now}</div>
                            </div>
                            <div style="text-align: right; font-size: 12px; margin-bottom: 3px;">👤 المندوب: {selected_rep}</div>
                            <table style="width:100%; border-collapse:collapse; table-layout: fixed;">
                                <thead style="background:#eee;">
                                    <tr>
                                        <th style="width:35px; border:1px solid black; font-size:12px;">ت</th>
                                        <th style="border:1px solid black; text-align:right; padding-right:5px; font-size:12px;">اسم الصنف</th>
                                        <th style="width:55px; border:1px solid black; font-size:12px;">العدد</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                        """
                        h_content += f'<div style="display:flex; justify-content:space-between; margin-bottom:15px; page-break-inside:avoid;">{single_table}{single_table}</div>'
                    
                    # عرض الأزرار
                    col_print, col_wa = st.columns([1, 1])
                    
                    with col_print:
                        final_style = """<style>table, th, td { border: 1px solid black; border-collapse: collapse; padding: 3px; text-align: center; } body { font-family: Arial, sans-serif; margin: 0; padding: 10px; } @media print { .no-print { display: none; } }</style>"""
                        print_html = f"""
                        <script>
                        function doPrint() {{ 
                            var w = window.open('', '', 'width=1000,height=1000'); 
                            w.document.write(`<html><head><title>طباعة</title>{final_style}</head><body dir="rtl"> {h_content} <script>setTimeout(function() {{ window.print(); window.close(); }}, 800);<\\/script></body></html>`); 
                            w.document.close(); 
                        }}
                        </script>
                        <button onclick="doPrint()" style="width:100%; height:80px; background-color:#28a745; color:white; border:none; border-radius:12px; font-weight:bold; font-size:20px; cursor:pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            🖨️ طباعة الورقة للمكتب
                        </button>
                        """
                        st.components.v1.html(print_html, height=100)
                    
                    with col_wa:
                        if phone:
                            wa_url = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_msg}"
                            st.markdown(f'''
                                <a href="{wa_url}" target="_blank" class="wa-btn">
                                    📲 إرسال تقرير التحميل المفصل (واتساب)
                                    <br><span style="font-size:14px; font-weight:normal;">(مبوب حسب الوجهة)</span>
                                </a>
                            ''', unsafe_allow_html=True)
                        else:
                            st.error("⚠️ رقم المندوب غير مسجل في شيت 'البيانات'")

                    st.markdown("---")

                    if st.button("🚀 تصديق وإغلاق الطلب نهائياً", type="primary", use_container_width=True):
                        # تحديد أرقام الأعمدة (الحالة والكمية)
                        idx_status = header.index('الحالة') + 1
                        try: idx_qty = header.index('الكميه المطلوبه') + 1
                        except: idx_qty = header.index('العدد') + 1
                        
                        with st.spinner("جاري التحديث..."):
                            for _, r in edited.iterrows():
                                try:
                                    row_idx = int(r['row_no'])
                                    item_qty = str(r['الكميه المطلوبه']).strip()
                                    
                                    # --- التعديل الجوهري هنا ---
                                    # إذا كانت الكمية صفر أو فارغة:
                                    if item_qty in ["", "0", "None", "nan", "0.0"]:
                                        # 1. نضع الكمية 0 في الشيت (العمود C)
                                        ws.update_cell(row_idx, idx_qty, 0) 
                                        # 2. نغير الحالة لـ "ملغى" (العمود D)
                                        ws.update_cell(row_idx, idx_status, "ملغى")
                                    else:
                                        # إذا الكمية مقبولة:
                                        ws.update_cell(row_idx, idx_qty, r['الكميه المطلوبه'])
                                        ws.update_cell(row_idx, idx_status, "تم التصديق")
                                    
                                    time.sleep(0.5) # زدنا الوقت شوي لضمان الكتابة
                                except Exception as e:
                                    print(e)
                                    continue
                        
                        st.success("✅ تم التصديق! (تم تصفير الكميات الملغية في الشيت)")
                        st.session_state.orders = [o for o in st.session_state.orders if o['name'] != selected_rep]
                        if 'active_rep' in st.session_state: del st.session_state.active_rep
                        time.sleep(1)
                        st.rerun()

# --- 4. قسم الأرشيف (باقي الكود كما هو) ---
st.divider()
st.markdown("<h3 style='text-align:right;'>📁 أرشيف الفواتير المصورة</h3>", unsafe_allow_html=True)

try:
    archive_ws = sh.worksheet("بيانات المندوبين")
    all_data = archive_ws.get_all_values()
    
    if len(all_data) > 1:
        df_raw = pd.DataFrame(all_data[1:]) 
        
        c1, c2 = st.columns(2)
        with c1: search_no = st.text_input("🔍 رقم الفاتورة للبحث", key="final_search_inv")
        with c2: search_rep = st.text_input("👤 اسم المندوب للبحث", key="final_search_rep")

        if st.button("🚀 ابدأ البحث في الأرشيف", use_container_width=True):
            mask_html = df_raw.iloc[:, 6].str.contains("<div", na=False)
            df_filtered = df_raw[mask_html].copy()

            if search_no:
                df_filtered = df_filtered[df_filtered.iloc[:, 2].astype(str).str.strip().str.contains(search_no.strip())]
            if search_rep:
                df_filtered = df_filtered[df_filtered.iloc[:, 4].astype(str).str.contains(search_rep)]

            if not df_filtered.empty:
                invoice_options = []
                for idx, r in df_filtered.iterrows():
                    invoice_options.append(f"📄 #{r[2]} | {r[5]} | {r[3]}")
                
                st.session_state.found_invoices = df_filtered
                st.session_state.invoice_labels = invoice_options[::-1]
            else:
                st.warning("⚠️ لم يتم العثور على فواتير.")
                if 'found_invoices' in st.session_state: del st.session_state.found_invoices

        if 'found_invoices' in st.session_state:
            selected = st.selectbox("👇 اختر الفاتورة:", ["-- اختر --"] + st.session_state.invoice_labels)

            if selected != "-- اختر --":
                inv_id = selected.split('|')[0].replace('📄 #', '').strip()
                target_data = st.session_state.found_invoices[st.session_state.found_invoices.iloc[:, 2].astype(str).str.strip() == inv_id].iloc[0]
                html_content = target_data[6]

                st.markdown("---")
                st.markdown(html_content, unsafe_allow_html=True)
                
                if st.button("🖨️ طباعة النسخة"):
                    p_script = f"""<script>var w=window.open('','','width=900,height=900');w.document.write(`{html_content}`);setTimeout(function(){{w.print();w.close();}},500);</script>"""
                    st.components.v1.html(p_script, height=0)

except Exception as e:
    pass

