import csv

def detect_csv_separator(file_path, Output_File_Path):
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        with open(Output_File_Path, mode ='w', encoding='utf-8') as csv_file:
            csv_writer = csv.DictWriter(csv_file, fieldnames=csv_reader.fieldnames)
            csv_writer.writeheader()
            for line in csv_reader:
                id = line['idiom_id']
                if id.lower().startswith("id"):
                    csv_writer.writerow(line)

Language = "Indonesian"
Output_File_Path = f"idioms_structured/Meanings/{Language}/Raw_Meaning_Rows.csv"



if __name__ == "__main__":
    detect_csv_separator("idioms_structured/idiom_meanings_rows.csv", Output_File_Path)