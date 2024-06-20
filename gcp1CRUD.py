import pandas as pd
from flask import Flask, render_template, request
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread
from datetime import datetime

#instantiate new flask app
app = Flask(__name__)

#initialize API object for the Flask Application
api = Api(app)


spreadsheet_id = '1h9sIOdii_eRXVy7Kd9Nh2-LXsNNhMlfdjGB3LmwugB8'
sheet_id='0'
Credentialsfile = 'dependable-star-426716-q7-ec8c049c4281.json'
sheetscopes=['https://www.googleapis.com/auth/spreadsheets']

# Load credentials from the JSON file you downloaded from Google Cloud Console
creds = None
creds = service_account.Credentials.from_service_account_file(
    Credentialsfile, scopes=sheetscopes)

service = build('sheets', 'v4', credentials=creds)

#Call the sheets API
sheet = service.spreadsheets()
# result = sheet.values().get(spreadsheetId=spreadsheet_id,range='Sheet1').execute()
records = sheet.values().get(spreadsheetId=spreadsheet_id, range='Sheet1').execute()
# print(result)

@app.route('/')
def index():
    return render_template('index.html')


#get all record in spreadsheet
@app.route('/api',methods=['GET'])
def get():
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range='Sheet1').execute()
    return jsonify(result.get('values',[]))
    # return result.get('values',[])


#Add record in spreadsheet
@app.route('/api/add', methods=['POST'])
def append_to_sheet():
    data = request.get_json()
    # Example assuming data is a JSON object with keys matching your sheet columns
    record_values = [
        data.get('id'),
        data.get('date'),
        data.get('amount'),
        data.get('description'),
        data.get('category'),
        data.get("payment mode")
        ]
    result = sheet.values().append(spreadsheetId=spreadsheet_id,range='Sheet1',
                                   valueInputOption='USER_ENTERED', body={'values': [record_values]} ).execute()
    # return result
    return jsonify({'success': True, 'response': result})

def FoundRowByExpenseId(expense_id):
    print(f'In function of found row ---- {expense_id}')
    range_name = 'Sheet1!A1:F'  # Adjust this range based on your actual sheet

    # Example criteria: searching for rows where column A has a specific value
    value_to_find = expense_id  # Replace with the value you want to search for

    # Execute the request to retrieve values
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()

    # Get all the values from the response
    rows = result.get('values', [])

    row_found = None
    row_index = 0
    # print(rows)
    # Iterate through the rows and find the row that matches the criteria
    if not rows:
        return None,0
    else:
        for index, row in enumerate(rows):
            # print(row)
            if row and row[0] == str(value_to_find):  # Assuming column A (index 0) is where you're searching
                row_found = row
                row_index = index + 1  # Adjust to 1-based index for Sheets API
                print (row_found , "    >>>> " , str(row_index))
                return row_found, row_index
        else:
            return row_found,-1


# Route to update an existing expense
@app.route('/api/update/<string:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    data = request.get_json()

    #calling Function - to find row by ID
    row_found,row_index = FoundRowByExpenseId(expense_id)

    if row_found and row_index != -1:
        new_values = [[data['id'], data['date'], data['amount'], data['description'], data['category'], data["payment mode"]]]

        # Specify the range to update (just one row in this example)
        update_range = f'Sheet1!A{row_index}:F{row_index}'  # Adjust columns as per your sheet structure

        # Prepare the request body
        update_body = {'values': new_values}

        # Execute the update request
        update_result = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=update_range,
                                                                   valueInputOption='USER_ENTERED', body=update_body).execute()

        return jsonify((f'message: Expense {expense_id} updated successfully.Updated {update_result.get("updatedCells")} cells.'))
    else:
        return jsonify(f'{row_found}   >>>> {row_index}   message: No rows found matching the criteria.')


# Route to delete a expense
@app.route('/api/delete/<string:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    row_found,row_index = None,0
    # calling Function - to find row by ID
    row_found, row_index = FoundRowByExpenseId(expense_id)
    print(row_found,row_index)
    if(row_found and row_index != -1):
        # Prepare the request body
        batch_update_body = {
            'requests': [
                {
                    'deleteDimension': {
                        'range' :{
                                'sheetId': '0',  # You may need to get the sheetId programmatically
                                'dimension': 'ROWS',
                                'startIndex': row_index - 1,  # Adjust to 0-based index for API
                                'endIndex': row_index  # endIndex is exclusive, so it deletes only one row
                        }
                    }
                }
            ]
        }
        print(batch_update_body)
        # Execute the delete request
        delete_result = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=batch_update_body).execute()
        return (f'Message : Deleted expense id {expense_id} row.')
    else:
        return ('Message : No row found matching the criteria.')


#Get by category
@app.route('/api/category/<string:value>', methods=['GET'])
def get_catgeory(value):
    fetchedresult = sheet.values().get(spreadsheetId=spreadsheet_id, range='Sheet1!A1:E').execute()
    values = fetchedresult.get('values',[])
    filtered_data = [row for row in values if row[4] == value]
    if not filtered_data:
        return jsonify({'error': 'No data found'})

    # #calculate
    total = sum(float(row[2]) for row in filtered_data[0:])  # Skip header row
    return jsonify(f'Total = {total} >>>> data: {filtered_data}')

#Summary by category
@app.route('/api/summarybycategory', methods=['GET'])
def Summary_catgeory():
    fetchedresult = sheet.values().get(spreadsheetId=spreadsheet_id, range='Sheet1!A1:E').execute()
    rows = fetchedresult.get('values',[])
    # filtered_data = [row for row in values if row[4] == value]

    if not rows:
        return jsonify({'Message': 'No data found'})

     # Assuming the first row contains headers, extract categories and values
    headers = rows[0]
    data = rows[1:]
    categories = set(rows[4] for rows in data)
    # print(categories)
    summary = {}
    summary_text = ''

    for category in categories:
        summary[category] = {
            'total': 0,
            'count': 0,
            'average': 0
        }

        for row in data:
            if row[4] == category:
                try:
                    value = float(row[2])  # Assuming the third column (index 2) contains numeric data
                    summary[category]['total'] += value
                    summary[category]['count'] += 1
                except ValueError:
                    continue

        if summary[category]['count'] > 0:
            summary[category]['average'] = summary[category]['total'] / summary[category]['count']
        summary_text += ('\n Catgeory: '+category + ': \n count = '+str(summary[category]['count']) + '\n Total = ' + str(summary[category]['total'] )
                            + '\n Average = ' + str(summary[category]['average']) + '\n')
        # print(summary[category]['count'],summary[category]['average'],summary[category]['total'],summary[category]['count'])
    print(summary_text)
    return summary_text

#Summary by Payment Mode
@app.route('/api/summarybypaymode', methods=['GET'])
def Summary_paymode():
    fetchedresult = sheet.values().get(spreadsheetId=spreadsheet_id, range='Sheet1!A1:F').execute()
    rows = fetchedresult.get('values',[])
    # filtered_data = [row for row in values if row[4] == value]

    if not rows:
        return jsonify({'Message': 'No data found'})

     # Assuming the first row contains headers, extract categories and values
    headers = rows[0]
    data = rows[1:]
    pay_modes = set(rows[5] for rows in data)
    # print(pay_modes)
    summary = {}
    summary_text = ''

    for paymode in pay_modes:
        summary[paymode] = {
            'total': 0,
            'count': 0,
            # 'average': 0
        }

        for row in data:
            if row[5] == paymode:
                try:
                    value = float(row[2])  # Assuming the third column (index 2) contains numeric data
                    summary[paymode]['total'] += value
                    summary[paymode]['count'] += 1
                except ValueError:
                    continue

        summary_text += ('\n Payment Modes: '+paymode + ': \n count = '+str(summary[paymode]['count']) + '\n Total = ' + str(summary[paymode]['total'] )+ '\n')
        # print(summary[category]['count'],summary[category]['average'],summary[category]['total'],summary[category]['count'])
    print(summary_text)
    return summary_text

#Get by Payment Mode
@app.route('/api/paymentmode/<string:value>', methods=['GET'])
def get_paymentmode(value):
    fetchedresult = sheet.values().get(spreadsheetId=spreadsheet_id, range='Sheet1!A1:F').execute()
    values = fetchedresult.get('values', [])
    filtered_data = [row for row in values if row[5] == value]
    if not filtered_data:
        return jsonify({'error': 'No data found'})

        # #calculate
    total = sum(float(row[2]) for row in filtered_data[0:])  # Skip header row
    return jsonify(f'Total = {total} >>>> data: {filtered_data}')
    # return jsonify({'data': filtered_data})


@app.route('/api/expensesbydaterange', methods=['GET'])
def get_expenses_by_date_range():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Define the date range (inclusive)
    start_date = datetime.strptime(start_date, '%d/%m/%Y').date()
    end_date = datetime.strptime(end_date, '%d/%m/%Y').date()
    print(start_date,end_date)

    # spreadsheet_id = 'your-spreadsheet-id'
    range_name = 'Sheet1!A2:F'  # Update with your sheet name and range
    # Filter records based on date range
    fetchedresult = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    records = fetchedresult.get('values', [])
    # print(records)

    filtered_records = [record for record in records if
                        start_date <= datetime.strptime(record[1], '%d/%m/%Y').date() <= end_date]

    # Print or process filtered records
    # for record in filtered_records:
    #     print(record)

    total = sum(float(row[2]) for row in filtered_records[0:])  # Skip header row
    return jsonify(f'Total = {total} >>>> data: {filtered_records}')
    # return jsonify({'data': filtered_records})

    # result = sheet.values().get(spreadsheetId=spreadsheet_id,range=range_name).execute()
    #
    # values = result.get('values', [])
    # expenses = []
    # for row in values:
    #     if row[1] >= start_date and row[1] <= end_date:
    #         expenses.append({
    #             'id': row[0],
    #             'date': row[1],
    #             'amount': row[2],
    #             'description': row[3],
    #             'category' : row[4],
    #             'payment mode' : row[5]
    #         })
    #
    # return jsonify(expenses)


# if __name__ == '__main__':
#     app.run(host = '127.0.0.',port = '5007',debug=True)

if __name__ == '__main__':
    app.run(debug=True, port = 5000)
