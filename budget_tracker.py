import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import tempfile
from calendar import monthrange
from datetime import datetime, timedelta
import requests
from functools import lru_cache
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class CurrencyConverter:
    def __init__(self):
        self.base_url = "https://api.exchangerate-api.com/v4/latest/"
        self.currencies = {
            'CZK': 'CZK',
            'USD': '$',
            'EUR': '€'
        }
        self.default_currency = 'CZK'
        self.rates = {}
        self.last_update = None
        self.update_rates()

    @lru_cache(maxsize=128)
    def get_rate(self, from_currency, to_currency, date=None):
        if from_currency == to_currency:
            return 1.0
        
        if self.last_update is None or datetime.now() - self.last_update > timedelta(hours=1):
            self.update_rates()
            
        try:
            if from_currency == self.default_currency:
                return self.rates.get(to_currency, 1.0)
            elif to_currency == self.default_currency:
                return 1.0 / self.rates.get(from_currency, 1.0)
            else:
                # Convert through USD
                return (1.0 / self.rates.get(from_currency, 1.0)) * self.rates.get(to_currency, 1.0)
        except:
            return 1.0

    def update_rates(self):
        try:
            response = requests.get(f"{self.base_url}{self.default_currency}")
            data = response.json()
            self.rates = data['rates']
            self.last_update = datetime.now()
        except:
            print("Failed to update exchange rates")

    def format_amount(self, amount, currency):
        symbol = self.currencies.get(currency, '$')
        formatted_amount = "{:,.2f}".format(amount)  # Add commas to the number
        if currency == 'CZK':
            return f"{formatted_amount} {symbol}"
        return f"{symbol}{formatted_amount}"

    def convert_amount(self, amount, from_currency, to_currency):
        rate = self.get_rate(from_currency, to_currency)
        return amount * rate

class Transaction:
    def __init__(self, amount, type_, category="", description="", date=None, currency="CZK"):
        self.id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.amount = float(amount)
        self.type = type_
        self.category = category
        self.description = description
        self.date = date if date else datetime.now().strftime("%Y-%m-%d")
        self.currency = currency

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'type': self.type,
            'category': self.category,
            'description': self.description,
            'date': self.date,
            'currency': self.currency
        }

class BudgetTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Budget Tracker")
        self.root.geometry("800x600")
        
        # Initialize currency converter and preferred currency before other variables
        self.currency_converter = CurrencyConverter()
        self.preferred_currency = tk.StringVar(value="CZK")  # Set default to CZK
        
        # Rest of initialization remains the same...
        self.transactions = []
        self.selected_items = []
        self.editing = False
        self.edit_index = None
        self.custom_category_var = tk.StringVar()
        self.showing_graphs = False
        self.graphs_frame = None
        self.transactions_frame = None
        self.default_categories = ['', 'salary', 'food', 'rent', 'utilities', 'entertainment', 'other']
        
        # Initialize storage variables
        self.budgets = {}
        self.savings_goals = {}
        
        # Load all data first
        self.load_budgets()
        self.load_transactions()
        self.initialize_savings_goals()
        
        # Then create all widgets
        self.create_widgets()
        self.create_savings_frame()
        
        # Finally update display
        self.update_display()

    def initialize_savings_goals(self):
        """Initialize savings goals with fresh data from file"""
        print("Initializing savings goals...")  # Debug print
        self.savings_goals = {}  # Clear existing goals
        
        try:
            if os.path.exists('savings_goals.json'):
                print("Found savings_goals.json")  # Debug print
                with open('savings_goals.json', 'r') as f:
                    print("Current file contents:")  # Debug print
                    content = f.read()
                    print(content)  # Debug print
                    f.seek(0)  # Reset file pointer
                    
                    data = json.load(f)
                    print("Loaded goals:", data)  # Debug print
                    
                    # Verify each goal's data structure
                    for name, goal in data.items():
                        if all(key in goal for key in ['target', 'current', 'monthly', 'deadline', 'contributions']):
                            self.savings_goals[name] = goal
                            print(f"Added valid goal: {name}")  # Debug print
                        else:
                            print(f"Skipped invalid goal: {name}")  # Debug print
                    
                print("Final savings_goals:", self.savings_goals)  # Debug print
                
                # Force rewrite the file with only valid goals
                self.save_savings_goals()
                
                # Verify the file was rewritten correctly
                with open('savings_goals.json', 'r') as f:
                    print("File contents after save:")  # Debug print
                    print(f.read())  # Debug print
                    
            else:
                print("No savings_goals.json found, creating new file")  # Debug print
                self.save_savings_goals()
                
        except Exception as e:
            print(f"Error in initialize_savings_goals: {str(e)}")  # Debug print
            self.savings_goals = {}
            self.save_savings_goals()

        # Final verification
        print("Final savings goals state:", self.savings_goals)  # Debug print

    def create_widgets(self):
        # Create Menu Bar
        self.menu_bar = ttk.Frame(self.root)
        self.menu_bar.pack(fill="x", padx=10, pady=5)

        # Create left side frame for navigation buttons
        nav_frame = ttk.Frame(self.menu_bar)
        nav_frame.pack(side="left")

        # Add menu buttons to nav_frame
        self.transactions_button = ttk.Button(
            nav_frame,
            text="Transactions",
            command=self.show_transactions,
            style='Selected.TButton'
        )
        self.transactions_button.pack(side="left", padx=5)

        self.analytics_button = ttk.Button(
            nav_frame,
            text="Analytics",
            command=self.show_analytics,
            style='Unselected.TButton'
        )
        self.analytics_button.pack(side="left", padx=5)

        self.budgets_button = ttk.Button(
            nav_frame,
            text="Budgets",
            command=self.show_budgets,
            style='Unselected.TButton'
        )
        self.budgets_button.pack(side="left", padx=5)

        self.savings_button = ttk.Button(
            nav_frame,
            text="Savings Goals",
            command=self.show_savings,
            style='Unselected.TButton'
        )
        self.savings_button.pack(side="left", padx=5)

        # Add refresh button to right side of menu bar
        self.refresh_button = ttk.Button(
            self.menu_bar,
            text="↻ Refresh",
            command=self.refresh_data
        )
        self.refresh_button.pack(side="right", padx=5)

        # Create button styles
        style = ttk.Style()
        style.configure('Selected.TButton', background='lightblue', font=('Arial', 10, 'bold'))
        style.configure('Unselected.TButton', font=('Arial', 10))

        # Input Frame
        input_frame = ttk.LabelFrame(self.root, text="Add Transaction", padding="10")
        input_frame.pack(fill="x", padx=10, pady=5)

        # Date (Required)
        ttk.Label(input_frame, text="Date:*").grid(row=0, column=0, padx=5, pady=5)
        self.date_entry = DateEntry(input_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2,
                                  date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)

        # Amount (Required)
        ttk.Label(input_frame, text="Amount:*").grid(row=0, column=2, padx=5, pady=5)
        self.amount_entry = ttk.Entry(input_frame)
        self.amount_entry.grid(row=0, column=3, padx=5, pady=5)

        # Type (Required)
        ttk.Label(input_frame, text="Type:*").grid(row=0, column=4, padx=5, pady=5)
        self.type_var = tk.StringVar(value="income")
        type_combo = ttk.Combobox(input_frame, textvariable=self.type_var)
        type_combo['values'] = ('income', 'expense')
        type_combo['state'] = 'readonly'
        type_combo.grid(row=0, column=5, padx=5, pady=5)

        # Category (Optional)
        ttk.Label(input_frame, text="Category:").grid(row=1, column=0, padx=5, pady=5)
        self.category_var = tk.StringVar(value="")
        self.category_combo = ttk.Combobox(input_frame, textvariable=self.category_var)
        self.category_combo['values'] = self.default_categories  # Use default categories
        self.category_combo['state'] = 'readonly'
        self.category_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Custom category entry (hidden by default)
        self.custom_category_entry = ttk.Entry(input_frame, textvariable=self.custom_category_var)
        self.custom_category_entry.grid(row=1, column=1, padx=5, pady=5)
        self.custom_category_entry.grid_remove()

        # Bind category selection event
        self.category_combo.bind('<<ComboboxSelected>>', self.on_category_change)

        # Description (Optional)
        ttk.Label(input_frame, text="Description:").grid(row=1, column=2, padx=5, pady=5)
        self.description_entry = ttk.Entry(input_frame)
        self.description_entry.grid(row=1, column=3, padx=5, pady=5)

        # Required fields note
        ttk.Label(input_frame, text="* Required fields", font=('Arial', 8)).grid(row=2, column=0, columnspan=4, pady=(0, 5))

        # Add Button
        self.action_button = ttk.Button(input_frame, text="Add Transaction", command=self.add_transaction)
        self.action_button.grid(row=3, column=0, columnspan=4, pady=5)

        # Add Cancel Button (hidden by default)
        self.cancel_button = ttk.Button(input_frame, text="Cancel", command=self.cancel_edit)
        self.cancel_button.grid(row=3, column=2, columnspan=2, pady=5)
        self.cancel_button.grid_remove()

        # Summary Frame
        self.summary_frame = ttk.LabelFrame(self.root, text="Summary", padding="10")
        self.summary_frame.pack(fill="x", padx=10, pady=5)

        # Balance, Income, and Expenses labels in a separate frame
        labels_frame = ttk.Frame(self.summary_frame)
        labels_frame.pack(side="left", expand=True)
        
        self.balance_label = ttk.Label(labels_frame, text="Balance: $0")
        self.balance_label.pack(side="left", expand=True)
        
        self.income_label = ttk.Label(labels_frame, text="Income: $0")
        self.income_label.pack(side="left", expand=True)
        
        self.expenses_label = ttk.Label(labels_frame, text="Expenses: $0")
        self.expenses_label.pack(side="left", expand=True)

        # Create export frame and buttons
        export_frame = ttk.Frame(self.summary_frame)
        export_frame.pack(side="right", padx=10)
        
        # Add export button
        self.export_button = ttk.Button(
            export_frame,
            text="Export PDF",
            command=self.export_pdf
        )
        self.export_button.pack(side="left", padx=5)

        # Create container for switchable frames
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Create transactions frame
        self.create_transactions_frame()
        
        # Create graphs frame (but don't show it yet)
        self.create_graphs_frame()

        # Add budgets frame creation
        self.create_budgets_frame()

        # Add currency settings to the menu bar
        settings_frame = ttk.Frame(self.menu_bar)
        settings_frame.pack(side="right", padx=5)
        
        ttk.Label(settings_frame, text="Default Currency:").pack(side="left", padx=5)
        currency_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.preferred_currency,
            values=list(self.currency_converter.currencies.keys()),
            state='readonly',
            width=5
        )
        currency_combo.pack(side="left", padx=5)
        currency_combo.bind('<<ComboboxSelected>>', self.on_currency_change)

        # Add currency selection to transaction input
        self.transaction_currency = tk.StringVar(value="USD")
        ttk.Label(input_frame, text="Currency:").grid(row=0, column=6, padx=5, pady=5)
        currency_select = ttk.Combobox(
            input_frame,
            textvariable=self.transaction_currency,
            values=list(self.currency_converter.currencies.keys()),
            state='readonly',
            width=5
        )
        currency_select.grid(row=0, column=7, padx=5, pady=5)

    def create_transactions_frame(self):
        self.transactions_frame = ttk.LabelFrame(self.main_container, text="Transactions", padding="10")
        self.transactions_frame.pack(fill="both", expand=True)

        # Move Treeview to transactions frame
        columns = ('date', 'type', 'category', 'description', 'amount')
        self.tree = ttk.Treeview(self.transactions_frame, columns=columns, show='headings', selectmode='extended')
        
        # Define headings
        self.tree.heading('date', text='Date')
        self.tree.heading('type', text='Type')
        self.tree.heading('category', text='Category')
        self.tree.heading('description', text='Description')
        self.tree.heading('amount', text='Amount')

        # Define column widths
        self.tree.column('date', width=100)
        self.tree.column('type', width=100)
        self.tree.column('category', width=100)
        self.tree.column('description', width=200)
        self.tree.column('amount', width=100)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.transactions_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack the treeview and scrollbar
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind right-click event and selection event
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Create context menus
        self.single_item_menu = tk.Menu(self.root, tearoff=0)
        self.single_item_menu.add_command(label="Edit", command=self.edit_transaction)
        self.single_item_menu.add_command(label="Delete", command=self.delete_transactions)

        self.multi_item_menu = tk.Menu(self.root, tearoff=0)
        self.multi_item_menu.add_command(label="Delete Selected", command=self.delete_transactions)

    def create_graphs_frame(self):
        self.graphs_frame = ttk.LabelFrame(self.main_container, text="Analytics", padding="10")
        
        # Create figure with subplots
        self.fig = plt.Figure(figsize=(12, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graphs_frame)
        
        # Create frame for the canvas
        canvas_frame = ttk.Frame(self.graphs_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        # Pack the canvas
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def update_graphs(self):
        self.fig.clear()
        
        # Create three subplots
        balance_ax = self.fig.add_subplot(131)
        expense_ax = self.fig.add_subplot(132)
        category_ax = self.fig.add_subplot(133)

        # Get currency symbol for labels
        currency_symbol = self.currency_converter.currencies[self.preferred_currency.get()]

        # Balance over time
        dates = []
        balances = []
        running_balance = 0
        
        # Sort transactions by date
        sorted_transactions = sorted(self.transactions, key=lambda x: x.date)
        
        for t in sorted_transactions:
            dates.append(datetime.strptime(t.date, "%Y-%m-%d"))
            # Convert amount to preferred currency
            converted_amount = self.currency_converter.convert_amount(
                t.amount,
                t.currency,
                self.preferred_currency.get()
            )
            if t.type == 'income':
                running_balance += converted_amount
            else:
                running_balance -= converted_amount
            balances.append(running_balance)

        if dates:  # Only plot if there are transactions
            balance_ax.plot(dates, balances, 'b-')
            balance_ax.set_title('Balance Over Time')
            balance_ax.set_xlabel('Date')
            balance_ax.set_ylabel(f'Balance ({currency_symbol})')
            balance_ax.tick_params(axis='x', rotation=45)

        # Income vs Expenses
        income = sum(
            self.currency_converter.convert_amount(t.amount, t.currency, self.preferred_currency.get())
            for t in self.transactions if t.type == 'income'
        )
        expenses = sum(
            self.currency_converter.convert_amount(t.amount, t.currency, self.preferred_currency.get())
            for t in self.transactions if t.type == 'expense'
        )
        
        expense_ax.bar(['Income', 'Expenses'], [income, expenses], color=['g', 'r'])
        expense_ax.set_title('Income vs Expenses')
        expense_ax.set_ylabel(f'Amount ({currency_symbol})')

        # Format y-axis labels with currency symbol for both graphs
        def format_amount(x, p):
            return f'{currency_symbol}{x:,.0f}'
        
        balance_ax.yaxis.set_major_formatter(plt.FuncFormatter(format_amount))
        expense_ax.yaxis.set_major_formatter(plt.FuncFormatter(format_amount))

        # Expenses by category
        category_expenses = defaultdict(float)
        for t in self.transactions:
            if t.type == 'expense':
                # Convert amount to preferred currency
                converted_amount = self.currency_converter.convert_amount(
                    t.amount,
                    t.currency,
                    self.preferred_currency.get()
                )
                category_expenses[t.category or 'Uncategorized'] += converted_amount

        if category_expenses:  # Only plot if there are expenses
            categories = list(category_expenses.keys())
            amounts = list(category_expenses.values())
            
            # Sort by amount for better visualization
            sorted_data = sorted(zip(categories, amounts), key=lambda x: x[1], reverse=True)
            categories, amounts = zip(*sorted_data)
            
            # Create custom labels with amounts
            total = sum(amounts)
            labels = [f'{cat}\n({currency_symbol}{amt:.2f})' for cat, amt in zip(categories, amounts)]
            
            category_ax.pie(amounts, labels=labels, autopct='%1.1f%%')
            category_ax.set_title('Expenses by Category')

        # Adjust layout and display
        self.fig.tight_layout()
        self.canvas.draw()

    def export_pdf(self):
        try:
            # Get current date and time for filename and report
            export_date = datetime.now()
            formatted_date = export_date.strftime("%Y-%m-%d")
            formatted_datetime = export_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Create default filename with date
            default_filename = f"Balance Report of {formatted_date}.pdf"
            
            # Ask user where to save the PDF
            file_path = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                title="Save PDF Report"
            )
            
            if not file_path:  # If user cancels the dialog
                return

            # Create the PDF document
            doc = SimpleDocTemplate(
                file_path,
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=36,
                bottomMargin=36
            )

            elements = []

            # Add title and date
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                fontName='Helvetica-Bold'
            )
            
            # Define summary style
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=12,
                fontName='Helvetica'
            )

            elements.append(Paragraph("Budget Report", title_style))
            
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                spaceAfter=20,
                fontName='Helvetica'
            )
            elements.append(Paragraph(f"Generated on: {formatted_datetime}", date_style))
            elements.append(Spacer(1, 20))

            # Function to create a KeepTogether block for graph and its title
            def add_graph_section(title, image_path, width, height):
                if os.path.exists(image_path):
                    graph_section = []
                    graph_section.append(Paragraph(title, styles['Heading2']))
                    graph_section.append(Spacer(1, 12))
                    graph_section.append(Image(image_path, width=width, height=height))
                    elements.append(KeepTogether(graph_section))
                    elements.append(Spacer(1, 20))

            # Get currency symbol for formatting
            currency_symbol = self.currency_converter.currencies[self.preferred_currency.get()]

            # Convert amounts to preferred currency for summary
            total_income = sum(
                self.currency_converter.convert_amount(t.amount, t.currency, self.preferred_currency.get())
                for t in self.transactions if t.type == 'income'
            )
            total_expenses = sum(
                self.currency_converter.convert_amount(t.amount, t.currency, self.preferred_currency.get())
                for t in self.transactions if t.type == 'expense'
            )
            balance = total_income - total_expenses

            elements.append(Paragraph(f"Balance: {currency_symbol}{balance:.2f}", summary_style))
            elements.append(Paragraph(f"Total Income: {currency_symbol}{total_income:.2f}", summary_style))
            elements.append(Paragraph(f"Total Expenses: {currency_symbol}{total_expenses:.2f}", summary_style))
            elements.append(Spacer(1, 20))

            # Add transaction table first
            elements.append(Paragraph("Transaction History", styles['Heading2']))
            elements.append(Spacer(1, 12))

            # Create table with automatic word wrapping
            table_data = [['Date', 'Type', 'Category', 'Description', 'Amount']]
            for transaction in reversed(self.transactions):
                # Convert amount to preferred currency
                converted_amount = self.currency_converter.convert_amount(
                    transaction.amount,
                    transaction.currency,
                    self.preferred_currency.get()
                )
                
                # Format amount with currency symbol
                amount_str = self.currency_converter.format_amount(
                    converted_amount,
                    self.preferred_currency.get()
                )
                
                # Add original amount if different currency
                if (transaction.currency != self.preferred_currency.get() and 
                    self.preferred_currency.get() == 'CZK' and 
                    transaction.currency in ['EUR', 'USD']):
                    original_amount = self.currency_converter.format_amount(
                        transaction.amount,
                        transaction.currency
                    )
                    amount_str = f"{amount_str} ({original_amount})"

                table_data.append([
                    transaction.date,
                    transaction.type,
                    transaction.category or '',
                    Paragraph(transaction.description, styles['Normal']),
                    amount_str
                ])

            # Adjust column widths proportionally
            available_width = letter[0] - doc.leftMargin - doc.rightMargin
            col_widths = [
                available_width * 0.15,  # Date
                available_width * 0.15,  # Type
                available_width * 0.2,   # Category
                available_width * 0.35,  # Description
                available_width * 0.15   # Amount
            ]

            # Create table with adjusted properties
            table = Table(table_data, colWidths=col_widths, repeatRows=1)

            # Update table style for better formatting
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),  # Amount column right-aligned
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]

            # Add row colors alternating
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    table_style.append(('BACKGROUND', (0, i), (-1, i), colors.beige))
                else:
                    table_style.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))

            table.setStyle(TableStyle(table_style))
            elements.append(table)
            elements.append(Spacer(1, 30))

            # Create graphs with proper currency labels
            temp_dir = tempfile.mkdtemp()
            graph_files = []

            # Balance over time graph
            balance_path = os.path.join(temp_dir, 'balance.png')
            plt.figure(figsize=(10, 5))
            
            dates = []
            balances = []
            running_balance = 0
            sorted_transactions = sorted(self.transactions, key=lambda x: x.date)
            
            for t in sorted_transactions:
                dates.append(datetime.strptime(t.date, "%Y-%m-%d"))
                # Convert amount to preferred currency
                converted_amount = self.currency_converter.convert_amount(
                    t.amount,
                    t.currency,
                    self.preferred_currency.get()
                )
                if t.type == 'income':
                    running_balance += converted_amount
                else:
                    running_balance -= converted_amount
                balances.append(running_balance)

            if dates:
                plt.plot(dates, balances, 'b-')
                plt.title('Balance Over Time')
                plt.xlabel('Date')
                plt.ylabel(f'Balance ({currency_symbol})')
                plt.xticks(rotation=45)
                
                # Format y-axis with currency symbol
                def format_amount(x, p):
                    return f'{currency_symbol}{x:,.0f}'
                plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(format_amount))
                
                plt.tight_layout(pad=1.5)
            plt.savefig(balance_path, bbox_inches='tight', dpi=300)
            plt.close()
            graph_files.append(balance_path)

            # Income vs Expenses graph
            expense_path = os.path.join(temp_dir, 'expense.png')
            plt.figure(figsize=(8, 6))
            
            # Convert amounts to preferred currency
            income = sum(
                self.currency_converter.convert_amount(t.amount, t.currency, self.preferred_currency.get())
                for t in self.transactions if t.type == 'income'
            )
            expenses = sum(
                self.currency_converter.convert_amount(t.amount, t.currency, self.preferred_currency.get())
                for t in self.transactions if t.type == 'expense'
            )
            
            plt.bar(['Income', 'Expenses'], [income, expenses], color=['g', 'r'], width=0.6)
            plt.title('Income vs Expenses')
            plt.ylabel(f'Amount ({currency_symbol})')
            
            # Format y-axis with currency symbol
            plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(format_amount))
            
            plt.tight_layout(pad=1.5)
            plt.savefig(expense_path, bbox_inches='tight', dpi=300)
            plt.close()
            graph_files.append(expense_path)

            # Category pie chart
            category_path = os.path.join(temp_dir, 'category.png')
            plt.figure(figsize=(8, 8))
            category_expenses = defaultdict(float)
            
            # Convert amounts to preferred currency for categories
            for t in self.transactions:
                if t.type == 'expense':
                    converted_amount = self.currency_converter.convert_amount(
                        t.amount,
                        t.currency,
                        self.preferred_currency.get()
                    )
                    category_expenses[t.category or 'Uncategorized'] += converted_amount

            if category_expenses:
                categories = list(category_expenses.keys())
                amounts = list(category_expenses.values())
                
                sorted_data = sorted(zip(categories, amounts), key=lambda x: x[1], reverse=True)
                categories, amounts = zip(*sorted_data)
                
                # Create labels with converted amounts
                labels = [f'{cat}\n({currency_symbol}{amt:.2f})' for cat, amt in zip(categories, amounts)]
                
                plt.pie(amounts, 
                       labels=labels,
                       autopct='%1.1f%%',
                       startangle=90,
                       counterclock=False,
                       pctdistance=0.85,
                       labeldistance=1.1)
                plt.title('Expenses by Category')
                plt.axis('equal')

            plt.savefig(category_path, bbox_inches='tight', dpi=300, pad_inches=0.5)
            plt.close()
            graph_files.append(category_path)

            # Add graphs with their titles
            add_graph_section("Balance History", balance_path, 7*inch, 3.5*inch)
            add_graph_section("Income vs Expenses", expense_path, 6*inch, 4.5*inch)
            add_graph_section("Expense Categories", category_path, 6*inch, 6*inch)

            # Generate PDF
            doc.build(elements)

            # Clean up temporary files
            for file in graph_files:
                if os.path.exists(file):
                    os.remove(file)
            os.rmdir(temp_dir)

            messagebox.showinfo("Success", "PDF report has been generated successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while generating the PDF:\n{str(e)}")

    def add_transaction(self):
        try:
            amount = self.amount_entry.get()
            if not amount:
                messagebox.showerror("Error", "Please enter an amount")
                return
                
            amount = float(amount)
            type_ = self.type_var.get()
            currency = self.transaction_currency.get() if hasattr(self, 'transaction_currency') else "CZK"
            
            # Get category based on whether "other" is selected
            if self.category_var.get() == 'other':
                category = self.custom_category_var.get()
            else:
                category = self.category_var.get()
                
            description = self.description_entry.get()
            date = self.date_entry.get_date().strftime("%Y-%m-%d")

            if self.editing:
                # Update existing transaction
                self.transactions[self.edit_index].amount = amount
                self.transactions[self.edit_index].type = type_
                self.transactions[self.edit_index].category = category
                self.transactions[self.edit_index].description = description
                self.transactions[self.edit_index].date = date
                self.transactions[self.edit_index].currency = currency
                self.end_editing()
            else:
                # Add new transaction
                transaction = Transaction(amount, type_, category, description, date, currency)
                self.transactions.append(transaction)

            self.save_transactions()
            self.update_display()
            self.clear_inputs()

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount")

    def update_display(self):
        self.update_summary()
        self.update_transaction_list()
        if self.showing_graphs:
            self.update_graphs()
        self.update_budget_display()

    def update_summary(self):
        income = 0
        expenses = 0
        
        for t in self.transactions:
            # Use the amount directly in its original currency
            if t.type == 'income':
                income += t.amount
            else:
                expenses += t.amount
                
        balance = income - expenses
        
        # Format amounts with proper spacing and commas
        if self.preferred_currency.get() == 'CZK':
            self.balance_label.config(text=f"Balance: {balance:,.2f} CZK")
            self.income_label.config(text=f"Income: {income:,.2f} CZK")
            self.expenses_label.config(text=f"Expenses: {expenses:,.2f} CZK")
        else:
            currency_symbol = self.currency_converter.currencies[self.preferred_currency.get()]
            self.balance_label.config(text=f"Balance: {currency_symbol}{balance:,.2f}")
            self.income_label.config(text=f"Income: {currency_symbol}{income:,.2f}")
            self.expenses_label.config(text=f"Expenses: {currency_symbol}{expenses:,.2f}")

    def update_transaction_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for transaction in reversed(self.transactions):
            # Convert amount to preferred currency for display
            converted_amount = self.currency_converter.convert_amount(
                transaction.amount,
                transaction.currency,
                self.preferred_currency.get()
            )
            
            # Format amount with currency symbol
            amount_str = self.currency_converter.format_amount(
                converted_amount,
                self.preferred_currency.get()
            )
            
            # Show original amount only when converting to CZK from EUR/USD
            if (transaction.currency != self.preferred_currency.get() and 
                self.preferred_currency.get() == 'CZK' and 
                transaction.currency in ['EUR', 'USD']):
                original_amount = self.currency_converter.format_amount(
                    transaction.amount,
                    transaction.currency
                )
                amount_str = f"{amount_str} ({original_amount})"

            self.tree.insert('', 'end', values=(
                transaction.date,
                transaction.type,
                transaction.category,
                transaction.description,
                amount_str
            ))

    def save_transactions(self):
        data = [t.to_dict() for t in self.transactions]
        with open('transactions.json', 'w') as f:
            json.dump(data, f)

    def load_transactions(self):
        if os.path.exists('transactions.json'):
            try:
                with open('transactions.json', 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        transactions_data = data
                    else:
                        transactions_data = data.get('transactions', [])

                    for t_dict in transactions_data:
                        t = Transaction(
                            t_dict['amount'],
                            t_dict['type'],
                            t_dict['category'],
                            t_dict['description']
                        )
                        t.id = t_dict['id']
                        t.date = t_dict['date']
                        # Set currency to CZK if not present in the data
                        t.currency = t_dict.get('currency', 'CZK')
                        self.transactions.append(t)
                    
                    # Sort transactions by date (newest first)
                    self.transactions.sort(key=lambda x: x.date, reverse=True)
            except (json.JSONDecodeError, FileNotFoundError):
                messagebox.showwarning(
                    "File Error",
                    "Could not load transactions file. Starting with empty transactions."
                )
                self.transactions = []
        else:
            with open('transactions.json', 'w') as f:
                json.dump([], f)

    def on_select(self, event):
        self.selected_items = self.tree.selection()

    def show_context_menu(self, event):
        # Select the item under cursor if not already selected
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
                self.selected_items = [item]
            
            # Show appropriate menu based on number of selected items
            if len(self.tree.selection()) > 1:
                self.multi_item_menu.post(event.x_root, event.y_root)
            else:
                self.single_item_menu.post(event.x_root, event.y_root)

    def delete_transactions(self):
        if not self.selected_items:
            return

        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete {len(self.selected_items)} transaction(s)?"):
            # Get indices of all selected items
            indices = []
            for item in self.selected_items:
                index = len(self.transactions) - 1 - self.tree.index(item)
                indices.append(index)
            
            # Sort indices in descending order to avoid index shifting when deleting
            indices.sort(reverse=True)
            
            # Delete transactions
            for index in indices:
                del self.transactions[index]
            
            # Save and update display
            self.save_transactions()
            self.update_display()

    def edit_transaction(self):
        if not self.selected_items or len(self.selected_items) != 1:
            return

        # Get the selected transaction
        index = len(self.transactions) - 1 - self.tree.index(self.selected_items[0])
        transaction = self.transactions[index]

        # Set editing mode
        self.editing = True
        self.edit_index = index

        # Fill the form with transaction data
        self.date_entry.set_date(datetime.strptime(transaction.date, "%Y-%m-%d"))
        self.amount_entry.delete(0, tk.END)
        self.amount_entry.insert(0, str(transaction.amount))
        self.type_var.set(transaction.type)
        
        # Handle category setting
        if transaction.category in self.category_combo['values']:
            self.category_var.set(transaction.category)
            self.custom_category_entry.grid_remove()
            self.category_combo.grid()
        else:
            self.category_var.set('other')
            self.custom_category_var.set(transaction.category)
            self.on_category_change()
            
        self.description_entry.delete(0, tk.END)
        self.description_entry.insert(0, transaction.description)

        # Update button text and show cancel button
        self.action_button.config(text="Save Changes")
        self.cancel_button.grid()

    def cancel_edit(self):
        self.end_editing()
        self.clear_inputs()

    def end_editing(self):
        self.editing = False
        self.edit_index = None
        self.action_button.config(text="Add Transaction")
        self.cancel_button.grid_remove()

    def on_category_change(self, event=None):
        if self.category_var.get() == 'other':
            self.category_combo.grid_remove()
            self.custom_category_entry.grid()
            self.custom_category_entry.focus()
        else:
            self.custom_category_entry.grid_remove()
            self.category_combo.grid()

    def clear_inputs(self):
        if not self.editing:
            self.date_entry.set_date(datetime.now())
            self.amount_entry.delete(0, tk.END)
            self.type_var.set('income')
            self.category_var.set('')
            self.custom_category_var.set('')
            self.custom_category_entry.grid_remove()
            self.category_combo.grid()
            self.description_entry.delete(0, tk.END)

    def show_transactions(self):
        self.showing_graphs = False
        self.graphs_frame.pack_forget()
        self.budgets_frame.pack_forget()
        self.savings_frame.pack_forget()
        self.transactions_frame.pack(fill="both", expand=True)
        
        self.transactions_button.configure(style='Selected.TButton')
        self.analytics_button.configure(style='Unselected.TButton')
        self.budgets_button.configure(style='Unselected.TButton')
        self.savings_button.configure(style='Unselected.TButton')

    def show_analytics(self):
        self.showing_graphs = True
        self.transactions_frame.pack_forget()
        self.budgets_frame.pack_forget()
        self.savings_frame.pack_forget()
        self.graphs_frame.pack(fill="both", expand=True)
        self.update_graphs()
        
        self.transactions_button.configure(style='Unselected.TButton')
        self.analytics_button.configure(style='Selected.TButton')
        self.budgets_button.configure(style='Unselected.TButton')
        self.savings_button.configure(style='Unselected.TButton')

    def create_budgets_frame(self):
        self.budgets_frame = ttk.LabelFrame(self.main_container, text="Budget Management", padding="10")
        
        # Create budget management section
        budget_input_frame = ttk.Frame(self.budgets_frame)
        budget_input_frame.pack(fill="x", padx=5, pady=5)

        # Category selection - use same categories as transactions
        ttk.Label(budget_input_frame, text="Category:").grid(row=0, column=0, padx=5, pady=5)
        self.budget_category_var = tk.StringVar()
        self.budget_category_combo = ttk.Combobox(
            budget_input_frame, 
            textvariable=self.budget_category_var,
            values=[cat for cat in self.default_categories if cat != '']  # Exclude empty category
        )
        self.budget_category_combo.grid(row=0, column=1, padx=5, pady=5)

        # Amount input
        ttk.Label(budget_input_frame, text="Budget Amount:").grid(row=0, column=2, padx=5, pady=5)
        self.budget_amount_entry = ttk.Entry(budget_input_frame)
        self.budget_amount_entry.grid(row=0, column=3, padx=5, pady=5)

        # Add currency selection after amount
        ttk.Label(budget_input_frame, text="Currency:").grid(row=0, column=4, padx=5, pady=5)
        self.budget_currency_var = tk.StringVar(value="CZK")
        budget_currency_combo = ttk.Combobox(
            budget_input_frame,
            textvariable=self.budget_currency_var,
            values=list(self.currency_converter.currencies.keys()),
            state='readonly',
            width=5
        )
        budget_currency_combo.grid(row=0, column=5, padx=5, pady=5)

        # Move period selection to next row
        ttk.Label(budget_input_frame, text="Period:").grid(row=1, column=0, padx=5, pady=5)
        self.budget_period_var = tk.StringVar(value="Monthly")
        period_combo = ttk.Combobox(
            budget_input_frame,
            textvariable=self.budget_period_var,
            values=['Weekly', 'Monthly'],
            state='readonly'
        )
        period_combo.grid(row=1, column=1, padx=5, pady=5)

        # Add budget button moved to next row
        ttk.Button(
            budget_input_frame,
            text="Set Budget",
            command=self.set_budget
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        # Create budget overview section
        self.budget_overview = ttk.Frame(self.budgets_frame)
        self.budget_overview.pack(fill="both", expand=True, pady=10)

        # Create treeview for budget display
        columns = ('category', 'period', 'amount', 'spent', 'remaining', 'status')
        self.budget_tree = ttk.Treeview(self.budget_overview, columns=columns, show='headings')
        
        self.budget_tree.heading('category', text='Category')
        self.budget_tree.heading('period', text='Period')
        self.budget_tree.heading('amount', text='Budget')
        self.budget_tree.heading('spent', text='Spent')
        self.budget_tree.heading('remaining', text='Remaining')
        self.budget_tree.heading('status', text='Status')

        self.budget_tree.column('category', width=100)
        self.budget_tree.column('period', width=100)
        self.budget_tree.column('amount', width=100)
        self.budget_tree.column('spent', width=100)
        self.budget_tree.column('remaining', width=100)
        self.budget_tree.column('status', width=100)

        # Add scrollbar
        budget_scrollbar = ttk.Scrollbar(self.budget_overview, orient="vertical", command=self.budget_tree.yview)
        self.budget_tree.configure(yscrollcommand=budget_scrollbar.set)

        self.budget_tree.pack(side="left", fill="both", expand=True)
        budget_scrollbar.pack(side="right", fill="y")

        # Add right-click menu for budget deletion
        self.budget_tree.bind("<Button-3>", self.show_budget_context_menu)
        self.budget_menu = tk.Menu(self.root, tearoff=0)
        self.budget_menu.add_command(label="Delete Budget", command=self.delete_budget)

    def show_budgets(self):
        self.showing_graphs = False
        self.transactions_frame.pack_forget()
        self.graphs_frame.pack_forget()
        self.savings_frame.pack_forget()
        self.budgets_frame.pack(fill="both", expand=True)
        
        # Update button styles
        self.transactions_button.configure(style='Unselected.TButton')
        self.analytics_button.configure(style='Unselected.TButton')
        self.budgets_button.configure(style='Selected.TButton')
        self.savings_button.configure(style='Unselected.TButton')
        
        self.update_budget_display()

    def set_budget(self):
        category = self.budget_category_var.get()
        try:
            amount = float(self.budget_amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount")
            return

        if not category:
            messagebox.showerror("Error", "Please select a category")
            return

        period = self.budget_period_var.get()
        currency = self.budget_currency_var.get()
        
        # Convert amount to CZK for storage
        if currency != 'CZK':
            amount = self.currency_converter.convert_amount(amount, currency, 'CZK')
        
        self.budgets[category] = {
            'amount': amount,
            'period': period,
            'currency': currency  # Store original currency for reference
        }
        
        self.save_budgets()
        self.update_budget_display()
        
        # Clear inputs
        self.budget_amount_entry.delete(0, tk.END)
        self.budget_category_var.set('')
        self.budget_currency_var.set('CZK')

    def update_budget_display(self):
        for item in self.budget_tree.get_children():
            self.budget_tree.delete(item)

        for category, budget in self.budgets.items():
            # Convert budget amount to preferred currency
            converted_amount = self.currency_converter.convert_amount(
                budget['amount'],
                'CZK',  # Budgets are stored in CZK
                self.preferred_currency.get()
            )
            
            spent = self.calculate_spending(category, budget['period'])
            # Convert spent amount to preferred currency
            converted_spent = self.currency_converter.convert_amount(
                spent,
                'CZK',  # Spending is calculated in CZK
                self.preferred_currency.get()
            )
            
            remaining = converted_amount - converted_spent
            
            # Format amounts with currency symbol
            amount_str = self.currency_converter.format_amount(
                converted_amount,
                self.preferred_currency.get()
            )
            spent_str = self.currency_converter.format_amount(
                converted_spent,
                self.preferred_currency.get()
            )
            remaining_str = self.currency_converter.format_amount(
                remaining,
                self.preferred_currency.get()
            )
            
            # Calculate status based on converted amounts
            if remaining < 0:
                status = "Over Budget"
                status_color = 'red'
            elif remaining < (converted_amount * 0.2):
                status = "Near Limit"
                status_color = 'orange'
            else:
                status = "On Track"
                status_color = 'green'

            item = self.budget_tree.insert('', 'end', values=(
                category,
                budget['period'],
                amount_str,
                spent_str,
                remaining_str,
                status
            ))
            
            self.budget_tree.tag_configure(status_color, foreground=status_color)
            self.budget_tree.item(item, tags=(status_color,))

    def calculate_spending(self, category, period):
        total = 0
        now = datetime.now()
        
        if period == 'Monthly':
            start_date = datetime(now.year, now.month, 1)
            _, last_day = monthrange(now.year, now.month)
            end_date = datetime(now.year, now.month, last_day)
        else:  # Weekly
            start_date = now - timedelta(days=now.weekday())
            end_date = start_date + timedelta(days=6)

        for transaction in self.transactions:
            if (transaction.type == 'expense' and 
                transaction.category == category and
                start_date <= datetime.strptime(transaction.date, "%Y-%m-%d") <= end_date):
                total += transaction.amount

        return total

    def show_budget_context_menu(self, event):
        item = self.budget_tree.identify_row(event.y)
        if item:
            self.budget_tree.selection_set(item)
            self.budget_menu.post(event.x_root, event.y_root)

    def delete_budget(self):
        selected = self.budget_tree.selection()
        if not selected:
            return

        category = self.budget_tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirm Delete", f"Delete budget for {category}?"):
            del self.budgets[category]
            self.save_budgets()
            self.update_budget_display()

    def save_budgets(self):
        with open('budgets.json', 'w') as f:
            json.dump(self.budgets, f)

    def load_budgets(self):
        try:
            if os.path.exists('budgets.json'):
                with open('budgets.json', 'r') as f:
                    self.budgets = json.load(f)
            else:
                self.budgets = {}
        except:
            self.budgets = {}

    def create_savings_frame(self):
        self.savings_frame = ttk.LabelFrame(self.main_container, text="Savings Goals", padding="10")
        
        # Create input section
        input_frame = ttk.Frame(self.savings_frame)
        input_frame.pack(fill="x", padx=5, pady=5)

        # Goal Name
        ttk.Label(input_frame, text="Goal Name:").grid(row=0, column=0, padx=5, pady=5)
        self.goal_name_entry = ttk.Entry(input_frame)
        self.goal_name_entry.grid(row=0, column=1, padx=5, pady=5)

        # Target Amount
        ttk.Label(input_frame, text="Target Amount:").grid(row=0, column=2, padx=5, pady=5)
        self.goal_amount_entry = ttk.Entry(input_frame)
        self.goal_amount_entry.grid(row=0, column=3, padx=5, pady=5)

        # Add currency selection after target amount
        ttk.Label(input_frame, text="Currency:").grid(row=0, column=4, padx=5, pady=5)
        self.goal_currency_var = tk.StringVar(value="CZK")
        goal_currency_combo = ttk.Combobox(
            input_frame,
            textvariable=self.goal_currency_var,
            values=list(self.currency_converter.currencies.keys()),
            state='readonly',
            width=5
        )
        goal_currency_combo.grid(row=0, column=5, padx=5, pady=5)

        # Target Date
        ttk.Label(input_frame, text="Target Date:").grid(row=1, column=0, padx=5, pady=5)
        self.goal_date_entry = DateEntry(input_frame, width=12, background='darkblue',
                                       foreground='white', borderwidth=2,
                                       date_pattern='yyyy-mm-dd')
        self.goal_date_entry.grid(row=1, column=1, padx=5, pady=5)

        # Monthly Contribution
        ttk.Label(input_frame, text="Monthly Contribution:").grid(row=1, column=2, padx=5, pady=5)
        self.goal_contribution_entry = ttk.Entry(input_frame)
        self.goal_contribution_entry.grid(row=1, column=3, padx=5, pady=5)

        # Add goal button
        ttk.Button(
            input_frame,
            text="Add Goal",
            command=self.add_savings_goal
        ).grid(row=1, column=4, columnspan=2, padx=5, pady=5)

        # Create goals overview section
        self.savings_overview = ttk.Frame(self.savings_frame)
        self.savings_overview.pack(fill="both", expand=True, pady=10)

        # Create treeview for goals display
        columns = ('name', 'target', 'current', 'monthly', 'deadline', 'progress')
        self.savings_tree = ttk.Treeview(self.savings_overview, columns=columns, show='headings')
        
        self.savings_tree.heading('name', text='Goal Name')
        self.savings_tree.heading('target', text='Target Amount')
        self.savings_tree.heading('current', text='Current Amount')
        self.savings_tree.heading('monthly', text='Monthly Contribution')
        self.savings_tree.heading('deadline', text='Target Date')
        self.savings_tree.heading('progress', text='Progress')

        # Set column widths
        for col in columns:
            self.savings_tree.column(col, width=100)

        # Add scrollbar
        savings_scrollbar = ttk.Scrollbar(self.savings_overview, orient="vertical", command=self.savings_tree.yview)
        self.savings_tree.configure(yscrollcommand=savings_scrollbar.set)

        self.savings_tree.pack(side="left", fill="both", expand=True)
        savings_scrollbar.pack(side="right", fill="y")

        # Add right-click menu for goal management
        self.savings_tree.bind("<Button-3>", self.show_savings_context_menu)
        self.savings_menu = tk.Menu(self.root, tearoff=0)
        self.savings_menu.add_command(label="Add Contribution", command=self.add_contribution)
        self.savings_menu.add_command(label="Delete Goal", command=self.delete_savings_goal)

    def show_savings(self):
        self.showing_graphs = False
        self.transactions_frame.pack_forget()
        self.graphs_frame.pack_forget()
        self.budgets_frame.pack_forget()
        
        # Reload savings goals data before showing the frame
        self.load_savings_goals()
        self.update_savings_display()
        
        self.savings_frame.pack(fill="both", expand=True)
        
        # Update button styles
        self.transactions_button.configure(style='Unselected.TButton')
        self.analytics_button.configure(style='Unselected.TButton')
        self.budgets_button.configure(style='Unselected.TButton')
        self.savings_button.configure(style='Selected.TButton')

    def add_savings_goal(self):
        name = self.goal_name_entry.get()
        try:
            target = float(self.goal_amount_entry.get())
            monthly = float(self.goal_contribution_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid amounts")
            return

        if not name:
            messagebox.showerror("Error", "Please enter a goal name")
            return

        deadline = self.goal_date_entry.get_date().strftime("%Y-%m-%d")
        currency = self.goal_currency_var.get()
        
        # Convert amounts to CZK for storage
        if currency != 'CZK':
            target = self.currency_converter.convert_amount(target, currency, 'CZK')
            monthly = self.currency_converter.convert_amount(monthly, currency, 'CZK')
        
        self.savings_goals[name] = {
            'target': target,
            'current': 0,
            'monthly': monthly,
            'deadline': deadline,
            'contributions': [],
            'currency': currency  # Store original currency for reference
        }
        
        self.save_savings_goals()
        self.update_savings_display()
        
        # Clear inputs
        self.goal_name_entry.delete(0, tk.END)
        self.goal_amount_entry.delete(0, tk.END)
        self.goal_contribution_entry.delete(0, tk.END)
        self.goal_date_entry.set_date(datetime.now())
        self.goal_currency_var.set('CZK')

    def add_contribution(self):
        selected = self.savings_tree.selection()
        if not selected:
            return

        # Get all values from the selected item
        values = self.savings_tree.item(selected[0])['values']
        if not values:
            return
        
        goal_name = str(values[0])  # Convert to string to ensure consistent type
        
        if goal_name not in self.savings_goals:
            # Try reloading goals from file
            self.load_savings_goals()
            if goal_name not in self.savings_goals:
                messagebox.showerror("Error", "Could not find the selected goal")
                return
        
        # Create contribution dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Add Contribution to {goal_name}")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Amount:").pack(pady=5)
        amount_entry = ttk.Entry(dialog)
        amount_entry.pack(pady=5)

        def save_contribution():
            try:
                amount = float(amount_entry.get())
                if amount <= 0:
                    messagebox.showerror("Error", "Please enter a positive amount")
                    return
                
                self.savings_goals[goal_name]['current'] += amount
                self.savings_goals[goal_name]['contributions'].append({
                    'amount': amount,
                    'date': datetime.now().strftime("%Y-%m-%d")
                })
                self.save_savings_goals()
                self.update_savings_display()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid amount")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving contribution: {str(e)}")

        ttk.Button(dialog, text="Save", command=save_contribution).pack(pady=20)

    def update_savings_display(self):
        try:
            for item in self.savings_tree.get_children():
                self.savings_tree.delete(item)

            self.load_savings_goals()

            for name, goal in self.savings_goals.items():
                try:
                    # Convert amounts to preferred currency
                    converted_target = self.currency_converter.convert_amount(
                        goal['target'],
                        'CZK',  # Goals are stored in CZK
                        self.preferred_currency.get()
                    )
                    converted_current = self.currency_converter.convert_amount(
                        goal['current'],
                        'CZK',
                        self.preferred_currency.get()
                    )
                    converted_monthly = self.currency_converter.convert_amount(
                        goal['monthly'],
                        'CZK',
                        self.preferred_currency.get()
                    )
                    
                    # Calculate progress using converted amounts
                    progress = (converted_current / converted_target) * 100
                    
                    # Format amounts with currency symbol
                    target_str = self.currency_converter.format_amount(
                        converted_target,
                        self.preferred_currency.get()
                    )
                    current_str = self.currency_converter.format_amount(
                        converted_current,
                        self.preferred_currency.get()
                    )
                    monthly_str = self.currency_converter.format_amount(
                        converted_monthly,
                        self.preferred_currency.get()
                    )
                    
                    item = self.savings_tree.insert('', 'end', values=(
                        name,
                        target_str,
                        current_str,
                        monthly_str,
                        goal['deadline'],
                        f"{progress:.1f}%"
                    ))
                    
                    # Color coding remains the same...
                    
                except Exception as e:
                    print(f"Error displaying goal {name}: {str(e)}")
                    continue

        except Exception as e:
            messagebox.showerror("Error", f"Error updating savings display: {str(e)}")

    def show_savings_context_menu(self, event):
        item = self.savings_tree.identify_row(event.y)
        if item:
            self.savings_tree.selection_set(item)
            self.savings_menu.post(event.x_root, event.y_root)

    def delete_savings_goal(self):
        selected = self.savings_tree.selection()
        if not selected:
            return

        # Get all values from the selected item
        values = self.savings_tree.item(selected[0])['values']
        if not values:
            return
        
        goal_name = str(values[0])  # Convert to string to ensure consistent type
        
        if messagebox.askyesno("Confirm Delete", f"Delete savings goal: {goal_name}?"):
            try:
                if goal_name in self.savings_goals:
                    del self.savings_goals[goal_name]
                    self.save_savings_goals()
                    self.update_savings_display()
                    messagebox.showinfo("Success", f"Goal '{goal_name}' has been deleted.")
                else:
                    # Reload goals from file and try again
                    self.load_savings_goals()
                    if goal_name in self.savings_goals:
                        del self.savings_goals[goal_name]
                        self.save_savings_goals()
                        self.update_savings_display()
                        messagebox.showinfo("Success", f"Goal '{goal_name}' has been deleted.")
                    else:
                        messagebox.showerror("Error", f"Could not find goal: {goal_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Error deleting goal: {str(e)}")

    def save_savings_goals(self):
        with open('savings_goals.json', 'w') as f:
            json.dump(self.savings_goals, f)

    def load_savings_goals(self):
        try:
            if os.path.exists('savings_goals.json'):
                with open('savings_goals.json', 'r') as f:
                    self.savings_goals = json.load(f)
            else:
                self.savings_goals = {}
        except:
            self.savings_goals = {}

    def refresh_data(self):
        """Reload all data from files and update displays"""
        try:
            # Clear current data
            self.transactions = []
            self.budgets = {}
            self.savings_goals = {}
            
            # Reload all data
            self.load_transactions()
            self.load_budgets()
            self.load_savings_goals()
            
            # Update displays
            self.update_display()
            
            messagebox.showinfo("Success", "Data refreshed successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Error refreshing data: {str(e)}")

    def on_currency_change(self, event=None):
        self.update_display()
        # Add explicit update for savings display
        if hasattr(self, 'savings_frame') and self.savings_frame.winfo_ismapped():
            self.update_savings_display()

if __name__ == "__main__":
    root = tk.Tk()
    app = BudgetTracker(root)
    root.mainloop() 