# Budget Tracker Application

A comprehensive personal finance management application built with Python and Tkinter. This application helps users track their income, expenses, budgets, and savings goals with support for multiple currencies (CZK, EUR, USD).

## Features

- **Transaction Management**
  - Add, edit, and delete transactions
  - Support for multiple currencies
  - Categorize transactions
  - Date tracking for each transaction

- **Budget Management**
  - Set budgets for different categories
  - Weekly or monthly budget periods
  - Real-time budget tracking
  - Visual status indicators

- **Savings Goals**
  - Create and track savings goals
  - Set target amounts and deadlines
  - Track progress towards goals
  - Add contributions to goals

- **Analytics**
  - Balance over time graph
  - Income vs Expenses comparison
  - Expense breakdown by category
  - Visual data representation

- **Export Functionality**
  - Export reports to PDF
  - Includes transaction history
  - Visual graphs and charts
  - Summary statistics

## Installation

1. **Prerequisites**
   - Python 3.x
   - pip (Python package installer)

2. **Required Libraries**
   ```bash
   pip install tkinter
   pip install tkcalendar
   pip install reportlab
   pip install matplotlib
   pip install requests
   ```

3. **Download and Setup**
   - Clone or download the repository
   - Ensure all files are in the same directory:
     - budget_tracker.py
     - launcher.pyw

## Usage

1. **Starting the Application**
   - Double-click `launcher.pyw` to start the application
   - The main window will open with the transactions view

2. **Managing Transactions**
   - Click "Add Transaction" to record new transactions
   - Right-click transactions to edit or delete them
   - Select multiple transactions to delete them together

3. **Setting Budgets**
   - Navigate to the "Budgets" tab
   - Set category budgets with amounts and periods
   - Monitor spending against budgets

4. **Creating Savings Goals**
   - Go to "Savings Goals" tab
   - Create new goals with target amounts and deadlines
   - Add contributions to track progress

5. **Viewing Analytics**
   - Click on "Analytics" to view graphs
   - See balance trends over time
   - View income vs expenses
   - Analyze spending by category

6. **Exporting Reports**
   - Click "Export PDF" to generate a report
   - Choose save location
   - Report includes transactions, graphs, and summary

7. **Currency Management**
   - Select preferred display currency from the top menu
   - Add transactions in any supported currency
   - Automatic currency conversion for display

## Data Storage

The application stores data locally in JSON files:
- transactions.json
- budgets.json
- savings_goals.json

These files are automatically created and managed by the application.

## Notes

- The application uses real-time currency conversion rates
- Default currency is set to CZK
- All monetary values are displayed with proper formatting (e.g., 1,234.56 CZK)
- Graphs and statistics automatically update when data changes

## Support

For issues or questions, please:
1. Check the existing documentation
2. Verify all required libraries are installed
3. Ensure all files are in the correct location
4. Check file permissions for data storage
