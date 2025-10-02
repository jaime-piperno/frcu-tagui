# 🤖 RPA Automation Project: Pending Balance Notification
---

This repository contains the **Automation Project for Pending and Overdue Balance Notifications** developed in **UiPath**.

## 👥 Development Team
This project was developed by **Team 2** within the course **Automation Technologies (UTN FRCU)**:

* **Callegari, Maria**
* **Egel, Valeria**
* **Marks, Milagros**
* **Romero Klug, Valentina**


## 🎯 Objectives
The goal is to maximize operational efficiency and reduce overdue debt by sending personalized and segmented emails to clients, classifying them into two groups:
* Upcoming Due Date: Preventive reminder.
* Overdue: Non-compliance notification.


# 📖  Documentation 
*   **Official UiPath Website:** https://www.uipath.com/product/studio
*   **UiPath Community:** https://www.uipath.com/community

# 🛠️ Installation
To install UiPath on your system, follow the instructions provided at: https://docs.uipath.com/es/studio/standalone/2022.10/user-guide/install-studio


# 💻 Key Features
*   **Data Validation:** Ensures that essential fields (Name, Last Name, Email, Due Date, Amount) are not empty for each row.
*   **Email Validation:** Validates the email format using regular expressions.
*   **Upcoming Due Reminder Emails:** Sends reminder emails to clients whose invoices will be due within the next 7 days and are still unpaid.
*   **Overdue Invoice Notifications:** Sends notification emails to clients with overdue and unpaid invoices.
*   **Registro de Datos Incompletos/Inválidos:** Rows with invalid emails are written into a Google Sheets spreadsheet `(Sheet 2 in "InformacionClientes")` for further review.
*   **Status Tracking:** Keeps a record of the number of emails sent, emails not sent due to invalid addresses, and clients with canceled debts.
*   **Summary Message:** At the end, displays a message box with a summary of the process execution.

# 💡 Prerequisites

### 👩‍💻 Software Requirements

**UiPath Studio** installed.
**UiPath GSuite Activities Package** installed in your project.
**Google Workspace (GSuite) connection** configured in UiPath Studio.

### 💾 Data Files

* A source data file named **ClientesInformacion.xlsx**  containing the following columns: 
    * `Nombre`
    * `Apellido`
    * `E-mail`
    * `Monto`
    * `FechaVencimiento`
    * `FechaPago` (optional column, used to determine the debt status).
 * Additionally, it must include a `“Sheet 2”` to log incomplete data.
 * In the following link we show an example, and we recommend saving a copy of this file in your drive.
 https://docs.google.com/spreadsheets/d/14e41S4DPWxg17NAvQsnDCMjIVRlqed7kOboIMkzuCk8/edit?usp=sharing 
---