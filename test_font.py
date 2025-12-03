import tkinter as tk
import tkinter.font as tkfont

root = tk.Tk()
print([f for f in tkfont.families() if "MOE" in f])
root.destroy()

# test_chars = "󰀟"
# root = tk.Tk()
# for fam in ("HanaMinA", "HanaMinB"):
#     label = tk.Label(root, text=f"{fam}: {test_chars}", font=(fam, 24))
#     label.pack()
# root.mainloop()

test_chars = "󰀦"
root = tk.Tk()
for fam in ("BabelStone Han PUA", "TW-MOE-Std-Kai"):
    label = tk.Label(root, text=f"{fam}: {test_chars}", font=(fam, 24))
    label.pack()
root.mainloop()

