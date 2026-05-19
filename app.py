from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import mysql.connector
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os

app = Flask(__name__)
app.secret_key = 'skripsi_honda_2026'

# --- KONFIGURASI DATABASE HOSTING (CLEVER CLOUD) ---
def get_db_connection():
    # Diubah menjadi False agar otomatis menggunakan database online Clever Cloud saat di hosting
    RUNNING_LOCALLY = False 
    
    if RUNNING_LOCALLY:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="db_honda"
        )
    else:
        # Menghubungkan ke database MySQL gratis dari Clever Cloud kamu
        return mysql.connector.connect(
            host="bivmbejmj20pxb65thrq-mysql.services.clever-cloud.com",
            user="u4qp8avyytlqfmbv",
            password="G6DdX4m5Dy85JGVuhiOz",  # <--- Ganti ini dengan password aslimu
            database="bivmbejmj20pxb65thrq",
            port=3306
        )

# --- FUNGSI HELPER HARGA ---
def get_harga(nama):
    n = str(nama).upper()
    if 'VARIO' in n: return 27000000
    if 'BEAT' in n: return 18000000
    if 'SCOOPY' in n: return 22000000
    if 'PCX' in n: return 33000000
    return 20000000

# --- RUTE LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        return "Login Gagal!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    df = pd.read_sql("SELECT jenis_beli, nama_motor FROM transaksi", conn)
    conn.close()
    cash = int(df['jenis_beli'].value_counts().get('Cash', 0))
    kredit = int(df['jenis_beli'].value_counts().get('Kredit', 0))
    top_motor = df['nama_motor'].value_counts().head(5).reset_index()
    top_motor.columns = ['nama_motor', 'jumlah']
    return render_template('index.html', cash=cash, kredit=kredit, top_motor=top_motor.to_dict(orient='records'))

@app.route('/cluster', methods=['POST'])
def cluster():
    if not session.get('logged_in'): return redirect(url_for('login'))
    k = int(request.form.get('jumlah_k', 3))
    session['last_k'] = k 
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT no_faktur, nama_konsumen, jenis_beli, nama_motor FROM transaksi", conn)
    conn.close()
    
    df['jenis_num'] = df['jenis_beli'].map({'Cash': 1, 'Kredit': 0}).fillna(0)
    df['harga_estimasi'] = df['nama_motor'].apply(get_harga)
    
    scaler = StandardScaler()
    features = scaler.fit_transform(df[['jenis_num', 'harga_estimasi']])
    model = KMeans(n_clusters=k, random_state=42, n_init="auto")
    df['cluster_label'] = model.fit_predict(features)
    
    # --- LOGIKA TAMBAHAN IDE 1 & 3 ---
    
    # 1. Rata-rata Harga per Klaster
    analisis_df = df.groupby('cluster_label').agg({
        'jenis_num': 'mean', 
        'harga_estimasi': 'mean'
    }).reset_index()
    analisis_df.columns = ['cluster', 'persentase_cash', 'rata_rata_harga']
    
    # 2. Motor Favorit per Klaster
    motor_per_klaster = []
    for c in sorted(df['cluster_label'].unique()):
        counts = df[df['cluster_label'] == c]['nama_motor'].value_counts()
        if not counts.empty:
            top_motor_name = counts.idxmax()
            top_motor_count = int(counts.max())
            motor_per_klaster.append({
                'cluster': int(c),
                'motor': top_motor_name,
                'jumlah': top_motor_count
            })

    # Data untuk Chart.js
    chart_labels = analisis_df['cluster'].tolist()
    chart_harga = analisis_df['rata_rata_harga'].tolist()
    
    return render_template('hasil.html', 
                           data=df.to_dict(orient='records'), 
                           k=k, 
                           analisis=analisis_df.to_dict(orient='records'),
                           chart_labels=chart_labels,
                           chart_harga=chart_harga,
                           motor_per_klaster=motor_per_klaster)

@app.route('/detail_cluster/<int:cluster_id>')
def detail_cluster(cluster_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    k = session.get('last_k', 3)
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT no_faktur, nama_konsumen, jenis_beli, nama_motor FROM transaksi", conn)
    conn.close()
    df['jenis_num'] = df['jenis_beli'].map({'Cash': 1, 'Kredit': 0}).fillna(0)
    df['harga_estimasi'] = df['nama_motor'].apply(get_harga)
    
    features = StandardScaler().fit_transform(df[['jenis_num', 'harga_estimasi']])
    df['cluster_label'] = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(features)
    
    detail_data = df[df['cluster_label'] == cluster_id].to_dict(orient='records')
    return render_template('detail.html', data=detail_data, cluster_id=cluster_id)

if __name__ == '__main__':
    # Saat running di local laptop menggunakan debug=True
    app.run(debug=True)