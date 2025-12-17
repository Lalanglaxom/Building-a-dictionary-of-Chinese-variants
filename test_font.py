import tkinter as tk
import tkinter.font as tkfont

root = tk.Tk()
print([f for f in tkfont.families() if "TW" in f])
root.destroy()

# test_chars = "󰀟"
# root = tk.Tk()
# for fam in ("HanaMinA", "HanaMinB"):
#     label = tk.Label(root, text=f"{fam}: {test_chars}", font=(fam, 24))
#     label.pack()
# root.mainloop()

test_chars = "丟,󰀦,󲷱"
root = tk.Tk()
for fam in ("TW-Sung", "TW-Sung-Ext-B","TW-Sung-Plus",'TW-Kai', 'TW-Kai-Ext-B', 'TW-Kai-Plus'):
    label = tk.Label(root, text=f"{fam}: {test_chars}", font=(fam, 24))
    label.pack()
root.mainloop()

