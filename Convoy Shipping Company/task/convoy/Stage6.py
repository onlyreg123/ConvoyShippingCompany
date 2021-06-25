# Write your code here
import pandas as pd
import sqlite3


def convert_2csv(xlsx_name, csv_name, sheet=''):
    df = pd.read_excel(xlsx_name, sheet_name=sheet, converters={'vehicle_id': str, 'engine_capacity': str,
                                                                'fuel_consumption': str, 'maximum_load': str})
    df.to_csv(csv_name, index=False)
    n_lines = df.shape[0]
    line_s = "line" if n_lines == 1 else "lines"
    was_were = "was" if n_lines == 1 else "were"
    print(f"{n_lines} {line_s} {was_were} added to {csv_name}")
    return


def clean_df(df):
    df_out = df.copy(deep=True)
    for col in df_out:
        df_out[col].replace(r'[^0-9]', '', regex=True, inplace=True)
    return df_out


def create_checked(csv_name, checked_name):
    # load initial df from input csv file
    df_ini = pd.read_csv(csv_name, dtype=str)
    # clean non alphanumeric characters
    df_out = clean_df(df_ini)
    # MAGIC! compare set Nan to unchanged cells
    df_diff = df_ini.compare(df_out, keep_shape=True)
    # obtain changed cells
    null_values = df_diff.isnull().sum().sum()
    total_values = df_out.shape[0] * df_out.shape[1] * 2
    changed_values = (total_values - null_values) // 2
    # save cleaned result to new csv "checked" file
    df_out.to_csv(checked_name, index=False)
    # print resume
    cell_s = "cell" if changed_values == 1 else "cells"
    was_were = "was" if changed_values == 1 else "were"
    print(f'{changed_values} {cell_s} {was_were} corrected in {checked_name}')


def calc_score(row):
    # pitstops = (450 // row['engine_capacity'])
    pitstops = 4.5 * row['fuel_consumption'] // (row['engine_capacity'])
    fuel = (450 / 100) * row['fuel_consumption']
    more20T = row['maximum_load'] >= 20
    score = 0
    score += 2 if pitstops == 0 else (1 if pitstops == 1 else 0)
    score += 2 if fuel <= 230 else 1
    score += 2 if more20T else 0
    return score


def add_score(df):
    score = []
    for idx, row in df.iterrows():
        score.append(calc_score(row))
    df['score'] = score
    return df


def populate_from_checked(base_name, conn):
    checked_name = base_name + '[CHECKED].csv'
    df_previous = pd.read_csv(checked_name)
    df = add_score(df_previous)
    df.to_sql("convoy", conn, if_exists='append', index=False)
    record_s = "record" if df.shape[0] == 1 else "records"
    was_were = "was" if df.shape[0] == 1 else "were"
    print(f"{df.shape[0]} {record_s} {was_were} inserted into {base_name + '.s3db'}")
    conn.commit()


def create_table(name, conn):
    cursor = conn.cursor()
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {name} (
    vehicle_id INT NOT NULL PRIMARY KEY,
    engine_capacity INT NOT NULL,
    fuel_consumption INT NOT NULL,
    maximum_load INT NOT NULL,
    score INT NOT NULL
    );""")
    conn.commit()


def save_2sql(base_name):
    conn = sqlite3.connect(base_name + ".s3db", isolation_level=None)
    create_table("convoy", conn)
    populate_from_checked(base_name, conn)
    conn.close()
    return


def save_json(base_name):
    conn = sqlite3.connect(base_name + ".s3db", isolation_level=None)
    query = "SELECT vehicle_id, engine_capacity, fuel_consumption, maximum_load FROM convoy WHERE score > 3"
    df = pd.read_sql(sql=query, con=conn)
    # df.to_json(base_name + ".json", orient="records")
    records = df.to_json(orient="records")
    dic = f'{{"convoy": {records}}}'
    with open(base_name + ".json", "w") as f:
        f.write(str(dic))
    # json.dumps(text, indent=4)
    conn.close()
    vehicle_s = "vehicle" if df.shape[0] == 1 else "vehicles"
    was_were = "was" if df.shape[0] == 1 else "were"
    print(f"{df.shape[0]} {vehicle_s} {was_were} saved into {base_name + '.json'}")


def to_xml(df, filename=None, mode='w'):
    def row_to_xml(row):
        xml = ['<vehicle>']
        for i, col_name in enumerate(row.index):
            xml.append('  <{0}>{1}</{2}>'.format(col_name, row.iloc[i], col_name))
            # xml.append('  <field name="{0}">{1}</field>'.format(col_name, row.ilog[i]))
        xml.append('</vehicle>')
        return '\n'.join(xml)
    res = '\n'.join(df.apply(row_to_xml, axis=1))

    if filename is None:
        return res
    with open(filename, mode) as f:
        f.write(res)


def save_xml(base_name):
    conn = sqlite3.connect(base_name + ".s3db", isolation_level=None)
    query = "SELECT vehicle_id, engine_capacity, fuel_consumption, maximum_load FROM convoy WHERE score <= 3"
    df = pd.read_sql(sql=query, con=conn)
    pd.DataFrame.to_xml = to_xml
    str_xml = df.to_xml()
    xml = f'<convoy>\n{str_xml}\n</convoy>'
    with open(base_name + ".xml", "w") as f:
        f.write(xml)

    vehicle_s = "vehicle" if df.shape[0] == 1 else "vehicles"
    was_were = "was" if df.shape[0] == 1 else "were"
    print(f"{df.shape[0]} {vehicle_s} {was_were} saved into {base_name + '.xml'}")


def main():
    print("Input file name")
    fname = input()
    # fname = "data_big_csv.csv"

    # define different filenames that we use
    base_name, ext = fname.split(".")
    csv_name = base_name + ".csv"
    checked_name = base_name + '[CHECKED].csv'

    if ext == "xlsx":
        convert_2csv(fname, csv_name, sheet='Vehicles')

    if not fname.endswith("[CHECKED].csv") and (ext == "xlsx" or ext == "csv"):
        create_checked(csv_name, checked_name)

    base_name = base_name.replace('[CHECKED]', '')
    if ext != "s3db":
        save_2sql(base_name)

    save_json(base_name)    # score > 3
    save_xml(base_name)     # score <= 3


if __name__ == "__main__":
    main()
