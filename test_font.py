import tkinter as tk
import tkinter.font as tkfont

root = tk.Tk()
print([f for f in tkfont.families() if "Ming" in f])
root.destroy()

# test_chars = "󰀟"
# root = tk.Tk()
# for fam in ("HanaMinA", "HanaMinB"):
#     label = tk.Label(root, text=f"{fam}: {test_chars}", font=(fam, 24))
#     label.pack()
# root.mainloop()

test_chars = "󰀛"
root = tk.Tk()
for fam in ("HanaMinA", "DFKai-SB","MingLiU-ExtB","PMingLiU-ExtB","MingLiU_HKSCS-ExtB"):
    label = tk.Label(root, text=f"{fam}: {test_chars}", font=(fam, 24))
    label.pack()
root.mainloop()

