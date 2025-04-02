import json
from datetime import datetime
import re

# Read the JSON data from file
def read_json_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: File '{filename}' contains invalid JSON.")
        return None

# Format date string to PostgreSQL format (YYYY-MM-DD)
def format_date(date_string):
    if not date_string:
        return "NULL"
    
    # Handle different date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # ISO format with microseconds
        "%Y-%m-%d",              # Simple date format
        "%d/%m/%Y",              # Thai date format
        "%Y%m%d"                 # Compact date format
    ]
    
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_string, fmt)
            return f"'{date_obj.strftime('%Y-%m-%d')}'"
        except ValueError:
            continue
    
    return f"'{date_string}'"  # Return as is if no format matches

# Clean string for SQL insertion
def clean_sql_string(s):
    if s is None:
        return "NULL"
    if isinstance(s, bool):
        return "TRUE" if s else "FALSE"
    if isinstance(s, (int, float)):
        return str(s)
    
    # Escape single quotes
    s = str(s).replace("'", "''")
    return f"'{s}'"

# Extract address components
def extract_address(address_data):
    if not address_data:
        return {
            'no': '',
            'moo': '',
            'village_type': '',
            'building': '',
            'floor': '',
            'soi': '',
            'road': '',
            'sub_district': '',
            'district': '',
            'province': '',
            'country': '',
            'postal_code': ''
        }
    
    return {
        'no': address_data.get('no', ''),
        'moo': address_data.get('moo', ''),
        'village_type': address_data.get('villageType', {}).get('key', '') if isinstance(address_data.get('villageType'), dict) else '',
        'building': address_data.get('building', ''),
        'floor': address_data.get('floor', ''),
        'soi': address_data.get('soi', ''),
        'road': address_data.get('road', ''),
        'sub_district': address_data.get('subDistrict', ''),
        'district': address_data.get('district', ''),
        'province': address_data.get('province', ''),
        'country': address_data.get('country', ''),
        'postal_code': address_data.get('postalCode', '')
    }

# Generate SQL for eopen_sba table
def generate_sba_sql(json_data):
    if not json_data:
        return ""
    
    # Extract application data
    app_id = json_data.get('applicationId', 0)
    data = json_data.get('data', {})
    
    # Extract addresses
    residence = extract_address(data.get('residence', {}))
    mailing = extract_address(data.get('mailing', {}))
    work = extract_address(data.get('work', {}))
    
    # Extract bank account info
    redemption_accounts = data.get('otherAccountInfo', {}).get('redemptionBankAccounts', [{}])[0] if data.get('otherAccountInfo', {}).get('redemptionBankAccounts') else {}
    
    # Extract personal info
    title = data.get('title', {}).get('key', '') if isinstance(data.get('title'), dict) else ''
    th_first_name = data.get('thFirstName', '')
    th_last_name = data.get('thLastName', '')
    en_first_name = data.get('enFirstName', '')
    en_last_name = data.get('enLastName', '')
    
    # Card info
    card_number = data.get('cardNumber', '')
    card_expiry = data.get('cardExpiryDate', {}).get('formatted', '') if data.get('cardExpiryDate') else ''
    
    # Contact info
    email = data.get('email', '')
    mobile = data.get('mobileNumber', '')
    
    # Extract dates
    created_time = json_data.get('createdTime', '')
    trans_date = datetime.now().strftime('%Y-%m-%d')
    
    # Extract account type
    account_types = json_data.get('types', [])
    
    # Prepare SQL fields and values
    fields = [
        'trans_date', 'request_time', 'app_id', 'custtype', 'accounttype', 
        'ttitle', 'tname', 'tsurname', 'etitle', 'ename', 'esurname',
        'cardidtype', 'cardid', 'cardexpire', 
        'firstaddr1', 'firstaddr2', 'firstaddr3', 'firstzipcode', 'firstctycode',
        'firsttelno1', 'email1', 'secondsame', 'secondaddr1', 'secondaddr2', 'secondaddr3',
        'secondzipcode', 'secondctycode', 'thirdsame', 
        'thirdaddr1', 'thirdaddr2', 'thirdaddr3', 'thirdzipcode', 'thirdctycode',
        'bankcode', 'bankbranchcode', 'bankaccno',
        'mktid', 'fund_type', 'entry_user', 'entry_datetime'
    ]
    
    # Set values based on extracted data
    values = {
        'trans_date': f"'{trans_date}'",
        'request_time': "extract(epoch from now())",
        'app_id': str(app_id),
        'custtype': "'I'",  # Individual
        'accounttype': f"'{','.join(account_types)}'",
        'ttitle': clean_sql_string(title),
        'tname': clean_sql_string(th_first_name),
        'tsurname': clean_sql_string(th_last_name),
        'etitle': clean_sql_string(title),
        'ename': clean_sql_string(en_first_name),
        'esurname': clean_sql_string(en_last_name),
        'cardidtype': "'C'",  # Citizen card
        'cardid': clean_sql_string(card_number),
        'cardexpire': clean_sql_string(card_expiry),
        'firstaddr1': clean_sql_string(f"{residence['no']} {residence['moo']} {residence['soi']}".strip()),
        'firstaddr2': clean_sql_string(f"{residence['road']} {residence['sub_district']}".strip()),
        'firstaddr3': clean_sql_string(f"{residence['district']} {residence['province']}".strip()),
        'firstzipcode': clean_sql_string(residence['postal_code']),
        'firstctycode': clean_sql_string(residence['country']),
        'firsttelno1': clean_sql_string(mobile),
        'email1': clean_sql_string(email),
        'secondsame': clean_sql_string('Y' if data.get('mailingAddressSameAsFlag', {}).get('key') == 'Residence' else 'N'),
        'secondaddr1': clean_sql_string(f"{mailing['no']} {mailing['moo']} {mailing['soi']}".strip()),
        'secondaddr2': clean_sql_string(f"{mailing['road']} {mailing['sub_district']}".strip()),
        'secondaddr3': clean_sql_string(f"{mailing['district']} {mailing['province']}".strip()),
        'secondzipcode': clean_sql_string(mailing['postal_code']),
        'secondctycode': clean_sql_string(mailing['country']),
        'thirdsame': clean_sql_string('Y' if data.get('workAddressOption', {}).get('key') == 'Residence' else 'N'),
        'thirdaddr1': clean_sql_string(f"{work['no']} {work['moo']} {work['soi']}".strip()),
        'thirdaddr2': clean_sql_string(f"{work['road']} {work['sub_district']}".strip()),
        'thirdaddr3': clean_sql_string(f"{work['district']} {work['province']}".strip()),
        'thirdzipcode': clean_sql_string(work['postal_code']),
        'thirdctycode': clean_sql_string(work['country']),
        'bankcode': clean_sql_string(redemption_accounts.get('bankCode', '')),
        'bankbranchcode': clean_sql_string(redemption_accounts.get('bankBranchCode', '')),
        'bankaccno': clean_sql_string(redemption_accounts.get('bankAccountNo', '')),
        'mktid': clean_sql_string(data.get('referralId', '')),
        'fund_type': "'Y'" if 'FUND' in account_types else "'N'",
        'entry_user': "'SYSTEM'",
        'entry_datetime': "now()"
    }
    
    # Construct SQL
    fields_str = ', '.join(fields)
    values_str = ', '.join([values.get(field, 'NULL') for field in fields])
    
    sql = f"INSERT INTO public.eopen_sba ({fields_str}) VALUES ({values_str});"
    return sql

# Generate SQL for eopen_stt table
def generate_stt_sql(json_data):
    if not json_data:
        return ""
    
    # Extract application data
    app_id = json_data.get('applicationId', 0)
    status = json_data.get('status', '')
    contract_no = json_data.get('contractNo', '')
    data = json_data.get('data', {})
    
    # Extract dates and times
    created_time = json_data.get('createdTime', '')
    last_updated_time = json_data.get('lastUpdatedTime', '')
    submitted_time = json_data.get('submittedTime', '')
    trans_date = datetime.now().strftime('%Y-%m-%d')
    
    # Extract user data
    user_data = json_data.get('user', {})
    user_id = user_data.get('userId', 0)
    cid = user_data.get('cid', '')
    
    # Extract personal info
    title = data.get('title', {}).get('key', '') if isinstance(data.get('title'), dict) else ''
    th_first_name = data.get('thFirstName', '')
    th_last_name = data.get('thLastName', '')
    en_first_name = data.get('enFirstName', '')
    en_last_name = data.get('enLastName', '')
    
    # Extract addresses
    residence = extract_address(data.get('residence', {}))
    mailing = extract_address(data.get('mailing', {}))
    contact = extract_address(data.get('contact', {}))
    work = extract_address(data.get('work', {}))
    
    # Extract contact info
    mobile = data.get('mobileNumber', '')
    email = data.get('email', '')
    
    # Extract birth date
    birth_date = data.get('birthDate', {}).get('formatted', '') if data.get('birthDate') else ''
    
    # Extract bank account info
    redemption_accounts = data.get('otherAccountInfo', {}).get('redemptionBankAccounts', [{}])[0] if data.get('otherAccountInfo', {}).get('redemptionBankAccounts') else {}
    
    # Extract account types
    types = ','.join(json_data.get('types', []))
    
    # Extract suitability data
    suit_risk_level = data.get('suitabilityRiskLevel', '')
    
    # Prepare SQL fields and values
    fields = [
        'trans_date', 'request_time', 'app_id', 'status', 'types', 'verifi_type',
        'contract_no', 'created_time', 'last_updated_time', 'submitted_time',
        'u_userid', 'u_cid', 't_title', 't_fname', 't_lname', 'e_title', 'e_fname', 'e_lname',
        'mobile', 'email', 'birth_date', 'nationality',
        'mail_same_flag', 'mail_no', 'mail_moo', 'mail_soi', 'mail_road',
        'mail_sub_district', 'mail_district', 'mail_province', 'mail_country', 'mail_postal',
        'cont_same_flag', 'cont_no', 'cont_moo', 'cont_soi', 'cont_road',
        'cont_sub_district', 'cont_district', 'cont_province', 'cont_country', 'cont_postal',
        'resi_no', 'resi_moo', 'resi_soi', 'resi_road',
        'resi_sub_district', 'resi_district', 'resi_province', 'resi_country', 'resi_postal',
        'redemp_bank_code', 'redemp_bank_branch_code', 'redemp_bank_account_no', 'redemp_bank_account_name',
        'suit_risk_level', 'entry_user', 'entry_datetime'
    ]
    
    values = {
        'trans_date': f"'{trans_date}'",
        'request_time': "extract(epoch from now())",
        'app_id': str(app_id),
        'status': clean_sql_string(status),
        'types': clean_sql_string(types),
        'verifi_type': clean_sql_string(json_data.get('verificationType', '')),
        'contract_no': clean_sql_string(contract_no),
        'created_time': clean_sql_string(created_time),
        'last_updated_time': clean_sql_string(last_updated_time),
        'submitted_time': clean_sql_string(submitted_time),
        'u_userid': str(user_id),
        'u_cid': clean_sql_string(cid),
        't_title': clean_sql_string(title),
        't_fname': clean_sql_string(th_first_name),
        't_lname': clean_sql_string(th_last_name),
        'e_title': clean_sql_string(title),
        'e_fname': clean_sql_string(en_first_name),
        'e_lname': clean_sql_string(en_last_name),
        'mobile': clean_sql_string(mobile),
        'email': clean_sql_string(email),
        'birth_date': clean_sql_string(birth_date),
        'nationality': clean_sql_string(data.get('nationality', '')),
        'mail_same_flag': clean_sql_string(data.get('mailingAddressSameAsFlag', {}).get('key', '') if isinstance(data.get('mailingAddressSameAsFlag'), dict) else ''),
        'mail_no': clean_sql_string(mailing['no']),
        'mail_moo': clean_sql_string(mailing['moo']),
        'mail_soi': clean_sql_string(mailing['soi']),
        'mail_road': clean_sql_string(mailing['road']),
        'mail_sub_district': clean_sql_string(mailing['sub_district']),
        'mail_district': clean_sql_string(mailing['district']),
        'mail_province': clean_sql_string(mailing['province']),
        'mail_country': clean_sql_string(mailing['country']),
        'mail_postal': clean_sql_string(mailing['postal_code']),
        'cont_same_flag': clean_sql_string(data.get('contactAddressSameAsFlag', {}).get('key', '') if isinstance(data.get('contactAddressSameAsFlag'), dict) else ''),
        'cont_no': clean_sql_string(contact['no']),
        'cont_moo': clean_sql_string(contact['moo']),
        'cont_soi': clean_sql_string(contact['soi']),
        'cont_road': clean_sql_string(contact['road']),
        'cont_sub_district': clean_sql_string(contact['sub_district']),
        'cont_district': clean_sql_string(contact['district']),
        'cont_province': clean_sql_string(contact['province']),
        'cont_country': clean_sql_string(contact['country']),
        'cont_postal': clean_sql_string(contact['postal_code']),
        'resi_no': clean_sql_string(residence['no']),
        'resi_moo': clean_sql_string(residence['moo']),
        'resi_soi': clean_sql_string(residence['soi']),
        'resi_road': clean_sql_string(residence['road']),
        'resi_sub_district': clean_sql_string(residence['sub_district']),
        'resi_district': clean_sql_string(residence['district']),
        'resi_province': clean_sql_string(residence['province']),
        'resi_country': clean_sql_string(residence['country']),
        'resi_postal': clean_sql_string(residence['postal_code']),
        'redemp_bank_code': clean_sql_string(redemption_accounts.get('bankCode', '')),
        'redemp_bank_branch_code': clean_sql_string(redemption_accounts.get('bankBranchCode', '')),
        'redemp_bank_account_no': clean_sql_string(redemption_accounts.get('bankAccountNo', '')),
        'redemp_bank_account_name': clean_sql_string(redemption_accounts.get('bankAccountName', '')),
        'suit_risk_level': clean_sql_string(suit_risk_level),
        'entry_user': "'SYSTEM'",
        'entry_datetime': "now()"
    }
    
    # Construct SQL
    fields_str = ', '.join(fields)
    values_str = ', '.join([values.get(field, 'NULL') for field in fields])
    
    sql = f"INSERT INTO public.eopen_stt ({fields_str}) VALUES ({values_str});"
    return sql

# Main function
def main():
    # File paths
    json_file = 'data.json'
    output_file = 'sql_inserts.sql'
    
    # Read JSON data
    json_data = read_json_file(json_file)
    if not json_data:
        return
    
    # Generate SQL statements
    sba_sql = generate_sba_sql(json_data)
    stt_sql = generate_stt_sql(json_data)
    
    # Write SQL to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- SQL generated from JSON data\n")
        f.write("-- Generated on: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
        
        f.write("-- Insert into eopen_sba table\n")
        f.write(sba_sql + "\n\n")
        
        f.write("-- Insert into eopen_stt table\n")
        f.write(stt_sql + "\n")
    
    print(f"SQL statements have been written to {output_file}")
    print("I will done.")

if __name__ == "__main__":
    main()