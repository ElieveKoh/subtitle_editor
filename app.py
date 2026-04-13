import tkinter as tk
from tkinter import ttk

def change_language(event):
    selected_language = language_var.get()
    if selected_language == "English":
        label.config(text="Hello! Please select your language.")
    elif selected_language == "Korean":
        label.config(text="안녕하세요! 언어를 선택해주세요.")

# Create the main window
root = tk.Tk()
root.title("Multilingual Support App")

# Variable to hold the selected language
language_var = tk.StringVar(value="English")

# Create a dropdown menu for language selection
language_dropdown = ttk.Combobox(root, textvariable=language_var)
language_dropdown['values'] = ("English", "Korean")
language_dropdown.bind('<<ComboboxSelected>>', change_language)

# Create a label for user instruction
label = tk.Label(root, text="Hello! Please select your language.")

# Arrange the components in the window
language_dropdown.pack(pady=10)
label.pack(pady=10)

# Start the main loop
root.mainloop()