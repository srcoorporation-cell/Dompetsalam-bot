import sqlite3
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
import csv
import io
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from datetime import datetime

# === SETTING ===
TELEGRAM_TOKEN = "ISI_TOKEN_TELEGRAM_BOTMU"
openai.api_key = "ISI_API_KEY_OPENAI"  # optional kalau mau pakai AI

# === DATABASE ===
conn = sqlite3.connect("finance.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS transaksi
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            jenis TEXT, kategori TEXT, jumlah REAL, tanggal TEXT)""")
conn.commit()

# === FUNGSI PARSING DENGAN AI (opsional) ===
def ai_parse(text):
    # Untuk simpel, langsung parsing manual.
    # Bisa diganti dengan GPT buat lebih fleksibel.
    text = text.lower()
    if any(x in text for x in ["gaji", "masuk", "+"]):
        jenis = "pemasukan"
    else:
        jenis = "pengeluaran"

    # cari angka
    jumlah = ''.join([c if c.isdigit() else ' ' for c in text]).split()
    jumlah = int(jumlah[0]) if jumlah else 0

    kategori = "lainnya"
    if "makan" in text: kategori = "makan"
    elif "bensin" in text or "transport" in text: kategori = "transport"
    elif "gaji" in text: kategori = "gaji"

    return jenis, kategori, jumlah

# === SIMPAN TRANSAKSI ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    jenis, kategori, jumlah = ai_parse(text)
    tanggal = datetime.now().strftime("%Y-%m-%d")

    cur.execute("INSERT INTO transaksi (jenis, kategori, jumlah, tanggal) VALUES (?,?,?,?)",
                (jenis, kategori, jumlah, tanggal))
    conn.commit()

    await update.message.reply_text(f"✅ {jenis.title()} Rp{jumlah:,} ({kategori}) dicatat.")

# === SALDO ===
async def saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT SUM(jumlah) FROM transaksi WHERE jenis='pemasukan'")
    pemasukan = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(jumlah) FROM transaksi WHERE jenis='pengeluaran'")
    pengeluaran = cur.fetchone()[0] or 0
    saldo = pemasukan - pengeluaran
    await update.message.reply_text(f"💰 Saldo saat ini: Rp{saldo:,}")

# === EXPORT CSV ===
async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT * FROM transaksi")
    rows = cur.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Jenis", "Kategori", "Jumlah", "Tanggal"])
    writer.writerows(rows)
    output.seek(0)
    await update.message.reply_document(InputFile(io.BytesIO(output.getvalue().encode()), filename="transaksi.csv"))

# === EXPORT EXCEL ===
async def export_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT * FROM transaksi")
    rows = cur.fetchall()
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Jenis", "Kategori", "Jumlah", "Tanggal"])
    for row in rows:
        ws.append(row)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    await update.message.reply_document(InputFile(output, filename="transaksi.xlsx"))

# === EXPORT PDF ===
async def export_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT * FROM transaksi")
    rows = cur.fetchall()
    output = io.BytesIO()
    c = canvas.Canvas(output)
    c.drawString(100, 800, "Laporan Transaksi")
    y = 770
    for row in rows:
        c.drawString(50, y, f"{row[4]} - {row[1]} Rp{row[3]:,.0f} ({row[2]})")
        y -= 20
    c.save()
    output.seek(0)
    await update.message.reply_document(InputFile(output, filename="transaksi.pdf"))

# === MAIN ===
app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("saldo", saldo))
app.add_handler(CommandHandler("exportcsv", export_csv))
app.add_handler(CommandHandler("exportexcel", export_excel))
app.add_handler(CommandHandler("exportpdf", export_pdf))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan...")
app.run_polling()
