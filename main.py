import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# Sample dictionary of variants
chinese_variants = {
    '你': ['妳', '祢'],
    '好': ['好'],
    '中': ['仲', '忠']
}

def search_variants():
    char = entry.get()
    variants = chinese_variants.get(char, [])
    if variants:
        result.set(", ".join(variants))
    else:
        messagebox.showinfo("Not Found", "No variants found for this character.")

# Create main window
root = tk.Tk()
root.title("Chinese Character Variant Dictionary")
root.geometry("400x200")

# Use themed ttk styles
style = ttk.Style()
style.configure("TButton", font=("Helvetica", 12))
style.configure("TLabel", font=("Helvetica", 14))

# Layout management
frame = ttk.Frame(root, padding="10")
frame.pack(expand=True)

# Entry and button
entry = ttk.Entry(frame, font=("Helvetica", 14))
entry.pack(pady=10)

button = ttk.Button(frame, text="Search", command=search_variants)
button.pack(pady=5)

# Result display
result = tk.StringVar()
result_label = ttk.Label(frame, textvariable=result, font=("Helvetica", 14), wraplength=350)
result_label.pack(pady=20)

root.mainloop()