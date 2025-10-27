import tkinter as tk

from tkinter import ttk, messagebox, PhotoImage
import sqlite3, os

from tkinter import font
font_fallback = ("Jigmo", "Jigmo2", "Jigmo3", 16)

DB = "dictionary.db"
# fetch variants and image paths
def get_variants(char):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT code FROM summary WHERE char=?;", (char,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return []
    main_code = row[0]
    cur.execute("SELECT variant_char, img_path FROM variants WHERE main_code=?;", (main_code,))
    rows = cur.fetchall()
    conn.close()
    return rows


# search callback
def search_variants():
    char = entry.get().strip()
    if not char:
        messagebox.showwarning("Input", "Please enter a Chinese character.")
        return

    for w in img_frame.winfo_children():
        w.destroy()
    result.set("")

    variants = get_variants(char)
    if not variants:
        messagebox.showinfo("Not Found", f"No variants found for “{char}”.")
        return

    # show all text variants
    text_only = [v for v, path in variants if v and not path]
    if text_only:
        result.set("，".join(text_only))

    # show images underneath
    for _, path in variants:
        if path and os.path.exists(path):
            try:
                img = PhotoImage(file=path)
                lbl = ttk.Label(img_frame, image=img)
                lbl.image = img          # keep reference
                lbl.pack(side="left", padx=4, pady=4)
            except Exception as e:
                ttk.Label(img_frame, text="[image error]").pack(side="left", padx=4)


# GUI
root = tk.Tk()
root.title("Chinese Character Variant Dictionary")
root.geometry("480x400")

style = ttk.Style()
style.configure("TButton", font=("Helvetica", 13))
style.configure("TLabel", font=("Noto Serif CJK TC", 16))

frame = ttk.Frame(root, padding=10)
frame.pack(expand=True, fill="both")

ttk.Label(frame, text="Enter Character:", font=("Noto Serif CJK TC", 16)).pack(pady=(5, 0))
entry = ttk.Entry(frame, font=("Noto Serif CJK TC", 20), justify="center", width=4)
entry.pack(pady=5)
entry.focus()

ttk.Button(frame, text="Search", command=search_variants).pack(pady=5)

result = tk.StringVar()
ttk.Label(frame, textvariable=result,
          font=("Noto Serif CJK TC", 22),
          wraplength=440, justify="center").pack(pady=(15, 5))

# container for image variants
img_frame = ttk.Frame(frame)
img_frame.pack(pady=10)

root.mainloop()