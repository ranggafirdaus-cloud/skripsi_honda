import pandas as pd
import mysql.connector

# 1. Koneksi ke MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="db_honda"
)
cursor = db.cursor()

# 2. Membaca file dengan pemisah titik koma (;)
try:
    df = pd.read_csv('data_penjualan.csv', sep=';')
    # Membersihkan nama kolom dari spasi tambahan (jika ada)
    df.columns = df.columns.str.strip()
    
    # --- PERBAIKAN FORMAT TANGGAL (PENTING) ---
    # Mengubah format DD/MM/YYYY menjadi YYYY-MM-DD agar diterima MySQL
    df['Tgl'] = pd.to_datetime(df['Tgl'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
    
    print("Data berhasil dimuat. Total baris:", len(df))
except Exception as e:
    print(f"Gagal membaca/memproses file: {e}")
    exit()

# 3. Insert ke database
sql = """INSERT IGNORE INTO transaksi 
         (no_faktur, tgl_transaksi, nama_konsumen, nama_motor, jenis_beli) 
         VALUES (%s, %s, %s, %s, %s)"""

# Menghapus baris kosong (jika ada baris yang isinya NaN/kosong semua)
df = df.dropna(subset=['No Faktur'])

for index, row in df.iterrows():
    try:
        cursor.execute(sql, (
            str(row['No Faktur']), 
            row['Tgl'], 
            str(row['Konsumen']), 
            str(row['Nama Motor']), 
            str(row['Jenis Beli'])
        ))
    except Exception as e:
        print(f"Error di baris {index}: {e}")

db.commit()
cursor.close()
db.close()
print("Selesai! Data berhasil diimport ke database.")