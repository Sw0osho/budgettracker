import tkinter as tk
from budget_tracker import BudgetTracker

if __name__ == "__main__":
    root = tk.Tk()
    app = BudgetTracker(root)
    root.mainloop() 