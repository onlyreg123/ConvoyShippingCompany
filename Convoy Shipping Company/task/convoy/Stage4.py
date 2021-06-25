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


def populate_from_checked(base_name, conn):
    checked_name = base_name + '[CHECKED].csv'
    df = pd.read_csv(checked_name)
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
    maximum_load INT NOT NULL
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
    df = pd.read_sql(sql="SELECT * FROM convoy", con=conn)
    # df.to_json(base_name + ".json", orient="records")
    records = df.to_json(orient="records")
    dic = f'{{convoy: {records}}}'
    with open(base_name + ".json", "w") as f:
        f.write(str(dic))
    # json.dumps(text, indent=4)
    conn.close()
    vehicle_s = "vehicle" if df.shape[0] == 1 else "vehicles"
    was_were = "was" if df.shape[0] == 1 else "were"
    print(f"{df.shape[0]} {vehicle_s} {was_were} saved into {base_name + '.json'}")


def main():
    print("Input file name")
    # fname = input()
    fname = "data_big_xlsx.xlsx"

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

    save_json(base_name)


if __name__ == "__main__":
    main()
